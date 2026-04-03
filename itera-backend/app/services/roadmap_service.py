"""
v3 Roadmap generation service.
Breaks generation into small LLM calls that 7B models can handle.
"""
import logging
import asyncio
import httpx
from urllib.parse import quote_plus
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.llm_tracker import tracked_llm_call_with_json_retry
from app.models.generated_roadmap import GeneratedRoadmap, KnowledgeBase
from app.models.resource_cache import ResourceCache
from app.models.user import User
from app.config import get_settings

logger = logging.getLogger(__name__)

# Keep strong references to background tasks so they aren't garbage collected
_background_tasks: set = set()


def sa_now():
    from sqlalchemy import func
    return func.now()


# ---------- Step 1: Generate phase/skill_area structure (small JSON) ----------

_STRUCTURE_SYSTEM = """You are an expert curriculum designer. Create a learning roadmap structure.
Return ONLY a valid JSON object. No markdown. No text outside JSON."""

_STRUCTURE_USER = """Create a learning roadmap for someone who wants to become a {target_role}.
Their goal: {learning_goal}
{interests_line}
Their tech stack: {tech_stack}
Experience: {experience_years} years in {domain}

Return ONLY this JSON structure:
{{
  "title": "Roadmap title",
  "description": "1-2 sentence description",
  "phases": [
    {{
      "phase_index": 0,
      "title": "Phase title",
      "description": "Phase description",
      "skill_areas": [
        {{
          "skill_area_index": 0,
          "title": "Skill area title",
          "description": "Skill area description"
        }}
      ]
    }}
  ]
}}

Keep it to 3-4 phases, 2 skill areas per phase. Use 0-based indexing. No markdown. Just JSON."""


async def _generate_structure(user: User, target_role: str, learning_goal: str, interests: str | None) -> dict:
    tech_stack = ", ".join(user.tech_stack or []) or "none specified"
    interests_line = f"Interests: {interests}" if interests else ""

    user_msg = _STRUCTURE_USER.format(
        target_role=target_role,
        learning_goal=learning_goal,
        interests_line=interests_line,
        tech_stack=tech_stack,
        experience_years=user.experience_years or 0,
        domain=user.primary_domain or "general",
    )

    logger.info("[Roadmap] Step 1: Generating phase/skill_area structure...")
    result = await tracked_llm_call_with_json_retry(
        [{"role": "system", "content": _STRUCTURE_SYSTEM}, {"role": "user", "content": user_msg}],
        call_type="roadmap_structure",
        temperature=0.7, max_tokens=1500,
    )
    logger.info("[Roadmap] Step 1 complete: %d phases", len(result.get("phases", [])))
    return result


# ---------- Step 2: Generate topics per skill area (small JSON per call) ----------

_TOPICS_SYSTEM = """You are an expert curriculum designer. Generate learning topics for a skill area.
Return ONLY a valid JSON object. No markdown. No text outside JSON."""

_TOPICS_USER = """Generate learning topics for the skill area "{skill_area_title}" ({skill_area_desc}).
This is part of a roadmap to become a {target_role}.
Student knows: {tech_stack} ({experience_years} years experience).

Return ONLY this JSON:
{{
  "topics": [
    {{
      "title": "Topic title",
      "description": "2-3 sentences: what this teaches, key terms, practical applications.",
      "estimated_hours": 3,
      "difficulty": 3,
      "search_query": "specific search query for finding tutorials on this topic"
    }}
  ]
}}

Generate 3-4 topics. No markdown. Just JSON."""


async def _generate_topics_for_skill_area(
    skill_area: dict, target_role: str, user: User
) -> list[dict]:
    tech_stack = ", ".join(user.tech_stack or []) or "none"
    user_msg = _TOPICS_USER.format(
        skill_area_title=skill_area["title"],
        skill_area_desc=skill_area.get("description", ""),
        target_role=target_role,
        tech_stack=tech_stack,
        experience_years=user.experience_years or 0,
    )

    result = await tracked_llm_call_with_json_retry(
        [{"role": "system", "content": _TOPICS_SYSTEM}, {"role": "user", "content": user_msg}],
        call_type="topic_generation",
        temperature=0.7, max_tokens=1500,
    )
    topics = result.get("topics", [])
    logger.info("[Roadmap] Generated %d topics for skill area '%s'", len(topics), skill_area["title"])
    return topics


