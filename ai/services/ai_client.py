from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from django.conf import settings
from openai import APIError, OpenAI

logger = logging.getLogger(__name__)


def _build_client() -> OpenAI:
    """
    Construct the OpenAI client with an explicit httpx client to avoid
    environment-specific proxy kwargs issues.
    """

    http_client = httpx.Client(timeout=settings.AI_REQUEST_TIMEOUT)
    return OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        max_retries=2,
        http_client=http_client,
    )


_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = _build_client()
    return _client


def call_chat_completion(
    *,
    system_prompt: str,
    user_prompt: str,
    session_id: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """
    Execute a chat completion request and return the raw content.
    """

    client = get_client()
    headers: dict[str, Any] = {"X-Correlation-ID": str(session_id)}
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    kwargs: dict[str, Any] = {
        "model": settings.OPENAI_MODEL,
        "messages": messages,
        "extra_headers": headers,
        "response_format": {"type": "json_object"},
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = client.chat.completions.create(**kwargs)
            message = response.choices[0].message
            return (message.content or "").strip()
        except APIError as exc:  # pragma: no cover - network failures are rare in tests
            last_error = exc
            logger.warning(
                "OpenAI API error attempt=%s session_id=%s error=%s",
                attempt + 1,
                session_id,
                exc,
            )
            if attempt == 1:
                raise
            time.sleep(1 + attempt)
    if last_error:
        raise last_error
    raise RuntimeError("Failed to execute completion and no error captured.")
