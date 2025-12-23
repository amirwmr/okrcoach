from django.urls import path

from review import views

urlpatterns = [
    path("start/", views.StartSessionView.as_view(), name="review-start"),
    path("<uuid:session_id>/next/", views.NextQuestionView.as_view(), name="review-next"),
    path("<uuid:session_id>/answer/", views.SubmitAnswerView.as_view(), name="review-answer"),
    path("session/contact/", views.SessionContactView.as_view(), name="review-session-contact"),
    path(
        "session/<uuid:review_session_id>/contact/",
        views.SessionContactDetailView.as_view(),
        name="review-session-contact-detail",
    ),
    path(
        "session/meeting/request/",
        views.MeetingRequestCreateView.as_view(),
        name="review-meeting-request",
    ),
    path(
        "session/<uuid:review_session_id>/meeting/requests/",
        views.MeetingRequestListView.as_view(),
        name="review-meeting-request-list",
    ),
]
