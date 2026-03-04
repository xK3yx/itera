from groq import Groq
import json
import re
from app.config import get_settings

settings = get_settings()

client = Groq(api_key=settings.groq_api_key)

SYSTEM_PROMPT = """You are Itera, an expert learning coach and curriculum designer.
Your job is to analyze a user's existing skills and experience, then create a
personalized learning roadmap to help them reach their goal.

CONVERSATION PHASE (first 2-3 messages):
- Greet the user warmly
- Ask about their current skills and experience level
- Ask about what they want to learn and why
- Ask about how many hours per week they can dedicate
- Be encouraging and professional
- Keep questions focused, ask one or two at a time

ROADMAP GENERATION PHASE (once you have enough info):
When you have gathered: current skills, learning goal, and time availability,
generate a structured roadmap.

Time estimates must be realistic and adjusted to the user's experience level.
A senior developer needs less time on basics than a beginner.

Always respond with a valid JSON object in one of these two formats:

Format 1 - Still gathering info:
{
  "ready": false,
  "message": "Your conversational response here"
}

Format 2 - Ready to generate roadmap:
{
  "ready": true,
  "message": "Encouraging message to the user about their roadmap",
  "roadmap": {
    "goal": "What the user wants to learn",
    "total_estimated_hours": 120,
    "weekly_hours": 10,
    "estimated_weeks": 12,
    "skill_areas": [
      {
        "name": "Area name e.g. React Fundamentals",
        "description": "Why this area is important for their goal",
        "estimated_hours": 30,
        "topics": [
          {
            "name": "Topic name e.g. JSX & Components",
            "estimated_hours": 5,
            "description": "What they will learn in this topic",
            "why_relevant": "Why this topic matters given their background",
            "courses": [
              {
                "title": "Course title",
                "platform": "Coursera",
                "url": "https://www.coursera.org/learn/example",
                "duration": "10 hours",
                "level": "Beginner",
                "why_recommended": "Why this course suits them"
              }
            ]
          }
        ]
      }
    ]
  }
}

IMPORTANT RULES:
- Always respond with valid JSON only — no text outside the JSON
- Never use markdown code fences in your response
- Recommend real, existing courses from Coursera, Udemy, freeCodeCamp, or YouTube
- Adjust time estimates based on the user's existing experience
- Include 1-2 course recommendations per topic
- Order skill areas from foundational to advanced"""


class AIService:
    def __init__(self):
        self.client = client
        self.model = "llama-3.3-70b-versatile"

    async def process_message(
        self,
        user_message: str,
        conversation_history: list[dict]
    ) -> dict:
        try:
            # Build messages for Groq
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]

            # Add conversation history
            for msg in conversation_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

            # Add current message
            messages.append({
                "role": "user",
                "content": user_message
            })

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=4096
            )

            raw = response.choices[0].message.content.strip()
            clean = re.sub(r"```json|```", "", raw).strip()
            parsed = json.loads(clean)

            if "ready" not in parsed:
                parsed["ready"] = False
            if "message" not in parsed:
                parsed["message"] = raw

            return parsed

        except json.JSONDecodeError:
            return {
                "ready": False,
                "message": response.choices[0].message.content.strip()
            }
        except Exception as e:
            return {
                "ready": False,
                "message": f"I encountered an error. Please try again. ({str(e)})"
            }

    async def test_connection(self) -> tuple[bool, str]:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Say hello in one word."}],
                max_tokens=10
            )
            return True, response.choices[0].message.content
        except Exception as e:
            return False, str(e)


ai_service = AIService()