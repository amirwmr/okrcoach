from django.urls import path

from core import consumers
from ai import consumers as ai_consumers

websocket_urlpatterns = [
    path("ws/health/", consumers.HealthCheckConsumer.as_asgi()),
    path(
        "ws/analysis/<uuid:session_id>/",
        ai_consumers.AnalysisConsumer.as_asgi(),
    ),
]
