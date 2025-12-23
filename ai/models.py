from __future__ import annotations

import uuid

from django.db import models


class AnalysisSessionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class AnalysisSession(models.Model):
    """
    Stores the AI dashboard output for a review session.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review_session = models.OneToOneField(
        "review.ReviewSession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analysis",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=16,
        choices=AnalysisSessionStatus.choices,
        default=AnalysisSessionStatus.PENDING,
    )
    raw_answers = models.JSONField()
    ai_raw_response = models.TextField(blank=True, default="")
    dashboard_json = models.JSONField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["-created_at"]),
        ]
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"AnalysisSession({self.id}, status={self.status})"
