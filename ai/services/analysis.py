from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from ai.models import AnalysisSession, AnalysisSessionStatus
from review.models import ReviewAnswer, ReviewQuestion, ReviewSession

logger = logging.getLogger(__name__)


def collect_answers_for_review_session(session: ReviewSession) -> dict[str, Any]:
    """
    Pull the latest five active questions and their answers for a session.
    """

    questions = list(
        ReviewQuestion.objects.filter(is_active=True).order_by("order")[:5]
    )
    if len(questions) < 5:
        raise ValueError("Not enough active questions to build analysis payload.")

    answers_payload: list[dict[str, Any]] = []
    for question in questions:
        try:
            answer = ReviewAnswer.objects.filter(
                session=session, question=question
            ).latest("created_at")
        except ReviewAnswer.DoesNotExist as exc:
            raise ValueError(
                f"Missing answer for question {question.id}."
            ) from exc
        answer_text = (answer.answer_text or "").strip()
        if not answer_text:
            raise ValueError(f"Answer text missing for question {question.id}.")
        answers_payload.append(
            {
                "order": question.order,
                "answer": answer_text,
                "prompt": question.prompt,
                "question_id": question.id,
            }
        )

    return {"session_id": str(session.id), "answers": answers_payload}


def _reset_session_state(
    instance: AnalysisSession, raw_answers: dict[str, Any], review_session: ReviewSession | None
) -> AnalysisSession:
    instance.raw_answers = raw_answers
    instance.status = AnalysisSessionStatus.PENDING
    instance.dashboard_json = None
    instance.ai_raw_response = ""
    instance.error = None
    if review_session:
        instance.review_session = review_session
    instance.save(
        update_fields=[
            "raw_answers",
            "status",
            "dashboard_json",
            "ai_raw_response",
            "error",
            "review_session",
        ]
    )
    _send_status(instance)
    return instance


def create_or_reset_analysis_session(
    *,
    raw_answers: dict[str, Any],
    review_session: ReviewSession | None = None,
    session_id: UUID | None = None,
) -> tuple[AnalysisSession, bool]:
    """
    Create a new AnalysisSession or reset an existing one with fresh answers.
    """

    existing = None
    if review_session:
        try:
            existing = review_session.analysis  # type: ignore[attr-defined]
        except AnalysisSession.DoesNotExist:
            existing = None
        if existing:
            session_id = session_id or existing.id

    with transaction.atomic():
        if session_id:
            instance, created = AnalysisSession.objects.select_for_update().update_or_create(
                id=session_id,
                defaults={
                    "review_session": review_session,
                    "raw_answers": raw_answers,
                    "status": AnalysisSessionStatus.PENDING,
                },
            )
        elif review_session:
            instance, created = AnalysisSession.objects.select_for_update().update_or_create(
                review_session=review_session,
                defaults={
                    "raw_answers": raw_answers,
                    "status": AnalysisSessionStatus.PENDING,
                },
            )
        else:
            instance = AnalysisSession.objects.create(
                raw_answers=raw_answers,
                review_session=review_session,
            )
            created = True
        if not created:
            instance = _reset_session_state(
                instance=instance,
                raw_answers=raw_answers,
                review_session=review_session,
            )
        else:
            _send_status(instance)

    from ai.tasks import run_analysis

    run_analysis.delay(str(instance.id))
    return instance, created


def enqueue_analysis_for_session(session: ReviewSession) -> AnalysisSession:
    """
    Helper used by the review app to create an analysis job.
    """

    raw_answers = collect_answers_for_review_session(session)
    analysis, _ = create_or_reset_analysis_session(
        raw_answers=raw_answers, review_session=session
    )
    logger.info("Enqueued analysis for review_session=%s analysis_id=%s", session.id, analysis.id)
    return analysis


def _channel_key(review_session_id: UUID | None, session_id: UUID) -> str:
    return str(review_session_id or session_id)


def _send_status(instance: AnalysisSession) -> None:
    layer = get_channel_layer()
    if not layer:
        return
    channel_key = _channel_key(instance.review_session_id, instance.id)
    async_to_sync(layer.group_send)(
        f"analysis_{channel_key}",
        {
            "type": "status",
            "status": instance.status,
            "error": instance.error,
            "session_id": str(instance.id),
            "review_session_id": str(instance.review_session_id) if instance.review_session_id else None,
        },
    )


__all__ = [
    "collect_answers_for_review_session",
    "enqueue_analysis_for_session",
    "create_or_reset_analysis_session",
    "_channel_key",
    "_send_status",
]
