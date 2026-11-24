"""
Find real, English, on-topic learning resources for a roadmap topic.

Every link comes from an API result or is an honestly labelled search/browse
page. Nothing is guessed. YouTube results are filtered (English only, on topic,
no clashing programming language) and then ranked, preferring well-known
educational channels and real courses over short clips.

Quota: each YouTube search costs 100 units no matter how many results it
returns, so we ask for 10 and filter ourselves. The detail lookups
(playlists.list / videos.list) cost 1 unit for the whole batch.
"""
from __future__ import annotations

import html
import logging
import math
import re
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)

YT_API = "https://www.googleapis.com/youtube/v3"
FREECODECAMP_CHANNEL_ID = "UC8butISFwT-Wl7EV0hUK0BQ"
FREECODECAMP_BROWSE_URL = "https://www.freecodecamp.org/learn"

# Bump when the selection rules change, so cached results from older rules are not reused.
RULES_VERSION = "v2"

# Lower-cased channel titles of educators known for clear, English, full-length courses.
TRUSTED_CHANNELS = {
    "freecodecamp.org", "cs50", "mit opencourseware", "stanford online", "harvard university",
    "corey schafer", "programming with mosh", "traversy media", "fireship", "the net ninja",
    "net ninja", "tech with tim", "bro code", "web dev simplified", "kevin powell",
    "techworld with nana", "3blue1brown", "statquest with josh starmer", "sentdex",
    "andrej karpathy", "deeplearningai", "neetcode", "abdul bari", "derek banas",
    "academind", "the coding train", "hussein nasser", "arjancodes", "mcoding",
    "computerphile", "google for developers", "microsoft developer", "aws events",
    "ibm technology", "simplilearn", "edureka!", "great learning", "amigoscode",
}

# Programming languages, for keeping a topic's language consistent with its results.
# Patterns are matched against lower-cased text.
LANGUAGES: dict[str, str] = {
    "python": r"\bpython\b",
    "javascript": r"\bjavascript\b|\bjs\b",
    "typescript": r"\btypescript\b",
    "java": r"\bjava\b(?!\s*script)",
    "c++": r"\bc\+\+|\bcpp\b",
    "c#": r"\bc#|\bc sharp\b|\bcsharp\b",
    "c": r"(?<![\w+#])c(?= programming| language| tutorial| course| for beginners)",
    "go": r"\bgolang\b|\bgo (?:programming|language|tutorial|course)\b",
    "rust": r"\brust\b",
    "php": r"\bphp\b",
    "ruby": r"\bruby\b",
    "kotlin": r"\bkotlin\b",
    "swift": r"\bswift\b",
    "dart": r"\bdart\b",
    "scala": r"\bscala\b",
    "sql": r"\bsql\b|\bmysql\b|\bpostgres(?:ql)?\b",
}
_LANG_RE = {name: re.compile(pat) for name, pat in LANGUAGES.items()}

# Words that mark a Latin-script title as being in, or taught in, another language.
NON_ENGLISH_MARKERS = re.compile(
    r"\b(?:hindi|urdu|bangla|bengali|tamil|telugu|kannada|malayalam|marathi|gujarati|punjabi|"
    r"nepali|sinhala|arabic|español|espanol|spanish|portugu[eê]s|portuguese|fran[cç]ais|french|"
    r"deutsch|german|italiano|italian|t[uü]rk[cç]e|turkish|indonesia|bahasa|tagalog|filipino|"
    r"vietnamese|ti[eế]ng vi[eệ]t|russian|русский|polski|polish|"
    r"curso|completo|desde cero|para principiantes|aula|programa[cç][aã]o|iniciantes|"
    r"kursus|belajar|dasar|pemula|dersleri|e[gğ]itimi|lernen|anf[aä]nger|f[uü]r|"
    r"d[ée]butants?|cours|corso|principianti|tutoriel)\b",
    re.IGNORECASE,
)

_STOPWORDS = {
    "a", "an", "and", "the", "to", "of", "for", "in", "on", "with", "how", "what", "is", "are",
    "intro", "introduction", "basics", "basic", "beginner", "beginners", "tutorial", "tutorials",
    "course", "courses", "full", "guide", "learn", "learning", "programming", "complete",
    "fundamentals", "using", "your", "from", "into", "via", "best", "practice", "practical",
}


# ---------- Pure helpers (unit-tested) ----------

