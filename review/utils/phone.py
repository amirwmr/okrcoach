import re

from rest_framework import serializers


_PHONE_ERROR = {"phone_number": "Invalid Iranian phone number. Expected +98XXXXXXXXXX."}


def normalize_ir_phone(raw: str) -> str:
    """
    Normalize Iranian phone numbers into E.164 +98XXXXXXXXXX format.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise serializers.ValidationError(_PHONE_ERROR)

    digits = re.sub(r"\D", "", raw)

    if digits.startswith("00"):
        digits = digits[2:]

    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]

    if len(digits) == 10:
        digits = f"98{digits}"

    if len(digits) == 12 and digits.startswith("98"):
        normalized = f"+{digits}"
    else:
        normalized = ""

    if not re.fullmatch(r"\+98\d{10}", normalized):
        raise serializers.ValidationError(_PHONE_ERROR)

    return normalized
