"""Resource selection: English only, on topic, ranked, with honest fallbacks. No API key needed."""
import json

import httpx
import pytest

from app.services import resource_search as rs


# ---------- Language and topic rules ----------

@pytest.mark.parametrize("title", [
    "সি প্রোগ্রামিং Bangla Full Course | সবার জন্য সি",
    "पायथन ट्यूटोरियल हिंदी में",
    "Python Tutorial in Hindi for Beginners",
    "Curso de Python desde cero",
    "Python para iniciantes - Aula 1",
    "Belajar Python Dasar untuk Pemula",
    "Python Programmieren lernen für Anfänger",
    "Programação em Python",
])
def test_rejects_non_english_titles(title):
    assert not rs.is_english_title(title)


@pytest.mark.parametrize("title", [
    "Python for Beginners – Full Course [Programming Tutorial]",
    "SQL Tutorial - Full Database Course for Beginners",
    "Learn C++ Programming | Data Structures & Algorithms",
])
def test_accepts_english_titles(title):
    assert rs.is_english_title(title)


def test_youtube_language_fields_must_be_english_when_present():
    assert rs.is_english_metadata("en", "en-US")
    assert rs.is_english_metadata(None, None)
    assert not rs.is_english_metadata("hi", None)
    assert not rs.is_english_metadata("en", "bn")


def test_topic_language_comes_from_topic_then_context():
    assert rs.topic_language("Understanding Variables", "intro to variables",
                             "Basic Programming Concepts", "Foundations of Programming & Python") == "python"
    assert rs.topic_language("Window functions in SQL", "", "Python for Data") == "sql"
    assert rs.topic_language("Learn C++ templates", "") == "c++"
    assert rs.topic_language("JavaScript closures", "") == "javascript"
    assert rs.topic_language("Version control with Git", "", "Team workflow") is None


def test_build_query_adds_the_language_once():
    assert rs.build_query("intro to variables and data types", "python") == "intro to variables and data types python"
    assert rs.build_query("python decorators", "python") == "python decorators"
    assert rs.build_query("git branching", None) == "git branching"


def test_rejects_a_course_in_a_different_language():
    q = "intro to variables and data types python"
    assert not rs.is_on_topic("C Programming Full Course for Beginners", "", q, "python")
    assert not rs.is_on_topic("Java Tutorial for Beginners", "", q, "python")
    assert rs.is_on_topic("Python for Beginners - Full Course", "", q, "python")
    assert rs.is_on_topic("Variables and Data Types explained", "", q, "python")


def test_rejects_off_topic_results():
    assert not rs.is_on_topic("Lofi beats to study to", "chill music", "docker networking", None)
    assert rs.is_on_topic("Docker Networking Deep Dive", "", "docker networking", None)


# ---------- Ranking ----------

def _video(title, channel, minutes=60, views=100_000, vid="v"):
    return {"id": vid, "format": "video", "title": title, "description": "", "channel": channel,
            "languages": ["en"], "minutes": minutes, "views": views}


def test_trusted_educator_outranks_a_more_viewed_unknown_channel():
    q = "python decorators"
    picked = rs.select([
        _video("Python Decorators Full Course", "Random Uploads", views=5_000_000, vid="a"),
        _video("Python Decorators Tutorial", "Corey Schafer", views=50_000, vid="b"),
    ], q, "python", limit=2)
    assert [c["id"] for c in picked] == ["b", "a"]


def test_short_clips_rank_below_full_courses():
    q = "python decorators"
    picked = rs.select([
        _video("Python decorators in 60 seconds", "Chan A", minutes=1, vid="short"),
        _video("Python decorators complete course", "Chan B", minutes=90, vid="long"),
    ], q, "python", limit=2)
    assert picked[0]["id"] == "long"


def test_keeps_one_result_per_channel():
    q = "python decorators"
    picked = rs.select([
        _video("Python Decorators Part 1", "Same", vid="1"),
        _video("Python Decorators Part 2", "Same", vid="2"),
        _video("Python Decorators", "Other", vid="3"),
    ], q, "python", limit=2)
    assert len({c["channel"] for c in picked}) == 2