def languages_in(text: str) -> set[str]:
    """Programming languages named in the text."""
    low = (text or "").lower()
    return {name for name, rx in _LANG_RE.items() if rx.search(low)}


def topic_language(*texts: str) -> str | None:
    """The main programming language of a topic, read from its own text first, then its context."""
    for text in texts:
        found = languages_in(text)
        if found:
            # Prefer the most specific match when e.g. both "c" and "c++" hit.
            for name in LANGUAGES:
                if name in found:
                    return name
    return None


def build_query(query: str, language: str | None) -> str:
    """Make sure the search names the topic's language, so 'variables and data types' becomes a Python search."""
    if language and language not in languages_in(query):
        return f"{query} {language}"
    return query


def is_english_title(title: str) -> bool:
    """English titles use ASCII letters only and carry no other-language marker words."""
    if any(ch.isalpha() and not ch.isascii() for ch in title):
        return False
    return not NON_ENGLISH_MARKERS.search(title)


def is_english_metadata(*language_codes: str | None) -> bool:
    """YouTube's own language fields, when present, must be English."""
    codes = [c for c in language_codes if c]
    return all(c.lower().startswith("en") for c in codes)


def keywords(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9+#.]+", (text or "").lower())
    return {w.strip(".") for w in words if len(w) > 2 and w not in _STOPWORDS}


def is_on_topic(title: str, description: str, query: str, language: str | None) -> bool:
    """Shares a real keyword with the query, and does not teach a different language."""
    text = f"{title} {description}"
    if language:
        named = languages_in(title)
        if named and language not in named:
            return False
    wanted = keywords(query) - {language or ""}
    if not wanted:
        return True
    return bool(wanted & keywords(text)) or (language is not None and language in languages_in(title))


def is_trusted(channel_title: str) -> bool:
    return (channel_title or "").strip().lower() in TRUSTED_CHANNELS


def _iso_minutes(duration: str) -> float:
    """ISO 8601 duration (PT1H2M3S) to minutes."""
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration or "")
    if not m:
        return 0.0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 1440 + h * 60 + mi + s / 60


def score(candidate: dict, query: str) -> float:
    """Higher is better. Trusted educators first, then real courses, then topic fit and popularity."""
    s = 0.0
    if is_trusted(candidate.get("channel", "")):
        s += 5
    if candidate["format"] == "playlist":
        items = candidate.get("item_count") or 0
        s += 2 if items >= 5 else (0 if items else 0.5)
    else:
        minutes = candidate.get("minutes", 0)
        s += 2 if minutes >= 40 else (1 if minutes >= 20 else -2)
        views = candidate.get("views") or 0
        s += min(math.log10(views + 1) / 2, 3)
    s += min(len(keywords(query) & keywords(candidate["title"])), 3) * 0.5
    return s


def select(candidates: list[dict], query: str, language: str | None, limit: int) -> list[dict]:
    """Drop non-English or off-topic results, rank the rest, and keep one per channel."""
    kept = [
        c for c in candidates
        if is_english_title(c["title"])
        and is_english_metadata(*c.get("languages", ()))
        and is_on_topic(c["title"], c.get("description", ""), query, language)
    ]
    kept.sort(key=lambda c: score(c, query), reverse=True)
    out, channels = [], set()
    for c in kept:
        if c.get("channel") in channels:
            continue
        channels.add(c.get("channel"))
        out.append(c)
        if len(out) == limit:
            break
    return out


# ---------- YouTube API ----------

async def _yt_search(client: httpx.AsyncClient, key: str, q: str, kind: str, **extra) -> list[dict]:
    params = {
        "part": "snippet", "q": q, "type": kind, "maxResults": 10,
        "relevanceLanguage": "en", "safeSearch": "moderate", "key": key, **extra,
    }
    resp = await client.get(f"{YT_API}/search", params=params)
    if resp.status_code != 200:
        raise RuntimeError(f"YouTube search returned {resp.status_code}")
    out = []
    for item in resp.json().get("items", []):
        sn = item.get("snippet", {})
        item_id = item.get("id", {})
        out.append({
            "id": item_id.get("playlistId") or item_id.get("videoId"),
            "format": "playlist" if kind == "playlist" else "video",
            "title": html.unescape(sn.get("title", "")),
            "description": html.unescape(sn.get("description", "")),
            "channel": html.unescape(sn.get("channelTitle", "")),
            "languages": [],
        })
    return [c for c in out if c["id"]]


