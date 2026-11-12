"""
Shared LLM helpers: Groq client setup and JSON extraction from LLM output.
The provider order (LLM_PRIMARY) lives in app/services/llm_tracker.py.
"""
import json
import re
import logging
from openai import AsyncOpenAI, OpenAI
from app.config import get_settings

logger = logging.getLogger(__name__)

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def groq_kwargs(model: str, max_tokens: int) -> dict:
    """Extra request options for Groq.

    Reasoning models (gpt-oss, qwen3) spend output tokens on hidden reasoning
    before answering, so keep reasoning short and leave headroom for it.
    Otherwise a small max_tokens budget can produce an empty answer.
    """
    if model.startswith("openai/gpt-oss"):
        return {"max_tokens": max_tokens + 1024, "extra_body": {"reasoning_effort": "low"}}
    if model.startswith("qwen/qwen3"):
        return {"max_tokens": max_tokens + 1024, "extra_body": {"reasoning_effort": "none"}}
    return {"max_tokens": max_tokens}


def groq_client(async_client: bool = True):
    """Build a Groq client that retries rate-limit (429) errors.

    The OpenAI SDK waits for Groq's retry-after header between attempts,
    so extra retries ride out the free tier's tokens-per-minute limit.
    """
    s = get_settings()
    cls = AsyncOpenAI if async_client else OpenAI
    return cls(base_url=_GROQ_BASE_URL, api_key=s.groq_api_key, max_retries=s.groq_max_retries)


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
