"""
Unified LLM client — Ollama primary, Groq fallback.
Uses the openai Python library as a drop-in for both.
"""
import json
import re
import logging
from openai import AsyncOpenAI, OpenAI
from app.config import get_settings

logger = logging.getLogger(__name__)

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_GROQ_MODEL = "llama-3.3-70b-versatile"


def extract_and_parse_json(raw_text: str) -> dict:
    """
    Robustly extract and parse JSON from LLM output.
    Handles: markdown fences, trailing commas, truncated output, extra text before/after JSON.
    """
    text = raw_text.strip()

    # 1. Remove markdown code fences
    text = re.sub(r'^```(?:json)?\s*\n?', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n?```\s*$', '', text, flags=re.MULTILINE)
    text = text.strip()

    # 2. Find the actual JSON object/array boundaries
    start = None
    for i, c in enumerate(text):
        if c in ('{', '['):
            start = i
            break

    if start is None:
        raise ValueError("No JSON object found in LLM output")

    # Find the matching closing bracket
    open_char = text[start]
    close_char = '}' if open_char == '{' else ']'
    depth = 0
    end = None
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        c = text[i]
        if escape_next:
            escape_next = False
            continue
        if c == '\\':
            escape_next = True
            continue
        if c == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == open_char:
            depth += 1
        elif c == close_char:
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end is None:
        # JSON was truncated — try to close it
        text_chunk = text[start:]
        open_braces = text_chunk.count('{') - text_chunk.count('}')
        open_brackets = text_chunk.count('[') - text_chunk.count(']')
        text_chunk += ']' * max(0, open_brackets)
        text_chunk += '}' * max(0, open_braces)
        json_str = text_chunk
    else:
        json_str = text[start:end]

    # 3. Fix trailing commas (,} or ,])
    json_str = re.sub(r',\s*([\]}])', r'\1', json_str)

    # 4. Try to parse
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # 5. Last resort: try line-by-line cleanup
        lines = json_str.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('//'):
                cleaned_lines.append(line)
        cleaned = '\n'.join(cleaned_lines)
        cleaned = re.sub(r',\s*([\]}])', r'\1', cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            raise ValueError(f"Could not parse JSON from LLM output. Raw start: {raw_text[:500]}...")


async def async_chat_complete(messages: list[dict], temperature: float = 0.7, max_tokens: int = 2048) -> str:
    """Call LLM with Ollama-first, Groq-fallback strategy. Returns raw text."""
    s = get_settings()
    kwargs = dict(messages=messages, temperature=temperature, max_tokens=max_tokens)

    # Try Ollama first
    try:
        client = AsyncOpenAI(base_url=f"{s.ollama_base_url}/v1", api_key="ollama")
        resp = await client.chat.completions.create(model=s.ollama_model, **kwargs)
        logger.info("[LLM] Ollama (%s) responded successfully", s.ollama_model)
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("[LLM] Ollama unreachable (%s) — falling back to Groq", exc)

    # Fallback to Groq
    if not s.groq_api_key:
        raise RuntimeError("Ollama is unreachable and GROQ_API_KEY is not configured")
    client = AsyncOpenAI(base_url=_GROQ_BASE_URL, api_key=s.groq_api_key)
    resp = await client.chat.completions.create(model=_GROQ_MODEL, **kwargs)
    logger.info("[LLM] Groq (%s) responded successfully", _GROQ_MODEL)
    return resp.choices[0].message.content.strip()


def sync_chat_complete(messages: list[dict], temperature: float = 0.7, max_tokens: int = 2048) -> str:
    """Synchronous version of async_chat_complete."""
    s = get_settings()
    kwargs = dict(messages=messages, temperature=temperature, max_tokens=max_tokens)

    try:
        client = OpenAI(base_url=f"{s.ollama_base_url}/v1", api_key="ollama")
        resp = client.chat.completions.create(model=s.ollama_model, **kwargs)
        logger.info("[LLM] Ollama (%s) responded successfully (sync)", s.ollama_model)
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("[LLM] Ollama unreachable (%s) — falling back to Groq (sync)", exc)

    if not s.groq_api_key:
        raise RuntimeError("Ollama is unreachable and GROQ_API_KEY is not configured")
    client = OpenAI(base_url=_GROQ_BASE_URL, api_key=s.groq_api_key)
    resp = client.chat.completions.create(model=_GROQ_MODEL, **kwargs)
    logger.info("[LLM] Groq (%s) responded successfully (sync)", _GROQ_MODEL)
    return resp.choices[0].message.content.strip()


async def llm_call_with_json_retry(messages: list[dict], temperature: float = 0.7, max_tokens: int = 2048, max_retries: int = 2) -> dict:
    """Call LLM and parse JSON response with retry on parse failure."""
    msgs = [dict(m) for m in messages]  # shallow copy
    for attempt in range(max_retries + 1):
        response = await async_chat_complete(msgs, temperature=temperature, max_tokens=max_tokens)
        try:
            parsed = extract_and_parse_json(response)
            logger.info("[LLM] JSON parsed successfully (attempt %d)", attempt + 1)
            return parsed
        except (ValueError, json.JSONDecodeError) as e:
            if attempt < max_retries:
                logger.warning("[LLM] JSON parse failed (attempt %d), retrying... Error: %s", attempt + 1, e)
                msgs[-1]["content"] += "\n\nCRITICAL: Your previous response was not valid JSON. Return ONLY a valid JSON object. No markdown, no explanation, no text outside the JSON."
            else:
                raise ValueError(f"LLM failed to produce valid JSON after {max_retries + 1} attempts: {e}")
