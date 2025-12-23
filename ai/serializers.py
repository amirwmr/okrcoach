from __future__ import annotations

from typing import Any
from uuid import UUID

from rest_framework import serializers

from ai.models import AnalysisSession


class AnswerItemSerializer(serializers.Serializer):
    order = serializers.IntegerField(min_value=1, max_value=5)
    question_id = serializers.IntegerField(min_value=1)
    prompt = serializers.CharField()
    answer = serializers.CharField()

    def validate_prompt(self, value: str) -> str:
        if not value or not value.strip():
            raise serializers.ValidationError("prompt is required.")
        return value

    def validate_answer(self, value: str) -> str:
        if not value or not value.strip():
            raise serializers.ValidationError("answer is required.")
        return value


class CreateAnalysisSerializer(serializers.Serializer):
    """
    Accept either a review_session_id to pull answers internally
    or a complete 5-answer payload.
    """

    review_session_id = serializers.UUIDField(required=False)
    session_id = serializers.UUIDField(required=False)
    answers = AnswerItemSerializer(many=True, required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        review_session_id = attrs.get("review_session_id")
        answers = attrs.get("answers")
        session_id: UUID | None = attrs.get("session_id")

        if not review_session_id and not answers:
            raise serializers.ValidationError(
                "Provide either review_session_id or answers."
            )

        if answers is not None:
            if len(answers) != 5:
                raise serializers.ValidationError("Exactly 5 answers are required.")
            orders = [item["order"] for item in answers]
            if sorted(orders) != [1, 2, 3, 4, 5]:
                raise serializers.ValidationError(
                    "Answers must include orders 1 through 5 exactly once."
                )
            if session_id is None:
                raise serializers.ValidationError(
                    {"session_id": "session_id is required when sending answers."}
                )

        if review_session_id and session_id and review_session_id != session_id:
            raise serializers.ValidationError(
                "session_id must match review_session_id when both are provided."
            )

        if review_session_id and not session_id:
            attrs["session_id"] = review_session_id

        return attrs


class AnalysisSessionSerializer(serializers.ModelSerializer):
    review_session_id = serializers.SerializerMethodField()

    class Meta:
        model = AnalysisSession
        fields = (
            "id",
            "review_session_id",
            "status",
            "created_at",
            "raw_answers",
            "dashboard_json",
            "error",
            "ai_raw_response",
        )
        read_only_fields = fields

    def get_review_session_id(self, obj: AnalysisSession) -> str | None:
        return str(obj.review_session_id) if obj.review_session_id else None
