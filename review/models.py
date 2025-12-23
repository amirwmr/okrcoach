from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models


class ReviewSession(models.Model):
    """
    Anonymous review session keyed by a UUID token.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=32, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"ReviewSession({self.id})"


class ReviewQuestion(models.Model):
    """
    Question prompt shown to the user in order.
    """

    prompt = models.TextField()
    order = models.PositiveIntegerField(unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("order",)

    def __str__(self) -> str:
        return f"Q{self.order}: {self.prompt[:32]}..."


class ReviewAnswer(models.Model):
    """
    Captures the answer for a question within a session.
    """

    session = models.ForeignKey(
        ReviewSession, related_name="answers", on_delete=models.CASCADE
    )
    question = models.ForeignKey(
        ReviewQuestion, related_name="answers", on_delete=models.CASCADE
    )
    answer_text = models.TextField(blank=True, default="")
    audio_file = models.FileField(
        upload_to="review/audio/", blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("session", "question")
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"Answer(session={self.session_id}, question={self.question_id})"


class MeetingRequest(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"

    review_session = models.ForeignKey(
        ReviewSession, related_name="meeting_requests", on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=16, choices=StatusChoices.choices, default=StatusChoices.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"MeetingRequest(session={self.review_session_id}, status={self.status})"

    def clean(self):
        super().clean()
        session = self.review_session
        if session and (not session.phone_number or not session.email):
            raise ValidationError(
                "You should first add your phone and email to the review session."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
