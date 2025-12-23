from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.models import AnalysisSession
from ai.serializers import AnalysisSessionSerializer, CreateAnalysisSerializer
from ai.services.analysis import collect_answers_for_review_session, create_or_reset_analysis_session
from review.models import ReviewSession


class AnalysisCreateView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        serializer = CreateAnalysisSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        review_session = None
        if data.get("review_session_id"):
            review_session = get_object_or_404(ReviewSession, id=data["review_session_id"])
            try:
                raw_answers = collect_answers_for_review_session(review_session)
            except ValueError as exc:
                return Response(
                    {"detail": str(exc)},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            raw_answers = {
                "session_id": str(data["session_id"]),
                "answers": sorted(data["answers"], key=lambda x: x["order"]),
            }

        analysis, created = create_or_reset_analysis_session(
            raw_answers=raw_answers, review_session=review_session
        )
        response_serializer = AnalysisSessionSerializer(analysis)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class AnalysisDetailView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request: Request, session_id) -> Response:
        analysis = get_object_or_404(AnalysisSession, id=session_id)
        serializer = AnalysisSessionSerializer(analysis)
        return Response(serializer.data)
