from __future__ import annotations

import json
from typing import Any, Dict, List

SCHEMA_EXAMPLE: Dict[str, Any] = {
    "session_id": "00000000-0000-0000-0000-000000000000",
    "cards": {
        "overall_score": {"score": 50, "delta": 0},
        "customer_satisfaction": {"score": 50, "delta": 0},
        "team_efficiency": {"score": 50, "delta": 0},
        "sales_performance": {"score": 50, "delta": 0},
    },
    "business_overview": {
        "radar": {
            "sales": 0.5,
            "team": 0.5,
            "marketing": 0.5,
            "systems": 0.5,
            "profitability": 0.5,
            "time": 0.5,
        },
        "main_challenge": {
            "title": "تیتر اصلی",
            "body": "متن خلاصه چالش به فارسی",
            "statistics": {"title": "۹۲٪ کسب‌وکارها", "description": "مثال"},
            "solution": {"title": "راهکار", "description": "شرح کوتاه"},
        },
    },
    "recommendations": [
        {"title": "توصیه اول"},
        {"title": "توصیه دوم"},
        {"title": "توصیه سوم"},
    ],
}


def build_system_prompt() -> str:
    return (
        "فقط JSON معتبر و بدون هیچ متن اضافه برگردان. "
        "هیچ توضیح یا نشانه‌گذاری مارک‌داون مجاز نیست."
    )


def _render_answers(answers: List[dict[str, Any]]) -> str:
    rendered = []
    for item in sorted(answers, key=lambda x: x.get("order", 0)):
        rendered.append(
            f"سوال {item['order']} (id={item['question_id']}): {item['prompt']}\n"
            f"پاسخ: {item['answer']}"
        )
    return "\n\n".join(rendered)


def build_user_prompt(payload: dict[str, Any]) -> str:
    answers = payload.get("answers", [])
    answers_block = _render_answers(answers)
    schema_block = json.dumps(SCHEMA_EXAMPLE, ensure_ascii=False, indent=2)
    return (
        "با توجه به پرسش و پاسخ‌های زیر یک داشبورد خلاصه کسب‌وکار بساز. "
        "تمام متن‌ها باید فارسی باشند.\n"
        f"شناسه جلسه: {payload.get('session_id')}\n"
        "پرسش‌ها و پاسخ‌ها:\n"
        f"{answers_block}\n\n"
        "خروجی باید دقیقا JSON مطابق این ساختار باشد و فقط JSON برگردد. "
        "به محدودیت‌های بازه اعداد توجه کن (score بین ۰ تا ۱۰۰، delta بین -۱۰۰ تا ۱۰۰، "
        "مقادیر radar بین ۰ و ۱ و دقیقا سه توصیه):\n"
        f"{schema_block}"
    )


def build_repair_prompt(raw_output: str) -> str:
    return (
        "این خروجی JSON معتبر نیست یا با طرح هماهنگ نیست. "
        "خروجی زیر را بدون هیچ توضیحی به JSON درست مطابق طرح تبدیل کن و فقط JSON برگردان. "
        "Fix this to valid JSON matching the schema exactly. Return JSON only.\n"
        f"{raw_output}"
    )