async def _yt_details(client: httpx.AsyncClient, key: str, candidates: list[dict]) -> None:
    """Add language, length and popularity in one batched call (1 quota unit)."""
    if not candidates:
        return
    kind = candidates[0]["format"]
    endpoint = "playlists" if kind == "playlist" else "videos"
    part = "snippet,contentDetails" if kind == "playlist" else "snippet,contentDetails,statistics"
    resp = await client.get(
        f"{YT_API}/{endpoint}",
        params={"part": part, "id": ",".join(c["id"] for c in candidates), "key": key},
    )
    if resp.status_code != 200:
        return
    by_id = {it["id"]: it for it in resp.json().get("items", [])}
    for c in candidates:
        it = by_id.get(c["id"])
        if not it:
            continue
        sn, cd = it.get("snippet", {}), it.get("contentDetails", {})
        c["languages"] = [sn.get("defaultAudioLanguage"), sn.get("defaultLanguage")]
        if kind == "playlist":
            c["item_count"] = cd.get("itemCount", 0)
        else:
            c["minutes"] = _iso_minutes(cd.get("duration", ""))
            c["views"] = int(it.get("statistics", {}).get("viewCount", 0) or 0)


def _youtube_resource(c: dict) -> dict:
    if c["format"] == "playlist":
        url = f"https://www.youtube.com/playlist?list={c['id']}"
    else:
        url = f"https://www.youtube.com/watch?v={c['id']}"
    return {"title": c["title"], "platform": "YouTube", "url": url, "type": "free",
            "format": c["format"], "channel": c["channel"]}


async def find_youtube(client, key: str, query: str, language: str | None) -> list[dict]:
    """Up to two ranked, English, on-topic YouTube courses (playlists first, then long videos)."""
    playlists = await _yt_search(client, key, f"{query} full course", "playlist")
    await _yt_details(client, key, playlists)
    picked = select(playlists, query, language, limit=2)
    if not picked:
        videos = await _yt_search(client, key, f"{query} full course", "video", videoDuration="long")
        await _yt_details(client, key, videos)
        picked = select(videos, query, language, limit=2)
    return [_youtube_resource(c) for c in picked]


async def find_freecodecamp(client, key: str, query: str, language: str | None) -> dict | None:
    """A real freeCodeCamp course from its YouTube channel, where most of its full courses live."""
    videos = await _yt_search(client, key, query, "video", channelId=FREECODECAMP_CHANNEL_ID)
    await _yt_details(client, key, videos)
    long_enough = [v for v in videos if v.get("minutes", 0) >= 20]
    picked = select(long_enough, query, language, limit=1)
    if not picked:
        return None
    v = picked[0]
    return {"title": v["title"], "platform": "freeCodeCamp",
            "url": f"https://www.youtube.com/watch?v={v['id']}", "type": "free", "format": "video"}


# ---------- Public entry point ----------

async def find_resources(client: httpx.AsyncClient, yt_key: str, query: str, language: str | None) -> list[dict]:
    """All resources for one topic. `query` should already name the topic's language (see build_query)."""
    resources: list[dict] = []
    fcc = None
    if yt_key:
        try:
            resources += await find_youtube(client, yt_key, query, language)
        except Exception as e:
            logger.warning("[Resources] YouTube search failed for '%s': %s", query, e)
        try:
            fcc = await find_freecodecamp(client, yt_key, query, language)
        except Exception as e:
            logger.warning("[Resources] freeCodeCamp search failed for '%s': %s", query, e)

    if not any(r["platform"] == "YouTube" for r in resources):
        resources.append({
            "title": f"Search YouTube: {query} (English)",
            "platform": "YouTube",
            "url": "https://www.youtube.com/results?search_query="
                   + quote_plus(f"{query} full course in English"),
            "type": "free",
            "format": "search",
        })

    resources.append(fcc or {
        "title": "Browse freeCodeCamp's free courses",
        "platform": "freeCodeCamp",
        "url": FREECODECAMP_BROWSE_URL,
        "type": "free",
        "format": "browse",
    })

    resources.append({
        "title": f"Search Coursera: {query}",
        "platform": "Coursera",
        "url": f"https://www.coursera.org/search?query={quote_plus(query)}&language=English",
        "type": "paid",
        "format": "search",
    })
    resources.append({
        "title": f"Search Udemy: {query}",
        "platform": "Udemy",
        "url": f"https://www.udemy.com/courses/search/?q={quote_plus(query)}&lang=en",
        "type": "paid",
        "format": "search",
    })
    return resources