def test_iso_durations():
    assert rs._iso_minutes("PT1H30M") == 90
    assert rs._iso_minutes("PT45S") == 0.75
    assert rs._iso_minutes("P1DT2H") == 1560
    assert rs._iso_minutes("") == 0


# ---------- End to end against a fake YouTube API ----------

def _fake_youtube(playlists, fcc_videos, details):
    def handler(request: httpx.Request) -> httpx.Response:
        p = request.url.params
        assert p.get("key") == "test-key"
        path = request.url.path
        if path.endswith("/search"):
            assert p["relevanceLanguage"] == "en"
            if p.get("channelId") == rs.FREECODECAMP_CHANNEL_ID:
                items = fcc_videos
            elif p["type"] == "playlist":
                items = playlists
            else:
                items = []
            return httpx.Response(200, json={"items": items})
        ids = p["id"].split(",")
        return httpx.Response(200, json={"items": [details[i] for i in ids if i in details]})
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _pl(pid, title, channel):
    return {"id": {"playlistId": pid}, "snippet": {"title": title, "description": "", "channelTitle": channel}}


def _vd(vid, title, channel="freeCodeCamp.org"):
    return {"id": {"videoId": vid}, "snippet": {"title": title, "description": "", "channelTitle": channel}}


@pytest.mark.asyncio
async def test_find_resources_end_to_end():
    playlists = [
        _pl("bangla", "সি প্রোগ্রামিং Bangla Full Course", "Bangla Coder"),
        _pl("hindi", "Python Full Course in Hindi", "Desi Coder"),
        _pl("good", "Python Programming Full Course", "Corey Schafer"),
        _pl("ok", "Python Variables and Data Types", "Small Channel"),
    ]
    fcc = [_vd("short", "Python variables in 5 minutes"), _vd("course", "Python for Beginners – Full Course")]
    details = {
        "good": {"id": "good", "snippet": {}, "contentDetails": {"itemCount": 40}},
        "ok": {"id": "ok", "snippet": {"defaultLanguage": "en"}, "contentDetails": {"itemCount": 3}},
        "short": {"id": "short", "snippet": {}, "contentDetails": {"duration": "PT5M"}, "statistics": {"viewCount": "9"}},
        "course": {"id": "course", "snippet": {"defaultAudioLanguage": "en"},
                   "contentDetails": {"duration": "PT4H26M"}, "statistics": {"viewCount": "4000000"}},
    }
    async with _fake_youtube(playlists, fcc, details) as client:
        out = await rs.find_resources(client, "test-key", "intro to variables and data types python", "python")

    youtube = [r for r in out if r["platform"] == "YouTube"]
    assert [r["url"] for r in youtube] == [
        "https://www.youtube.com/playlist?list=good",
        "https://www.youtube.com/playlist?list=ok",
    ]
    fcc_link = next(r for r in out if r["platform"] == "freeCodeCamp")
    assert fcc_link["url"] == "https://www.youtube.com/watch?v=course"
    assert fcc_link["title"] == "Python for Beginners – Full Course"
    assert "freecodecamp.org/news/search" not in json.dumps(out)


@pytest.mark.asyncio
async def test_fallbacks_are_honest_and_never_empty_pages():
    out = await rs.find_resources(None, "", "docker networking", None)  # no API key
    by_platform = {r["platform"]: r for r in out}
    assert by_platform["YouTube"]["format"] == "search"
    assert "in+English" in by_platform["YouTube"]["url"]
    assert by_platform["freeCodeCamp"]["url"] == rs.FREECODECAMP_BROWSE_URL
    assert by_platform["Coursera"]["title"].startswith("Search Coursera")
    assert "lang=en" in by_platform["Udemy"]["url"]


@pytest.mark.asyncio
async def test_api_errors_fall_back_instead_of_failing():
    def handler(request):
        return httpx.Response(403, json={"error": "quotaExceeded"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        out = await rs.find_resources(client, "test-key", "docker networking", None)
    assert {r["platform"] for r in out} == {"YouTube", "freeCodeCamp", "Coursera", "Udemy"}
    assert all(r["format"] in ("search", "browse") for r in out)
