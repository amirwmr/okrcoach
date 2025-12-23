from django.contrib import admin

from ai.models import AnalysisSession


@admin.register(AnalysisSession)
class AnalysisSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "review_session", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("id", "review_session__id")
