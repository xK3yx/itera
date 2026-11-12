"""LLM_PRIMARY decides which provider is tried first; the other is the fallback."""
import pytest

from app.config import Settings
from app.services import llm_tracker


def make_settings(**overrides) -> Settings:
    base = dict(secret_key="x", jwt_secret_key="y", database_url="sqlite://")
    # _env_file=None: ignore the developer's real .env so defaults are tested
    return Settings(_env_file=None, **{**base, **overrides})


def test_groq_is_primary_by_default():
    assert make_settings(groq_api_key="k").llm_provider_order == ["groq", "ollama"]


def test_ollama_can_be_primary():
    s = make_settings(groq_api_key="k", llm_primary="Ollama")
    assert s.llm_provider_order == ["ollama", "groq"]


def test_groq_is_skipped_without_api_key():
    assert make_settings(groq_api_key="").llm_provider_order == ["ollama"]


def _fake_providers(monkeypatch, order, failing=()):
    calls = []

    def provider(name):
        async def call(messages, temperature, max_tokens):
            calls.append(name)
            if name in failing:
                raise RuntimeError(f"{name} down")
            return f"answer from {name}", f"{name}-model", name
        return call

    monkeypatch.setattr(llm_tracker, "_PROVIDER_CALLS", {n: provider(n) for n in ("groq", "ollama")})
    monkeypatch.setattr(llm_tracker, "get_settings", lambda: make_settings(
        groq_api_key="k", llm_primary=order[0]))
    return calls


@pytest.mark.asyncio
async def test_primary_answers_without_touching_fallback(monkeypatch):
    calls = _fake_providers(monkeypatch, ["groq", "ollama"])
    _, _, provider = await llm_tracker._call_providers([], 0.5, 100)
    assert provider == "groq"
    assert calls == ["groq"]


@pytest.mark.asyncio
async def test_falls_back_when_primary_fails(monkeypatch):
    calls = _fake_providers(monkeypatch, ["groq", "ollama"], failing={"groq"})
    _, _, provider = await llm_tracker._call_providers([], 0.5, 100)
    assert provider == "ollama"
    assert calls == ["groq", "ollama"]


@pytest.mark.asyncio
async def test_raises_last_error_when_all_fail(monkeypatch):
    _fake_providers(monkeypatch, ["groq", "ollama"], failing={"groq", "ollama"})
    with pytest.raises(RuntimeError, match="ollama down"):
        await llm_tracker._call_providers([], 0.5, 100)
