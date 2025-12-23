from __future__ import annotations

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.services.analysis import enqueue_analysis_for_session
from review.models import MeetingRequest, ReviewAnswer, ReviewQuestion, ReviewSession
from review.serializers import (
    ContactInfoSerializer,
    CreateReviewSessionSerializer,
    MeetingRequestCreateSerializer,
    MeetingRequestSerializer,
    ReviewAnswerSerializer,
    ReviewQuestionSerializer,
    ReviewSessionSerializer,
    SubmitAnswerSerializer,
)


def _get_next_question(session: ReviewSession):
    answered_ids = ReviewAnswer.objects.filter(session=session).values_list(
        "question_id", flat=True
    )
    return (
        ReviewQuestion.objects.filter(is_active=True)
        .exclude(id__in=answered_ids)
        .order_by("order")
        .first()
    )


class StartSessionView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request):
        payload_serializer = CreateReviewSessionSerializer(data=request.data)
        payload_serializer.is_valid(raise_exception=True)
        session = ReviewSession.objects.create(**payload_serializer.validated_data)
        next_question = _get_next_question(session)
        payload = {
            "session": ReviewSessionSerializer(session).data,
            "next_question": ReviewQuestionSerializer(next_question).data
            if next_question
            else None,
        }
        return Response(payload, status=status.HTTP_201_CREATED)


class NextQuestionView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request, session_id):
        try:
            session = ReviewSession.objects.get(id=session_id)
        except ReviewSession.DoesNotExist:
            return Response({"detail": "Session not found."}, status=404)

        next_question = _get_next_question(session)
        if not next_question:
            return Response(
                {
                    "session": ReviewSessionSerializer(session).data,
                    "completed": True,
                    "next_question": None,
                }
            )

        return Response(
            {
                "session": ReviewSessionSerializer(session).data,
                "completed": False,
                "next_question": ReviewQuestionSerializer(next_question).data,
            }
        )


class SessionContactView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request):
        serializer = ContactInfoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session_id = serializer.validated_data["review_session_id"]
        try:
            session = ReviewSession.objects.get(id=session_id)
        except ReviewSession.DoesNotExist:
            return Response({"detail": "Session not found."}, status=404)

        session.email = serializer.validated_data["email"]
        session.phone_number = serializer.validated_data["phone_number"]
        session.save(update_fields=["email", "phone_number", "updated_at"])

        return Response(
            {
                "review_session_id": str(session.id),
                "email": session.email,
                "phone_number": session.phone_number,
            }
        )


class SessionContactDetailView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request, review_session_id):
        try:
            session = ReviewSession.objects.get(id=review_session_id)
        except ReviewSession.DoesNotExist:
            return Response({"detail": "Session not found."}, status=404)

        email = session.email or None
        phone_number = session.phone_number or None
        has_contact = bool(email or phone_number)

        return Response(
            {
                "review_session_id": str(session.id),
                "has_contact": has_contact,
                "email": email,
                "phone_number": phone_number,
            }
        )


class SubmitAnswerView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request, session_id):
        try:
            session = ReviewSession.objects.get(id=session_id)
        except ReviewSession.DoesNotExist:
            return Response({"detail": "Session not found."}, status=404)

        if session.completed_at:
            return Response(
                {"detail": "Session already completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SubmitAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question_id = serializer.validated_data["question_id"]
        answer_text = serializer.validated_data.get("answer_text", "")
        audio_file = serializer.validated_data.get("audio_file")

        try:
            question = ReviewQuestion.objects.get(id=question_id, is_active=True)
        except ReviewQuestion.DoesNotExist:
            return Response({"detail": "Question not found."}, status=404)

        expected_question = _get_next_question(session)
        if expected_question and question.id != expected_question.id:
            return Response(
                {
                    "detail": "Answers must be submitted in order.",
                    "expected_question_id": expected_question.id,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not expected_question and not session.completed_at:
            return Response(
                {"detail": "All questions already answered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        answer, created = ReviewAnswer.objects.get_or_create(
            session=session,
            question=question,
            defaults={"answer_text": answer_text, "audio_file": audio_file},
        )
        if not created:
            answer.answer_text = answer_text
            if audio_file:
                answer.audio_file = audio_file
            update_fields = ["answer_text"]
            if audio_file:
                update_fields.append("audio_file")
            answer.save(update_fields=update_fields)

        next_question = _get_next_question(session)
        if not next_question:
            if not session.completed_at:
                session.completed_at = timezone.now()
                session.save(update_fields=["completed_at", "updated_at"])
                enqueue_analysis_for_session(session)

        return Response(
            {
                "session": ReviewSessionSerializer(session).data,
                "answer": ReviewAnswerSerializer(
                    answer, context={"request": request}
                ).data,
                "next_question": ReviewQuestionSerializer(next_question).data
                if next_question
                else None,
                "completed": next_question is None,
            },
            status=status.HTTP_201_CREATED,
        )


class MeetingRequestCreateView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request):
        serializer = MeetingRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session_id = serializer.validated_data["review_session_id"]
        try:
            session = ReviewSession.objects.get(id=session_id)
        except ReviewSession.DoesNotExist:
            return Response({"detail": "Session not found."}, status=404)

        if not session.email or not session.phone_number:
            return Response(
                {
                    "detail": "You should first add your phone and email to the review session."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        meeting_request = MeetingRequest.objects.create(review_session=session)
        return Response(
            MeetingRequestSerializer(meeting_request).data,
            status=status.HTTP_201_CREATED,
        )


class MeetingRequestListView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request, review_session_id):
        try:
            session = ReviewSession.objects.get(id=review_session_id)
        except ReviewSession.DoesNotExist:
            return Response({"detail": "Session not found."}, status=404)

        meeting_requests = session.meeting_requests.order_by("-created_at")
        serializer = MeetingRequestSerializer(meeting_requests, many=True)
        return Response(serializer.data)