# ---------- Step 3: Search real resources per topic ----------

async def _search_topic_resources(topic: dict, include_paid: bool, db=None) -> list[dict]:
    """Search YouTube playlists + freeCodeCamp + Coursera + Udemy for a single topic.
    Results are cached in resource_cache by search_query to avoid re-fetching."""
    from sqlalchemy import select, update
    settings = get_settings()
    resources = []
    query = topic.get("search_query", topic["title"])

    # --- Cache lookup ---
    if db is not None:
        try:
            cached = await db.execute(
                select(ResourceCache).where(ResourceCache.search_query == query)
            )
            cached_row = cached.scalar_one_or_none()
            if cached_row is not None:
                await db.execute(
                    update(ResourceCache)
                    .where(ResourceCache.search_query == query)
                    .values(
                        hit_count=ResourceCache.hit_count + 1,
                        last_used_at=sa_now(),
                    )
                )
                logger.info("[Resources] Cache HIT for query '%s' (hits: %d)", query, cached_row.hit_count + 1)
                all_resources = cached_row.resources
                if include_paid:
                    return all_resources
                return [r for r in all_resources if r.get("type") == "free"]
        except Exception as e:
            logger.warning("[Resources] Cache lookup failed: %s", e)

    async with httpx.AsyncClient(timeout=10.0) as client:
        # YouTube — try API first, fall back to search URL if quota exceeded or key missing
        yt_key = settings.youtube_api_key if hasattr(settings, 'youtube_api_key') else getattr(settings, 'YOUTUBE_API_KEY', '')
        yt_api_ok = False
        if yt_key:
            yt_query = f"{query} full course tutorial playlist"
            try:
                resp = await client.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "part": "snippet",
                        "q": yt_query,
                        "type": "playlist",
                        "maxResults": 2,
                        "key": yt_key,
                    },
                )
                if resp.status_code == 200:
                    items = resp.json().get("items", [])
                    for item in items[:2]:
                        playlist_id = item["id"]["playlistId"]
                        resources.append({
                            "title": item["snippet"]["title"],
                            "platform": "YouTube",
                            "url": f"https://www.youtube.com/playlist?list={playlist_id}",
                            "type": "free",
                            "format": "playlist",
                        })
                    if items:
                        yt_api_ok = True

                # Fallback: if no playlists found, search for long-form videos (>20 min)
                if not any(r["platform"] == "YouTube" for r in resources) and resp.status_code == 200:
                    resp = await client.get(
                        "https://www.googleapis.com/youtube/v3/search",
                        params={
                            "part": "snippet",
                            "q": f"{query} full course tutorial",
                            "type": "video",
                            "videoDuration": "long",
                            "maxResults": 1,
                            "key": yt_key,
                        },
                    )
                    if resp.status_code == 200:
                        items = resp.json().get("items", [])
                        if items:
                            vid = items[0]
                            resources.append({
                                "title": vid["snippet"]["title"],
                                "platform": "YouTube",
                                "url": f"https://www.youtube.com/watch?v={vid['id']['videoId']}",
                                "type": "free",
                                "format": "video",
                            })
                            yt_api_ok = True

                if resp.status_code == 403:
                    logger.warning("[Resources] YouTube API quota exceeded — using search URL fallback")
            except Exception as e:
                logger.warning("[Resources] YouTube API failed: %s — using search URL fallback", e)

        # YouTube fallback: always guarantee a YouTube search link if API didn't return results
        if not yt_api_ok:
            resources.append({
                "title": f"YouTube: {query} — full course",
                "platform": "YouTube",
                "url": f"https://www.youtube.com/results?search_query={quote_plus(query + ' full course tutorial')}",
                "type": "free",
                "format": "search",
            })

        # freeCodeCamp — always include a search link (100% free, high quality)
        resources.append({
            "title": f"freeCodeCamp: {query}",
            "platform": "freeCodeCamp",
            "url": f"https://www.freecodecamp.org/news/search/?query={quote_plus(query)}",
            "type": "free",
        })

        # Coursera — always store in cache (filtered at read time)
        resources.append({
            "title": f"Coursera: {query}",
            "platform": "Coursera",
            "url": f"https://www.coursera.org/search?query={quote_plus(query)}",
            "type": "paid",
        })

        # Udemy — always store in cache (filtered at read time)
        resources.append({
            "title": f"Udemy: {query}",
            "platform": "Udemy",
            "url": f"https://www.udemy.com/courses/search/?q={quote_plus(query)}",
            "type": "paid",
        })

    # --- Cache write (always store all resources, both free+paid) ---
    if db is not None:
        try:
            import uuid as _uuid
            db.add(ResourceCache(
                id=_uuid.uuid4(),
                search_query=query,
                resources=resources,
                hit_count=0,
            ))
            logger.info("[Resources] Cache MISS — stored %d resources for query '%s'", len(resources), query)
        except Exception as e:
            logger.warning("[Resources] Cache write failed: %s", e)

    if include_paid:
        return resources
    return [r for r in resources if r.get("type") == "free"]


