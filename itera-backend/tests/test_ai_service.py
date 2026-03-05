import pytest
from unittest.mock import patch, MagicMock
from app.services.ai_service import AIService

pytestmark = pytest.mark.asyncio


async def test_process_message_returns_dict():
    service = AIService()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"ready": false, "message": "Hello! Tell me about your background."}'

    with patch.object(service.client.chat.completions, 'create', return_value=mock_response):
        result = await service.process_message("Hi", [])
        assert isinstance(result, dict)
        assert "ready" in result
        assert "message" in result


async def test_process_message_ready_false():
    service = AIService()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"ready": false, "message": "What do you want to learn?"}'

    with patch.object(service.client.chat.completions, 'create', return_value=mock_response):
        result = await service.process_message("I know Python", [])
        assert result["ready"] == False
        assert result["message"] == "What do you want to learn?"


async def test_process_message_ready_true():
    service = AIService()
    mock_roadmap = {
        "ready": True,
        "message": "Here is your roadmap!",
        "roadmap": {
            "goal": "Learn React",
            "total_estimated_hours": 100,
            "weekly_hours": 10,
            "estimated_weeks": 10,
            "skill_areas": []
        }
    }
    import json
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps(mock_roadmap)

    with patch.object(service.client.chat.completions, 'create', return_value=mock_response):
        result = await service.process_message("I want to learn React, 10hrs/week", [])
        assert result["ready"] == True
        assert "roadmap" in result


async def test_process_message_invalid_json_fallback():
    service = AIService()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "This is not JSON at all"

    with patch.object(service.client.chat.completions, 'create', return_value=mock_response):
        result = await service.process_message("Hi", [])
        assert isinstance(result, dict)
        assert "ready" in result


async def test_process_message_with_history():
    service = AIService()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"ready": false, "message": "Got it!"}'

    history = [
        {"role": "user", "content": "I know Python"},
        {"role": "assistant", "content": "Great! What do you want to learn?"}
    ]

    with patch.object(service.client.chat.completions, 'create', return_value=mock_response):
        result = await service.process_message("I want to learn React", history)
        assert isinstance(result, dict)


async def test_test_connection_success():
    service = AIService()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Hello"

    with patch.object(service.client.chat.completions, 'create', return_value=mock_response):
        connected, message = await service.test_connection()
        assert connected == True
        assert message == "Hello"


async def test_test_connection_failure():
    service = AIService()

    with patch.object(service.client.chat.completions, 'create', side_effect=Exception("API Error")):
        connected, message = await service.test_connection()
        assert connected == False
        assert "API Error" in message