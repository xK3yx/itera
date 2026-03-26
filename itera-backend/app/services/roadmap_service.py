"""
v3 Roadmap generation service.
Breaks generation into small LLM calls that 7B models can handle.
"""
import logging
import asyncio
import httpx
from urllib.parse import quote_plus
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.llm_client import llm_call_with_json_retry
from app.models.generated_roadmap import GeneratedRoadmap, KnowledgeBase
from app.models.user import User
from app.config import get_settings

logger = logging.getLogger(__name__)


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

Keep it to 3-5 phases, 2-3 skill areas per phase. Use 0-based indexing. No markdown. Just JSON."""


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
    result = await llm_call_with_json_retry(
        [{"role": "system", "content": _STRUCTURE_SYSTEM}, {"role": "user", "content": user_msg}],
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

Generate 3-6 topics. No markdown. Just JSON."""


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

    result = await llm_call_with_json_retry(
        [{"role": "system", "content": _TOPICS_SYSTEM}, {"role": "user", "content": user_msg}],
        temperature=0.7, max_tokens=1500,
    )
    topics = result.get("topics", [])
    logger.info("[Roadmap] Generated %d topics for skill area '%s'", len(topics), skill_area["title"])
    return topics


# ---------- Step 3: Search real resources per topic ----------

async def _search_topic_resources(topic: dict, include_paid: bool) -> list[dict]:
    """Search YouTube playlists + Coursera + Udemy for a single topic."""
    settings = get_settings()
    resources = []
    query = topic.get("search_query", topic["title"])

    async with httpx.AsyncClient(timeout=10.0) as client:
        # YouTube — search for PLAYLISTS (full courses) instead of individual videos
        yt_key = settings.youtube_api_key if hasattr(settings, 'youtube_api_key') else getattr(settings, 'YOUTUBE_API_KEY', '')
        if yt_key:
            # Search query optimised for structured learning content
            yt_query = f"{query} full course tutorial playlist"
            try:
                # First: try to find a playlist (structured, multi-part learning)
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

                # Fallback: if no playlists found, search for long-form videos (>20 min)
                if not any(r["platform"] == "YouTube" for r in resources):
                    resp = await client.get(
                        "https://www.googleapis.com/youtube/v3/search",
                        params={
                            "part": "snippet",
                            "q": f"{query} full course tutorial",
                            "type": "video",
                            "videoDuration": "long",  # >20 minutes
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
            except Exception as e:
                logger.warning("[Resources] YouTube search failed: %s", e)

        # Coursera catalog
        try:
            resp = await client.get(
                "https://api.coursera.org/api/courses.v1",
                params={"q": "search", "query": query, "limit": 1, "fields": "name,slug"},
            )
            if resp.status_code == 200:
                elements = resp.json().get("elements", [])
                if elements:
                    c = elements[0]
                    resources.append({
                        "title": c["name"],
                        "platform": "Coursera",
                        "url": f"https://www.coursera.org/learn/{c['slug']}",
                        "type": "paid",
                    })
        except Exception as e:
            logger.warning("[Resources] Coursera search failed: %s", e)

        # Udemy search URL
        if include_paid:
            resources.append({
                "title": f"Udemy: {query}",
                "platform": "Udemy",
                "url": f"https://www.udemy.com/courses/search/?q={quote_plus(query)}",
                "type": "paid",
            })

    return resources


# ---------- Step 4: Stamp topic IDs ----------

def _stamp_topic_ids(roadmap_data: dict) -> float:
    """Stamp topic_id on every topic, return total_hours."""
    total_hours = 0.0
    for phase in roadmap_data.get("phases", []):
        pi = phase.get("phase_index", 0)
        for skill_area in phase.get("skill_areas", []):
            ai = skill_area.get("skill_area_index", 0)
            for ti, topic in enumerate(skill_area.get("topics", [])):
                topic["topic_id"] = f"{pi}-{ai}-{ti}"
                hours = topic.get("estimated_hours", 2)
                total_hours += hours
    return total_hours


# ---------- Step 5: Generate knowledge base per skill area ----------

_KB_SYSTEM = """You are an expert at creating semantic search knowledge bases for learning topics.
Return ONLY a valid JSON object. No markdown. No text outside JSON."""

_KB_USER = """Generate a knowledge base for these learning topics:
{topics_json}

Return ONLY this JSON:
{{
  "topics": [
    {{
      "topic_id": "the topic_id from input",
      "title": "topic title",
      "subtopics": ["subtopic1", "subtopic2"],
      "keywords": ["keyword1", "keyword2"],
      "synonyms": ["synonym1"],
      "related_terms": ["term1", "term2"],
      "common_student_phrases": ["phrase a student might use when describing this topic"]
    }}
  ]
}}
No markdown. Just JSON."""


async def _generate_kb_for_topics(topics: list[dict]) -> list[dict]:
    import json
    topics_summary = json.dumps(
        [{"topic_id": t["topic_id"], "title": t["title"], "description": t.get("description", "")} for t in topics],
        indent=2,
    )
    result = await llm_call_with_json_retry(
        [{"role": "system", "content": _KB_SYSTEM}, {"role": "user", "content": _KB_USER.format(topics_json=topics_summary)}],
        temperature=0.4, max_tokens=2000,
    )
    return result.get("topics", [])


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
    """Full roadmap generation pipeline."""

    # Step 1: Generate structure (phases + skill_areas, no topics yet)
    structure = await _generate_structure(user, target_role, learning_goal, interests)

    # Step 2: Generate topics for each skill area (parallel per phase, sequential between phases for order)
    all_topic_tasks = []
    for phase in structure.get("phases", []):
        for skill_area in phase.get("skill_areas", []):
            all_topic_tasks.append((phase, skill_area))

    # Run topic generation concurrently (batch of small LLM calls)
    async def _fill_topics(phase, skill_area):
        topics = await _generate_topics_for_skill_area(skill_area, target_role, user)
        skill_area["topics"] = topics

    await asyncio.gather(*[_fill_topics(p, sa) for p, sa in all_topic_tasks])

    # Step 3: Stamp topic IDs
    total_hours = _stamp_topic_ids(structure)
    logger.info("[Roadmap] Total estimated hours: %.1f", total_hours)

    # Step 4: Attach resources (parallel for all topics)
    all_topics = []
    for phase in structure.get("phases", []):
        for skill_area in phase.get("skill_areas", []):
            for topic in skill_area.get("topics", []):
                all_topics.append(topic)

    async def _attach(topic):
        topic["resources"] = await _search_topic_resources(topic, include_paid)

    await asyncio.gather(*[_attach(t) for t in all_topics])
    logger.info("[Roadmap] Resources attached for %d topics", len(all_topics))

    # Step 5: Generate knowledge base (per skill area for smaller chunks)
    all_kb_topics = []
    for phase in structure.get("phases", []):
        for skill_area in phase.get("skill_areas", []):
            topics_in_sa = skill_area.get("topics", [])
            if topics_in_sa:
                try:
                    kb_topics = await _generate_kb_for_topics(topics_in_sa)
                    all_kb_topics.extend(kb_topics)
                except Exception as e:
                    logger.warning("[KB] Failed for skill_area '%s': %s", skill_area.get("title"), e)
    logger.info("[Roadmap] Knowledge base generated for %d topics", len(all_kb_topics))

    # Step 6: Persist to DB
    rm = GeneratedRoadmap(
        user_id=user.id,
        title=structure.get("title", f"{target_role} Roadmap"),
        description=structure.get("description", ""),
        target_role=target_role,
        learning_goal=learning_goal,
        interests=interests,
        hours_per_week=hours_per_week,
        include_paid=include_paid,
        total_estimated_hours=total_hours,
        roadmap_data=structure,
    )
    db.add(rm)
    await db.flush()

    if all_kb_topics:
        kb = KnowledgeBase(
            roadmap_id=rm.id,
            data={"topics": all_kb_topics},
        )
        db.add(kb)
        await db.flush()

    logger.info("[Roadmap] Saved roadmap id=%s with %d KB topics", rm.id, len(all_kb_topics))
    return rm
