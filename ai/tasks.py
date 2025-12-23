from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import transaction

from ai.services import prompts
from ai.models import AnalysisSession, AnalysisSessionStatus
from ai.services.ai_client import call_chat_completion
from ai.services.analysis import _channel_key
from ai.services.schema import validate_dashboard

logger = logging.getLogger(__name__)


def _send_group_message(channel_key: str, message: dict[str, Any]) -> None:
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(f"analysis_{channel_key}", message)


def _parse_and_validate(raw_text: str, session_uuid: UUID) -> dict[str, Any]:
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON decode error: {exc}") from exc
    return validate_dashboard(data, session_uuid)


def _update_status(instance: AnalysisSession, channel_key: str, status: str, error: str | None = None) -> None:
    instance.status = status
    instance.error = error
    instance.save(update_fields=["status", "error"])
    _send_group_message(
        channel_key,
        {
            "type": "status",
            "status": status,
            "error": error,
            "session_id": str(instance.id),
            "review_session_id": str(instance.review_session_id) if instance.review_session_id else None,
        },
    )


@shared_task(bind=True)
def run_analysis(self, session_id: str) -> None:
    try:
        session = AnalysisSession.objects.get(id=session_id)
    except AnalysisSession.DoesNotExist:
        logger.warning("AnalysisSession %s no longer exists", session_id)
        return
    channel_key = _channel_key(session.review_session_id, session.id)

    logger.info("Starting analysis task for session=%s", session_id)
    _update_status(session, channel_key, AnalysisSessionStatus.RUNNING, None)

    payload = session.raw_answers
    target_session_id = (
        session.review_session_id
        or payload.get("session_id")
        or session.id
    )
    try:
        target_uuid = UUID(str(target_session_id))
    except Exception:
        target_uuid = session.id
    system_prompt = prompts.build_system_prompt()
    user_prompt = prompts.build_user_prompt(payload)
    last_raw_text: str | None = None

    try:
        raw_text = call_chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            session_id=session_id,
            temperature=settings.AI_TEMPERATURE,
            max_tokens=settings.AI_MAX_TOKENS,
        )
        last_raw_text = raw_text
        validated = _parse_and_validate(raw_text, target_uuid)
    except Exception as exc:
        logger.info("Attempting to repair invalid AI output for session=%s error=%s", session_id, exc)
        repair_prompt = prompts.build_repair_prompt(last_raw_text or "")
        try:
            raw_text = call_chat_completion(
                system_prompt=system_prompt,
                user_prompt=repair_prompt,
                session_id=session_id,
                temperature=settings.AI_TEMPERATURE,
                max_tokens=settings.AI_MAX_TOKENS,
            )
            last_raw_text = raw_text
            validated = _parse_and_validate(raw_text, target_uuid)
        except Exception as repair_exc:
            error_message = str(repair_exc)
            session.ai_raw_response = last_raw_text or ""
            session.dashboard_json = None
            _update_status(session, channel_key, AnalysisSessionStatus.FAILED, error_message)
            _send_group_message(
                channel_key,
                {"type": "error", "message": error_message},
            )
            logger.exception(
                "Failed to repair AI output for session=%s error=%s",
                session_id,
                repair_exc,
            )
            session.save(update_fields=["ai_raw_response", "dashboard_json"])
            return
    try:
        with transaction.atomic():
            session.ai_raw_response = last_raw_text or ""
            session.dashboard_json = validated
            _update_status(session, channel_key, AnalysisSessionStatus.SUCCEEDED, None)
            session.save(update_fields=["ai_raw_response", "dashboard_json"])
    except Exception as exc:  # pragma: no cover - safeguard
        logger.exception("Error saving analysis session=%s error=%s", session_id, exc)
        _update_status(session, channel_key, AnalysisSessionStatus.FAILED, str(exc))
        _send_group_message(
            channel_key, {"type": "error", "message": "Failed to persist result."}
        )
        return

    _send_group_message(
        channel_key,
        {"type": "result", "data": session.dashboard_json},
    )
    logger.info("Completed analysis for session=%s", session_id)
