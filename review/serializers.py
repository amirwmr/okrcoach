from __future__ import annotations

from rest_framework import serializers

from review.models import MeetingRequest, ReviewAnswer, ReviewQuestion, ReviewSession
from review.utils.phone import normalize_ir_phone


class ReviewQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewQuestion
        fields = ("id", "prompt", "order")


class ReviewSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewSession
        fields = (
            "id",
            "phone_number",
            "email",
            "created_at",
            "updated_at",
            "completed_at",
        )
        read_only_fields = ("created_at", "updated_at", "completed_at")


class CreateReviewSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewSession
        fields = ("phone_number", "email")


class ContactInfoSerializer(serializers.Serializer):
    review_session_id = serializers.UUIDField()
    email = serializers.EmailField()
    phone_number = serializers.CharField()

    def validate_phone_number(self, value: str) -> str:
        return normalize_ir_phone(value)


class ReviewAnswerSerializer(serializers.ModelSerializer):
    audio_url = serializers.SerializerMethodField()
    question = ReviewQuestionSerializer(read_only=True)

    class Meta:
        model = ReviewAnswer
        fields = ("id", "question", "answer_text", "audio_url", "created_at")

    def get_audio_url(self, obj: ReviewAnswer):
        if obj.audio_file:
            request = self.context.get("request")
            url = obj.audio_file.url
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return ""


class SubmitAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    answer_text = serializers.CharField(required=False, allow_blank=True, default="")
    audio_file = serializers.FileField(required=False, allow_empty_file=False)

    def validate(self, attrs):
        answer_text = attrs.get("answer_text", "")
        audio_file = attrs.get("audio_file")
        if not answer_text and not audio_file:
            raise serializers.ValidationError("Provide either answer_text or audio_file.")
        return attrs


class MeetingRequestSerializer(serializers.ModelSerializer):
    review_session_id = serializers.UUIDField(source="review_session.id", read_only=True)
    email = serializers.EmailField(source="review_session.email", read_only=True)
    phone_number = serializers.CharField(
        source="review_session.phone_number", read_only=True
    )

    class Meta:
        model = MeetingRequest
        fields = (
            "id",
            "review_session_id",
            "status",
            "email",
            "phone_number",
            "created_at",
        )
        read_only_fields = (
            "status",
            "review_session_id",
            "created_at",
            "email",
            "phone_number",
        )


class MeetingRequestCreateSerializer(serializers.Serializer):
    review_session_id = serializers.UUIDField()