# ---------- Step 4: Stamp topic IDs + split free/paid hours ----------

def _stamp_topic_ids(roadmap_data: dict) -> float:
    """
    Stamp topic_id on every topic.
    Replace scalar estimated_hours with {free, paid} split.
    Paid courses are ~30% more efficient than free resources.
    Returns total free hours (used for roadmap-level estimate).
    """
    total_free = 0.0
    total_paid = 0.0

    for phase in roadmap_data.get("phases", []):
        pi = phase.get("phase_index", 0)
        phase_free = 0.0
        phase_paid = 0.0
        for skill_area in phase.get("skill_areas", []):
            ai = skill_area.get("skill_area_index", 0)
            for ti, topic in enumerate(skill_area.get("topics", [])):
                topic["topic_id"] = f"{pi}-{ai}-{ti}"
                raw_hours = topic.get("estimated_hours", 2)
                free_h = round(float(raw_hours), 1)
                paid_h = round(free_h * 0.7, 1)
                topic["estimated_hours"] = {"free": free_h, "paid": paid_h}
                phase_free += free_h
                phase_paid += paid_h

        phase["estimated_hours"] = {"free": round(phase_free, 1), "paid": round(phase_paid, 1)}
        total_free += phase_free
        total_paid += phase_paid

    roadmap_data["total_estimated_hours"] = {
        "free": round(total_free, 1),
        "paid": round(total_paid, 1),
    }
    return round(total_free, 1)


# ---------- Step 5: Generate knowledge base ONE TOPIC AT A TIME ----------

_KB_TOPIC_SYSTEM = """You are a technical education knowledge base generator. Generate a DETAILED knowledge base entry for a single learning topic. Be extremely thorough — this data is used for semantic matching of student progress logs, so every relevant term, concept, function name, and student phrasing must be included.
Return ONLY valid JSON. No markdown. No text outside JSON."""

_KB_TOPIC_USER = """Generate a knowledge base entry for:

Topic: "{topic_title}"
Section: "{section_name}"
Domain: {domain}
Difficulty: {difficulty}/5

The student is learning this as part of becoming a {target_role}.

Return ONLY valid JSON:
{{
  "what_it_is": "3-4 sentence explanation of what this topic is, why it matters, and how it fits into the broader skill area. Be specific and technical.",
  "what_you_will_learn": [
    "Concept name — 1-2 sentence explanation of what it is and why it matters (5-8 items)"
  ],
  "subtopics": [
    "slug-format-subtopic-name (6-10 items, include specific tools/libraries)"
  ],
  "validation_keywords": [
    "relevant technical term, function name, library name, concept name (15-20 items)"
  ]
}}

IMPORTANT:
- what_you_will_learn: Each item must be "Concept — explanation" format. 5-8 items.
- subtopics: Use slug format (lowercase-with-hyphens). Include specific tools, libraries. 6-10 items.
- validation_keywords: Include technical terms, abbreviations, function names. 15-20 items.
- No markdown fences. Just JSON."""


