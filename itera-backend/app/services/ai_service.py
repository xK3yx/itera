import google.generativeai as genai
import json
import re
from app.config import get_settings

settings = get_settings()

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)

SYSTEM_PROMPT = """You are Itera, an expert learning coach and curriculum designer. 
Your job is to analyze a user's existing skills and experience, then create a 
personalized learning roadmap to help them reach their goal.

During the conversation:
- Ask targeted questions to understand their current skill level
- Identify gaps between where they are and where they want to be
- Be encouraging and professional

When you have enough information (after 2-3 messages), generate a structured 
learning roadmap in the following JSON format:

{
  "ready": true,
  "roadmap": {
    "goal": "What the user wants to learn",
    "total_estimated_hours": 120,
    "skill_areas": [
      {
        "name": "Area name e.g. React Fundamentals",
        "estimated_hours": 30,
        "topics": [
          {
            "name": "Topic name e.g. JSX & Components",
            "estimated_hours": 5,
            "description": "Brief description of what to learn",
            "courses": [
              {
                "title": "Course title",
                "platform": "Coursera",
                "url": "https://coursera.org/...",
                "duration": "10 hours",
                "level": "Beginner"
              }
            ]
          }
        ]
      }
    ]
  }
}

If you still need more information, respond normally in plain text with:
{
  "ready": false,
  "message": "Your conversational response here asking for more info"
}

Always respond with valid JSON only — no extra text outside the JSON."""


class AIService:
    def __init__(self):
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_PROMPT
        )

    async def process_message(
        self,
        user_message: str,
        conversation_history: list[dict]
    ) -> dict:
        """
        Process a user message and return either a question or a full roadmap.
        conversation_history: list of {"role": "user"/"model", "parts": ["text"]}
        """
        try:
            # Build history for Gemini
            history = [
                {"role": msg["role"], "parts": [msg["content"]]}
                for msg in conversation_history
            ]

            # Start chat with history
            chat = self.model.start_chat(history=history)

            # Send the new message
            response = chat.send_message(user_message)
            raw = response.text.strip()

            # Strip markdown code fences if present
            clean = re.sub(r"^```json|^```|```$", "", raw, flags=re.MULTILINE).strip()

            # Parse JSON response
            parsed = json.loads(clean)
            return parsed

        except json.JSONDecodeError:
            # If Gemini didn't return valid JSON, treat as a plain message
            return {
                "ready": False,
                "message": response.text.strip()
            }
        except Exception as e:
            return {
                "ready": False,
                "message": f"Sorry, I encountered an error. Please try again. ({str(e)})"
            }
