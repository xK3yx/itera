from openai import AsyncOpenAI, OpenAI

from app.config import get_settings
from app.services.llm_client import groq_client, groq_kwargs


def test_groq_client_retries_rate_limits():
    expected = get_settings().groq_max_retries
    assert expected > 2  # more than the SDK default, to ride out 429s
    client = groq_client()
    assert isinstance(client, AsyncOpenAI)
    assert client.max_retries == expected
    sync_client = groq_client(async_client=False)
    assert isinstance(sync_client, OpenAI)
    assert sync_client.max_retries == expected


def test_reasoning_models_get_token_headroom_and_low_effort():
    args = groq_kwargs("openai/gpt-oss-120b", 200)
    assert args["max_tokens"] > 200
    assert args["extra_body"] == {"reasoning_effort": "low"}


def test_non_reasoning_models_keep_requested_budget():
    assert groq_kwargs("some/other-model", 200) == {"max_tokens": 200}