def _slugify(text: str) -> str:
    """Convert text to slug format."""
    import re
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s]+', '-', text)
    return text


async def _generate_single_topic_kb(
    topic: dict,
    section_name: str,
    section_id: str,
    target_role: str,
    domain: str,
    roadmap_id: str | None = None,
    db=None,
) -> dict:
    """Generate a rich KB entry for one topic. Returns the assembled entry."""
    import hashlib
    import json

    topic_title = topic.get("title", "")
    topic_id = topic.get("topic_id", "")
    benchmark_hours = topic.get("estimated_hours", 2)
    difficulty = topic.get("difficulty", 3)

    user_msg = _KB_TOPIC_USER.format(
        topic_title=topic_title,
        section_name=section_name,
        domain=domain,
        difficulty=difficulty,
        target_role=target_role,
    )

    generation_status = "success"
    knowledge = {}

    try:
        knowledge = await tracked_llm_call_with_json_retry(
            [{"role": "system", "content": _KB_TOPIC_SYSTEM}, {"role": "user", "content": user_msg}],
            call_type="kb_generation",
            roadmap_id=roadmap_id,
            topic_id=topic_id,
            temperature=0.4,
            max_tokens=1500,
            db=db,
        )
    except Exception as e:
        logger.warning("[KB] Failed for topic '%s': %s — using fallback", topic_title, e)
        generation_status = "failed"
        knowledge = {
            "what_it_is": f"{topic_title} is a topic in {section_name}.",
            "what_you_will_learn": [topic_title],
            "subtopics": [_slugify(topic_title)],
            "validation_keywords": [w.lower() for w in topic_title.split()],
        }

    # Compute version hash from knowledge content
    content_str = json.dumps(knowledge, sort_keys=True)
    version_hash = hashlib.md5(content_str.encode()).hexdigest()[:16]

    return {
        "topic_id": topic_id,
        "section_id": section_id,
        "section_name": section_name,
        "topic_name": topic_title,
        "benchmark_hours": benchmark_hours,
        "difficulty": difficulty,
        "knowledge": knowledge,
        "generation_status": generation_status,
        "version_hash": version_hash,
    }


async def _generate_all_kb_entries(
    topics_with_context: list[dict],
    roadmap_id: str | None = None,
    db=None,
) -> list[dict]:
    """Generate KB entries for all topics with max 5 concurrent LLM calls."""
    semaphore = asyncio.Semaphore(5)

    async def _one(item):
        async with semaphore:
            return await _generate_single_topic_kb(
                topic=item["topic"],
                section_name=item["section_name"],
                section_id=item["section_id"],
                target_role=item["target_role"],
                domain=item["domain"],
                roadmap_id=roadmap_id,
                db=db,
            )

    results = await asyncio.gather(*[_one(item) for item in topics_with_context])
    return list(results)


# ---------- Background KB generation ----------

async def _generate_kb_background(
    roadmap_id_str: str,
    roadmap_title: str,
    structure: dict,
    target_role: str,
    domain: str,
    total_free_hours: float,
    total_paid_hours: float,
):
    """Generate KB entries in background after roadmap is returned to user."""
    from datetime import datetime
    from app.database import AsyncSessionLocal

    logger.info("[KB-BG] Starting background KB generation for roadmap %s", roadmap_id_str)

    topics_with_context = []
    for phase in structure.get("phases", []):
        for skill_area in phase.get("skill_areas", []):
            section_name = skill_area.get("title", "")
            section_id = _slugify(section_name)
            for topic in skill_area.get("topics", []):
                topics_with_context.append({
                    "topic": topic,
                    "section_name": section_name,
                    "section_id": section_id,
                    "target_role": target_role,
                    "domain": domain,
                })

    try:
        async with AsyncSessionLocal() as db:
            try:
                all_kb_topics = await _generate_all_kb_entries(
                    topics_with_context,
                    roadmap_id=roadmap_id_str,
                    db=db,
                )
                logger.info("[KB-BG] Generated %d KB entries", len(all_kb_topics))

                failed_count = sum(1 for t in all_kb_topics if t.get("generation_status") == "failed")
                if failed_count:
                    logger.warning("[KB-BG] %d/%d topics failed", failed_count, len(all_kb_topics))

                settings = get_settings()
                kb_data = {
                    "roadmap_id": roadmap_id_str,
                    "roadmap_name": roadmap_title,
                    "estimated_hours": {"free": total_free_hours, "paid": total_paid_hours},
                    "generated_at": datetime.utcnow().isoformat(),
                    "generator_model": settings.ollama_model,
                    "version": 1,
                    "topics": all_kb_topics,
                }

                import uuid
                if all_kb_topics:
                    kb = KnowledgeBase(
                        roadmap_id=uuid.UUID(roadmap_id_str),
                        data=kb_data,
                        version=1,
                    )
                    db.add(kb)

                await db.commit()
                logger.info("[KB-BG] Saved KB for roadmap %s (%d topics, %d failed)", roadmap_id_str, len(all_kb_topics), failed_count)
            except Exception:
                await db.rollback()
                raise
    except Exception as e:
        logger.error("[KB-BG] Background KB generation failed for roadmap %s: %s", roadmap_id_str, e, exc_info=True)


