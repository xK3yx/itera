import pytest
from unittest.mock import patch, MagicMock
from app.services.course_service import search_courses

pytestmark = pytest.mark.asyncio


async def test_search_courses_returns_list():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '''
    {
        "courses": [
            {
                "title": "React for Beginners",
                "platform": "Udemy",
                "url": "https://www.udemy.com/course/react",
                "duration": "10 hours",
                "level": "Beginner",
                "description": "Learn React from scratch",
                "why_recommended": "Great for beginners"
            }
        ]
    }
    '''

    with patch('app.services.course_service.client') as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        result = await search_courses("React", level="Beginner", max_results=1)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["title"] == "React for Beginners"


async def test_search_courses_has_required_fields():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '''
    {
        "courses": [
            {
                "title": "Python Basics",
                "platform": "freeCodeCamp",
                "url": "https://www.freecodecamp.org/python",
                "duration": "5 hours",
                "level": "Beginner",
                "description": "Learn Python",
                "why_recommended": "Free and comprehensive"
            }
        ]
    }
    '''

    with patch('app.services.course_service.client') as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        result = await search_courses("Python")
        assert len(result) > 0
        course = result[0]
        assert "title" in course
        assert "platform" in course
        assert "url" in course
        assert "duration" in course
        assert "level" in course


async def test_search_courses_invalid_json_returns_empty():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "not valid json"

    with patch('app.services.course_service.client') as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        result = await search_courses("React")
        assert result == []


async def test_search_courses_api_error_returns_empty():
    with patch('app.services.course_service.client') as mock_client:
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        result = await search_courses("React")
        assert result == []