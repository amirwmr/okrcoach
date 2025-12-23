from __future__ import annotations

import json
import logging
from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.exceptions import ObjectDoesNotExist

from ai.models import AnalysisSession
from ai.serializers import CreateAnalysisSerializer
from ai.services.analysis import collect_answers_for_review_session, create_or_reset_analysis_session
from review.models import ReviewSession

logger = logging.getLogger(__name__)


class AnalysisConsumer(AsyncJsonWebsocketConsumer):
    """
    Websocket channel that streams analysis progress/results.
    """

    group_name: str
    session_key: str

    async def connect(self) -> None:
        self.session_key = str(self.scope["url_route"]["kwargs"]["session_id"])
        self.session_id = self.session_key  # for backwards compatibility with existing logic
        self.group_name = f"analysis_{self.session_key}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self._send_current_status()

    async def disconnect(self, code: int) -> None:
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        await super().disconnect(code)

    async def receive_json(self, content: dict[str, Any], **kwargs: Any) -> None:
        if not content:
            await self.send_json({"type": "error", "message": "Empty payload"})
            return

        serializer = CreateAnalysisSerializer(data=content)
        if not serializer.is_valid():
            await self.send_json({"type": "error", "message": serializer.errors})
            return

        data = serializer.validated_data
        try:
            analysis = await self._start_analysis(data)
        except Exception as exc:  # pragma: no cover - defensive
            await self.send_json({"type": "error", "message": str(exc)})
            return

        await self.send_json({"type": "accepted", "session_id": str(analysis.id)})

    async def progress(self, event: dict[str, Any]) -> None:
        await self.send_json({"type": "progress", "step": event.get("step")})

    async def result(self, event: dict[str, Any]) -> None:
        await self.send_json({"type": "result", "data": event.get("data")})

    async def error(self, event: dict[str, Any]) -> None:
        await self.send_json({"type": "error", "message": event.get("message")})

    async def status(self, event: dict[str, Any]) -> None:
        await self.send_json(
            {
                "type": "status",
                "status": event.get("status"),
                "session_id": event.get("session_id"),
                "review_session_id": event.get("review_session_id"),
                "error": event.get("error"),
                "result": event.get("result"),
            }
        )

    async def decode_json(self, text_data: str | bytes) -> dict[str, Any] | None:
        """
        Be tolerant of empty/whitespace messages to avoid 500 errors on blank frames.
        """
        if not text_data:
            return None
        if isinstance(text_data, (bytes, bytearray)):
            text_data = text_data.decode()
        if not str(text_data).strip():
            return None
        return json.loads(text_data)

    async def _send_current_status(self) -> None:
        snapshot = await self._get_status_snapshot()
        await self.send_json(snapshot)

    @database_sync_to_async
    def _get_status_snapshot(self) -> dict[str, Any]:
        try:
            session = AnalysisSession.objects.get(review_session_id=self.session_key)
        except AnalysisSession.DoesNotExist:
            try:
                session = AnalysisSession.objects.get(id=self.session_key)
            except AnalysisSession.DoesNotExist:
                review_exists = ReviewSession.objects.filter(id=self.session_key).exists()
                return {
                    "type": "status",
                    "status": "not_completed" if review_exists else "not_found",
                    "session_id": None,
                    "review_session_id": self.session_key,
                }

        return {
            "type": "status",
            "status": session.status,
            "session_id": str(session.id),
            "review_session_id": str(session.review_session_id) if session.review_session_id else None,
            "error": session.error,
            "result": session.dashboard_json,
        }

    @database_sync_to_async
    def _start_analysis(self, data: dict[str, Any]):
        review_session = None
        if "review_session_id" in data and data["review_session_id"]:
            try:
                review_session = ReviewSession.objects.get(id=data["review_session_id"])
            except ObjectDoesNotExist as exc:
                raise ValueError("Review session not found.") from exc
            raw_answers = collect_answers_for_review_session(review_session)
        else:
            if review_session is None:
                try:
                    review_session = ReviewSession.objects.get(id=self.session_key)
                except ReviewSession.DoesNotExist:
                    review_session = None
            raw_answers = {
                "session_id": str(data.get("session_id") or self.session_key),
                "answers": sorted(data["answers"], key=lambda x: x["order"]),
            }

        analysis, _ = create_or_reset_analysis_session(
            raw_answers=raw_answers,
            review_session=review_session,
            session_id=self.session_key,
        )
        return analysis
