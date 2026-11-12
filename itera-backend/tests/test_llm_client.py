from app.services.llm_client import groq_kwargs


def test_reasoning_models_get_token_headroom_and_low_effort():
    args = groq_kwargs("openai/gpt-oss-120b", 200)
    assert args["max_tokens"] > 200
    assert args["extra_body"] == {"reasoning_effort": "low"}


def test_non_reasoning_models_keep_requested_budget():
    assert groq_kwargs("some/other-model", 200) == {"max_tokens": 200}
