from django.contrib import admin

from review.models import MeetingRequest, ReviewAnswer, ReviewQuestion, ReviewSession


@admin.register(ReviewSession)
class ReviewSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "phone_number", "email", "created_at", "completed_at")
    search_fields = ("id", "phone_number", "email")
    list_filter = ("completed_at", "created_at")
    readonly_fields = ("id", "created_at", "updated_at", "completed_at")


@admin.register(ReviewQuestion)
class ReviewQuestionAdmin(admin.ModelAdmin):
    list_display = ("order", "prompt", "is_active")
    list_editable = ("is_active",)
    ordering = ("order",)
    search_fields = ("prompt",)


@admin.register(ReviewAnswer)
class ReviewAnswerAdmin(admin.ModelAdmin):
    list_display = ("session", "question", "created_at")
    search_fields = ("session__id", "question__prompt", "answer_text")
    list_filter = ("question", "created_at")
    autocomplete_fields = ("session", "question")


@admin.register(MeetingRequest)
class MeetingRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "review_session",
        "session_phone_number",
        "session_email",
        "status",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "id",
        "review_session__id",
        "review_session__phone_number",
        "review_session__email",
    )
    list_filter = ("status", "created_at", "updated_at")
    autocomplete_fields = ("review_session",)
    readonly_fields = ("id", "created_at", "updated_at")
    list_select_related = ("review_session",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    fields = (
        "id",
        "review_session",
        "status",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Phone number")
    def session_phone_number(self, obj: MeetingRequest) -> str:
        return obj.review_session.phone_number

    @admin.display(description="Email")
    def session_email(self, obj: MeetingRequest) -> str:
        return obj.review_session.email
