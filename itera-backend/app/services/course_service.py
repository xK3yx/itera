import json
from app.services.llm_client import async_chat_complete, extract_and_parse_json

COURSE_SEARCH_PROMPT = """You are an expert learning resource curator.
Your job is to find the best online courses and learning resources for a given topic.

You must respond with a valid JSON object in this exact format:
{
  "courses": [
    {
      "title": "Exact course title",
      "platform": "Platform name (Coursera, Udemy, freeCodeCamp, YouTube, edX, Pluralsight, official docs)",
      "url": "https://actual-url.com",
      "duration": "X hours",
      "level": "Beginner / Intermediate / Advanced",
      "description": "What the course covers",
      "why_recommended": "Why this is a great resource for this topic"
    }
  ]
}

STRICT RULES:
- Respond with valid JSON only — no text outside the JSON
- Never wrap response in markdown code fences
- Only recommend real, currently available courses
- Prioritize free resources (freeCodeCamp, YouTube, official docs) first
- Then paid platforms (Udemy, Coursera) if they are well known for this topic
- Always include the exact URL
- Match the level to what was requested if specified"""


async def search_courses(
    query: str,
    level: str = None,
    max_results: int = 5
) -> list[dict]:
    """Search for courses using AI."""
    try:
        level_instruction = f"Focus on {level} level courses." if level else "Include a mix of levels."

        prompt = f"""Find the {max_results} best online courses and learning resources for: "{query}"
{level_instruction}

Return exactly {max_results} courses."""

        raw = await async_chat_complete(
            messages=[
                {"role": "system", "content": COURSE_SEARCH_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2048,
        )

        parsed = extract_and_parse_json(raw)
        return parsed.get("courses", [])

    except (ValueError, json.JSONDecodeError):
        return []
    except Exception:
        return []
