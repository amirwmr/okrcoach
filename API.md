# OKR Coach API

HTTP routes are prefixed with `/api/` and WebSocket endpoints with `/ws/`. All endpoints are unauthenticated by default. Requests and responses use JSON unless sending audio uploads (multipart/form-data).

Only the review flows are exposed over HTTP; AI analysis is triggered via WebSocket.

## REST: Review

### Start a review session  
`POST /api/review/start/`

Create a session and fetch the first active question.

Request body:
- `phone_number` (string, optional)
- `email` (string, optional)

Success `201 Created`:
```json
{
  "session": {
    "id": "75c6d5c2-95f0-4f98-9a2e-9c6c10f2fca8",
    "phone_number": "",
    "email": "",
    "created_at": "2024-05-01T10:00:00Z",
    "updated_at": "2024-05-01T10:00:00Z",
    "completed_at": null
  },
  "next_question": {
    "id": 1,
    "prompt": "Describe your main business goal.",
    "order": 1
  }
}
```

### Get the next question  
`GET /api/review/{session_id}/next/`

Returns the next unanswered active question or marks the session complete.

Success `200 OK`:
```json
{
  "session": { "...": "..." },
  "completed": false,
  "next_question": {
    "id": 2,
    "prompt": "What is blocking progress?",
    "order": 2
  }
}
```
Errors: `404` if the session is unknown.

### Submit an answer  
`POST /api/review/{session_id}/answer/`

Submit answers in question order. Rejects out-of-order submissions or completed sessions.

Request body (multipart/form-data when including `audio_file`):
- `question_id` (integer, required)
- `answer_text` (string, optional)
- `audio_file` (file, optional, required if `answer_text` blank)

Success `201 Created`:
```json
{
  "session": { "...": "..." },
  "answer": {
    "id": 10,
    "question": {
      "id": 2,
      "prompt": "What is blocking progress?",
      "order": 2
    },
    "answer_text": "Hiring bottlenecks.",
    "audio_url": "https://example.com/media/review/audio/answer.wav",
    "created_at": "2024-05-01T10:05:00Z"
  },
  "next_question": {
    "id": 3,
    "prompt": "What is working well?",
    "order": 3
  },
  "completed": false
}
```
Errors: `400` for out-of-order answers, missing payload, or completed sessions; `404` if session/question not found.

### Add contact info  
`POST /api/review/session/contact/`

Attach contact details to a session. Phone numbers are normalized to `+98XXXXXXXXXX` and must be valid Iranian numbers.

Request body:
- `review_session_id` (uuid, required)
- `email` (string, required)
- `phone_number` (string, required)

Success `200 OK`:
```json
{
  "review_session_id": "75c6d5c2-95f0-4f98-9a2e-9c6c10f2fca8",
  "email": "user@example.com",
  "phone_number": "+989121234567"
}
```
Errors: `404` if the session is unknown; `400` for invalid phone/email.

### Get contact status  
`GET /api/review/session/{review_session_id}/contact/`

Returns whether contact info exists and the current values (or `null` if absent).

Success `200 OK`:
```json
{
  "review_session_id": "75c6d5c2-95f0-4f98-9a2e-9c6c10f2fca8",
  "has_contact": true,
  "email": "user@example.com",
  "phone_number": "+989121234567"
}
```
Errors: `404` if the session is unknown.

### Request a meeting  
`POST /api/review/session/meeting/request/`

Creates a meeting request after contact info is present.

Request body:
- `review_session_id` (uuid, required)

Success `201 Created`:
```json
{
  "id": 3,
  "review_session_id": "75c6d5c2-95f0-4f98-9a2e-9c6c10f2fca8",
  "status": "PENDING",
  "email": "user@example.com",
  "phone_number": "+989121234567",
  "created_at": "2024-05-01T10:10:00Z"
}
```
Errors: `400` if contact info is missing; `404` if the session is unknown.

### List meeting requests  
`GET /api/review/session/{review_session_id}/meeting/requests/`

Lists meeting requests for a session (newest first).

Success `200 OK`:
```json
[
  {
    "id": 3,
    "review_session_id": "75c6d5c2-95f0-4f98-9a2e-9c6c10f2fca8",
    "status": "PENDING",
    "email": "user@example.com",
    "phone_number": "+989121234567",
    "created_at": "2024-05-01T10:10:00Z"
  }
]
```
Errors: `404` if the session is unknown.

## WebSockets

All WebSocket frames are JSON objects.

### Health check  
`ws/health/`

- On connect: server sends `{"status":"ok","message":"connected"}`.  
- Send `{"action":"db_ping"}` to verify async DB connectivity; server replies with `{"type":"db_ping","ok":true}` (or `error` set).  
- Any other payload is echoed back as `{"type":"echo","data":<payload>}`.

### Analysis stream  
`ws/analysis/{session_id}/`

Streams AI analysis status/results and allows triggering an analysis. `session_id` can be the review session UUID or an analysis session UUID.

Connection handshake:
- Server immediately sends a status snapshot:  
  - If an analysis exists: `{"type":"status","status":"pending|running|succeeded|failed","session_id":"<analysis_uuid>","review_session_id":"<uuid|null>","error":null,"result":<dashboard|null>}`.  
  - If no analysis but the review session exists: `status: "not_completed"`.  
  - If neither exists: `status: "not_found"`.

Client → server (start/reset analysis):
- Either provide a review session to auto-pull its answers:  
  ```json
  { "review_session_id": "75c6d5c2-95f0-4f98-9a2e-9c6c10f2fca8" }
  ```
- Or send a full five-answer payload (orders 1–5 exactly once; non-empty `prompt`/`answer`):  
  ```json
  {
    "session_id": "75c6d5c2-95f0-4f98-9a2e-9c6c10f2fca8",
    "answers": [
      { "order": 1, "question_id": 1, "prompt": "Q1", "answer": "A1" },
      { "order": 2, "question_id": 2, "prompt": "Q2", "answer": "A2" },
      { "order": 3, "question_id": 3, "prompt": "Q3", "answer": "A3" },
      { "order": 4, "question_id": 4, "prompt": "Q4", "answer": "A4" },
      { "order": 5, "question_id": 5, "prompt": "Q5", "answer": "A5" }
    ]
  }
  ```
- If both `review_session_id` and `session_id` are supplied, they must match. Validation errors are sent as `{"type":"error","message":<details>}`.
- On acceptance the server responds `{"type":"accepted","session_id":"<analysis_uuid>"}` and queues the Celery job.

Server → client events:
- `{"type":"status","status":"pending|running|succeeded|failed","session_id":"<uuid>","review_session_id":"<uuid|null>","error":<string|null>,"result":<dashboard|null>}` — lifecycle updates; `result` only included in the initial snapshot.  
- `{"type":"result","data":<dashboard_json>}` — emitted on success.  
- `{"type":"error","message":<string>}` — fatal errors (includes validation failures).  
- `{"type":"progress","step":<string|null>}` — reserved hook for intermediate progress (may be unused).
