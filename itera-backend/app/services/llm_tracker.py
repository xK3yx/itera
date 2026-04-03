"""
Tracked LLM call wrapper.
Every LLM call goes through tracked_llm_call() — logs to DB + console,
detects hallucinations, records latency/tokens/provider.
"""
import re
import time
import uuid
import logging
from typing import Optional

from app.services.llm_client import async_chat_complete, extract_and_parse_json
from app.config import get_settings

logger = logging.getLogger(__name__)


# ---------- Hallucination detection ----------

def detect_hallucinations(response: str, call_type: str) -> list:
    """Return a list of flagged issues found in the LLM response."""
    flags = []
    if not response:
        return flags

    response_lower = response.lower()

    # Hallucinated URLs — LLM-generated URLs are almost always fabricated
    urls = re.findall(r'https?://[^\s\'">\)]+', response)
    for url in urls:
        if call_type in ("roadmap_structure", "topic_generation", "kb_generation"):
            flags.append({
                "type": "hallucinated_url",
                "value": url,
                "severity": "high",
                "note": "LLM generated a URL — these are almost always fake",
            })

    # Future year references
    future_years = re.findall(r'20(?:2[8-9]|[3-9]\d)', response)
    for year in set(future_years):
        flags.append({
            "type": "hallucinated_future_date",
            "value": year,
            "severity": "medium",
            "note": f"References future year {year}",
        })

    # Factual errors about well-known technologies
    wrong_patterns = [
        (r"python\s+is\s+a\s+compiled", "Python incorrectly described as compiled"),
        (r"javascript\s+is\s+(?:a\s+)?strongly\s+typed", "JavaScript incorrectly described as strongly typed"),
        (r"html\s+is\s+a\s+programming\s+language", "HTML incorrectly described as a programming language"),
    ]
    for pattern, note in wrong_patterns:
        m = re.search(pattern, response_lower)
        if m:
            flags.append({
                "type": "factual_error",
                "value": m.group(),
                "severity": "high",
                "note": note,
            })

    # Truncated JSON
    if call_type in ("roadmap_structure", "topic_generation", "kb_generation"):
        open_braces = response.count('{') - response.count('}')
        open_brackets = response.count('[') - response.count(']')
        if open_braces > 0 or open_brackets > 0:
            flags.append({
                "type": "truncated_json",
                "value": f"Unclosed: {open_braces} braces, {open_brackets} brackets",
                "severity": "medium",
                "note": "LLM output was truncated — JSON repair was needed",
            })

    return flags


# ---------- Internal LLM call helpers ----------

async def _call_ollama(messages: list, temperature: float, max_tokens: int) -> tuple[str, str, str]:
    """Returns (raw_response, model_used, provider)."""
    from openai import AsyncOpenAI
    s = get_settings()
    client = AsyncOpenAI(base_url=f"{s.ollama_base_url}/v1", api_key="ollama")
    resp = await client.chat.completions.create(
        model=s.ollama_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip(), s.ollama_model, "ollama"


async def _call_groq(messages: list, temperature: float, max_tokens: int) -> tuple[str, str, str]:
    """Returns (raw_response, model_used, provider)."""
    from openai import AsyncOpenAI
    s = get_settings()
    if not s.groq_api_key:
        raise RuntimeError("Ollama is unreachable and GROQ_API_KEY is not configured")
    client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=s.groq_api_key)
    resp = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip(), "llama-3.3-70b-versatile", "groq"


# ---------- Main tracked call ----------

