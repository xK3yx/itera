from groq import AsyncGroq
import json
import re
from app.config import get_settings

settings = get_settings()

client = AsyncGroq(api_key=settings.groq_api_key)

SYSTEM_PROMPT = """You are Itera, an expert learning coach and curriculum designer.
Your job is to analyze a user's existing skills and experience, then create a
personalized learning roadmap to help them reach their goal.

CONVERSATION PHASE (first 2-3 messages):
- Greet the user warmly on the first message
- Ask about their current skills and experience level
- Ask about what they want to learn and why
- Ask about how many hours per week they can dedicate
- Be encouraging and professional
- Keep questions focused, ask one or two at a time
- Once you have enough information, generate the roadmap immediately

ROADMAP GENERATION RULES:
- Generate the roadmap as soon as you have: current skills, learning goal, and available time
- Time estimates MUST be adjusted to the user's experience level:
  * Beginners: full time estimates
  * Intermediate: reduce by 20-30% for topics they partially know
  * Advanced/Seniors: reduce by 40-60% for foundational topics
- Order skill areas from foundational to advanced
- Each topic must have 1-2 real course recommendations
- Courses must be from: Coursera, Udemy, freeCodeCamp, YouTube, or official docs
- total_estimated_hours must equal the sum of all skill area estimated_hours
- estimated_weeks = total_estimated_hours / weekly_hours (rounded up)

Always respond with a valid JSON object in one of these two formats:

Format 1 - Still gathering info:
{
  "ready": false,
  "message": "Your conversational response here"
}

Format 2 - Ready to generate roadmap:
{
  "ready": true,
  "message": "Brief encouraging message about their roadmap",
  "roadmap": {
    "goal": "Specific learning goal",
    "total_estimated_hours": 120,
    "weekly_hours": 10,
    "estimated_weeks": 12,
    "skill_areas": [
      {
        "name": "Skill area name",
        "description": "Why this area matters for their goal",
        "estimated_hours": 30,
        "topics": [
          {
            "name": "Topic name",
            "estimated_hours": 5,
            "description": "What they will learn",
            "why_relevant": "Why this matters given their background",
            "courses": [
              {
                "title": "Exact course title",
                "platform": "Coursera",
                "url": "https://www.coursera.org/learn/example",
                "duration": "10 hours",
                "level": "Beginner",
                "why_recommended": "Why this suits them specifically"
              }
            ]
          }
        ]
      }
    ]
  }
}

STRICT RULES:
- Respond with valid JSON only — absolutely no text outside the JSON
- Never wrap response in markdown code fences
- Never include comments inside the JSON
- Always include the message field in both formats
- Courses must be real and currently available"""

DISCUSSION_SYSTEM_PROMPT = """You are Itera, an expert learning coach. You have already generated a personalized learning roadmap for this user (provided below as context).

Your role now is to help the user understand and navigate their roadmap. You can:
- Explain why a specific course or topic was included
- Describe what a course covers and what they will learn from it
- Clarify why a skill area is important for their specific goal
- Give more detail about any topic, concept, or resource in the roadmap
- Suggest how to approach a specific topic or course
- Answer any questions about their learning journey

Be friendly, encouraging, and specific — always reference the actual roadmap content in your answers.

Always respond with a valid JSON object in this exact format:
{
  "ready": false,
  "message": "Your helpful response here"
}

STRICT RULES:
- Respond with valid JSON only — absolutely no text outside the JSON
- Never wrap response in markdown code fences
- Never include comments inside the JSON
- The "ready" field must always be false
- Never generate a new roadmap"""


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
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]

            for msg in conversation_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

            messages.append({
                "role": "user",
                "content": user_message
            })

            response = await self.client.chat.completions.create(
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
            try:
                match = re.search(r'\{.*\}', raw, re.DOTALL)
                if match:
                    parsed = json.loads(match.group())
                    if "ready" not in parsed:
                        parsed["ready"] = False
                    if "message" not in parsed:
                        parsed["message"] = raw
                    return parsed
            except Exception:
                pass
            return {
                "ready": False,
                "message": raw
            }
        except Exception as e:
            return {
                "ready": False,
                "message": f"I encountered an error. Please try again. ({str(e)})"
            }

    async def process_followup_message(
        self,
        user_message: str,
        conversation_history: list[dict],
        roadmap_data: dict
    ) -> dict:
        try:
            roadmap_context = f"\n\nUSER'S ROADMAP:\n{json.dumps(roadmap_data, indent=2)}"
            messages = [{"role": "system", "content": DISCUSSION_SYSTEM_PROMPT + roadmap_context}]

            # Include recent conversation history, truncating large messages (raw roadmap JSON)
            recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
            for msg in recent_history:
                content = msg["content"]
                if len(content) > 1500:
                    content = content[:300] + "... [roadmap generation response truncated]"
                messages.append({"role": msg["role"], "content": content})

            messages.append({"role": "user", "content": user_message})

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1024
            )

            raw = response.choices[0].message.content.strip()
            clean = re.sub(r"```json|```", "", raw).strip()
            parsed = json.loads(clean)

            parsed["ready"] = False
            parsed.pop("roadmap", None)
            if "message" not in parsed:
                parsed["message"] = raw

            return parsed

        except json.JSONDecodeError:
            try:
                match = re.search(r'\{.*\}', raw, re.DOTALL)
                if match:
                    parsed = json.loads(match.group())
                    parsed["ready"] = False
                    parsed.pop("roadmap", None)
                    if "message" not in parsed:
                        parsed["message"] = raw
                    return parsed
            except Exception:
                pass
            return {"ready": False, "message": raw}
        except Exception as e:
            return {
                "ready": False,
                "message": f"I encountered an error. Please try again. ({str(e)})"
            }

    async def test_connection(self) -> tuple[bool, str]:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Say hello in one word."}],
                max_tokens=10
            )
            return True, response.choices[0].message.content
        except Exception as e:
            return False, str(e)

    async def test_roadmap_generation(self) -> dict:
        test_history = [
            {
                "role": "assistant",
                "content": '{"ready": false, "message": "Welcome to Itera! I\'m here to help you create a personalized learning roadmap. Could you tell me about your current skills and experience?"}'
            },
            {
                "role": "user",
                "content": "I have 5 years of backend development experience with Python and Django. I'm comfortable with REST APIs, databases, and server-side logic."
            },
            {
                "role": "assistant",
                "content": '{"ready": false, "message": "That\'s a strong foundation! What do you want to learn next, and how many hours per week can you dedicate to learning?"}'
            }
        ]

        test_message = "I want to learn React and frontend development. I can dedicate about 10 hours per week."

        return await self.process_message(test_message, test_history)


ai_service = AIService()