# ---------- Main orchestrator ----------

async def generate_roadmap(
    db: AsyncSession,
    user: User,
    target_role: str,
    learning_goal: str,
    interests: str | None = None,
    hours_per_week: float | None = None,
    include_paid: bool = True,
) -> GeneratedRoadmap:
    """Full roadmap generation pipeline. KB is generated in background."""

    domain = user.primary_domain or "general"

    # Step 1: Generate structure (phases + skill_areas, no topics yet)
    structure = await _generate_structure(user, target_role, learning_goal, interests)

    # Step 2: Generate topics for each skill area (parallel)
    all_topic_tasks = []
    for phase in structure.get("phases", []):
        for skill_area in phase.get("skill_areas", []):
            all_topic_tasks.append((phase, skill_area))

    async def _fill_topics(phase, skill_area):
        topics = await _generate_topics_for_skill_area(skill_area, target_role, user)
        skill_area["topics"] = topics

    await asyncio.gather(*[_fill_topics(p, sa) for p, sa in all_topic_tasks])

    # Step 3: Stamp topic IDs + compute split free/paid hours
    total_free_hours = _stamp_topic_ids(structure)
    total_paid_hours = structure.get("total_estimated_hours", {}).get("paid", round(total_free_hours * 0.7, 1))
    logger.info("[Roadmap] Total estimated hours: free=%.1f paid=%.1f", total_free_hours, total_paid_hours)

    # Step 4: Attach resources (parallel for all topics)
    all_topics = []
    for phase in structure.get("phases", []):
        for skill_area in phase.get("skill_areas", []):
            for topic in skill_area.get("topics", []):
                all_topics.append(topic)

    async def _attach(topic):
        topic["resources"] = await _search_topic_resources(topic, include_paid, db=db)

    await asyncio.gather(*[_attach(t) for t in all_topics])
    logger.info("[Roadmap] Resources attached for %d topics", len(all_topics))

    # Step 5: Persist roadmap (KB will be generated in background)
    rm = GeneratedRoadmap(
        user_id=user.id,
        title=structure.get("title", f"{target_role} Roadmap"),
        description=structure.get("description", ""),
        target_role=target_role,
        learning_goal=learning_goal,
        interests=interests,
        hours_per_week=hours_per_week,
        include_paid=include_paid,
        total_estimated_hours=total_free_hours,
        roadmap_data=structure,
    )
    db.add(rm)
    await db.flush()  # rm.id is now available
    roadmap_id_str = str(rm.id)

    # Step 6: Kick off KB generation in background (user gets roadmap immediately)
    import copy
    structure_copy = copy.deepcopy(structure)
    task = asyncio.create_task(
        _generate_kb_background(
            roadmap_id_str=roadmap_id_str,
            roadmap_title=rm.title,
            structure=structure_copy,
            target_role=target_role,
            domain=domain,
            total_free_hours=total_free_hours,
            total_paid_hours=total_paid_hours,
        )
    )
    # Hold a strong reference so the task isn't garbage collected
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    logger.info("[Roadmap] Saved roadmap id=%s — KB generating in background", rm.id)
    return rm