async def tracked_llm_call(
    messages: list,
    call_type: str,
    roadmap_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    db=None,
) -> dict:
    """
    Wrapper around async_chat_complete that logs everything.
    Returns: {"content": str, "log_id": str, "model": str, "provider": str, "latency_ms": int, "tokens_total": int}
    """
    start_time = time.time()
    log_id = str(uuid.uuid4())
    model_used = None
    provider_used = None
    raw_response = ""
    error_msg = None
    parsed_ok = False

    # Estimate input tokens (~4 chars per token)
    input_text = " ".join(m.get("content", "") for m in messages)
    est_input_tokens = max(1, len(input_text) // 4)

    try:
        try:
            raw_response, model_used, provider_used = await _call_ollama(messages, temperature, max_tokens)
        except Exception as ollama_err:
            logger.warning("[LLM] Ollama unreachable (%s) — falling back to Groq", ollama_err)
            raw_response, model_used, provider_used = await _call_groq(messages, temperature, max_tokens)

        parsed_ok = True

    except Exception as e:
        error_msg = str(e)
        model_used = model_used or "unknown"
        provider_used = provider_used or "unknown"

    latency_ms = int((time.time() - start_time) * 1000)
    est_output_tokens = max(0, len(raw_response) // 4)
    est_total_tokens = est_input_tokens + est_output_tokens

    hallucination_flags = detect_hallucinations(raw_response, call_type)

    # Console log — always
    flag_count = len(hallucination_flags)
    logger.info(
        "[LLM] %s | %s:%s | %dms | tokens: %d+%d=%d | parsed: %s | hallucinations: %d",
        call_type, provider_used, model_used, latency_ms,
        est_input_tokens, est_output_tokens, est_total_tokens,
        parsed_ok, flag_count,
    )
    if flag_count:
        logger.warning("[LLM] Hallucination flags: %s", hallucination_flags)

    # DB log — if session provided
    if db is not None:
        try:
            from app.models.llm_call_log import LLMCallLog
            import uuid as _uuid
            log_entry = LLMCallLog(
                id=_uuid.UUID(log_id),
                call_type=call_type,
                model_used=model_used,
                provider=provider_used,
                prompt_messages=messages,
                raw_response=raw_response,
                parsed_successfully=parsed_ok,
                parse_attempts=1,
                tokens_input=est_input_tokens,
                tokens_output=est_output_tokens,
                tokens_total=est_total_tokens,
                latency_ms=latency_ms,
                error_message=error_msg,
                hallucination_flags=hallucination_flags if hallucination_flags else None,
                roadmap_id=_uuid.UUID(roadmap_id) if roadmap_id else None,
                topic_id=topic_id,
            )
            db.add(log_entry)
            # Caller's transaction will commit — we don't commit here
        except Exception as log_err:
            logger.warning("[LLM] Failed to write LLM log to DB: %s", log_err)

    if error_msg:
        raise RuntimeError(f"LLM call failed ({call_type}): {error_msg}")

    return {
        "content": raw_response,
        "log_id": log_id,
        "model": model_used,
        "provider": provider_used,
        "latency_ms": latency_ms,
        "tokens_total": est_total_tokens,
    }


async def tracked_llm_call_with_json_retry(
    messages: list,
    call_type: str,
    roadmap_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    max_retries: int = 2,
    db=None,
) -> dict:
    """
    tracked_llm_call + JSON parsing with retry.
    Returns the parsed dict (not the tracking envelope).
    """
    msgs = [dict(m) for m in messages]
    last_raw = ""
    parse_attempts = 0

    for attempt in range(max_retries + 1):
        result = await tracked_llm_call(
            msgs,
            call_type=call_type,
            roadmap_id=roadmap_id,
            topic_id=topic_id,
            temperature=temperature,
            max_tokens=max_tokens,
            db=db,
        )
        last_raw = result["content"]
        parse_attempts += 1
        try:
            parsed = extract_and_parse_json(last_raw)
            logger.info("[LLM] JSON parsed successfully (attempt %d) for %s", attempt + 1, call_type)
            return parsed
        except (ValueError, Exception) as e:
            if attempt < max_retries:
                logger.warning("[LLM] JSON parse failed (attempt %d) for %s: %s", attempt + 1, call_type, e)
                msgs[-1]["content"] += (
                    "\n\nCRITICAL: Your previous response was not valid JSON. "
                    "Return ONLY a valid JSON object. No markdown, no explanation, no text outside the JSON."
                )
            else:
                raise ValueError(
                    f"LLM failed to produce valid JSON after {max_retries + 1} attempts "
                    f"for call_type={call_type}: {e}"
                )
