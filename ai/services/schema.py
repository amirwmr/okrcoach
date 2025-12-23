from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScoreDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=0, le=100)
    delta: int = Field(ge=-100, le=100)


class Cards(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_score: ScoreDelta
    customer_satisfaction: ScoreDelta
    team_efficiency: ScoreDelta
    sales_performance: ScoreDelta


class Radar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sales: float = Field(ge=0.0, le=1.0)
    team: float = Field(ge=0.0, le=1.0)
    marketing: float = Field(ge=0.0, le=1.0)
    systems: float = Field(ge=0.0, le=1.0)
    profitability: float = Field(ge=0.0, le=1.0)
    time: float = Field(ge=0.0, le=1.0)


class MainChallenge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    body: str
    statistics: dict[str, Any] = Field(default_factory=dict)
    solution: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "body")
    @classmethod
    def _ensure_text(cls, value: str) -> str:
        if not value or not str(value).strip():
            raise ValueError("Field cannot be empty.")
        return value

    @field_validator("statistics", "solution")
    @classmethod
    def _ensure_dict(cls, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("Must be an object.")
        return value


class BusinessOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    radar: Radar
    main_challenge: MainChallenge


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str

    @field_validator("title")
    @classmethod
    def _ensure_title(cls, value: str) -> str:
        if not value or not str(value).strip():
            raise ValueError("Title is required.")
        return value


class Dashboard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: UUID | str
    cards: Cards
    business_overview: BusinessOverview
    recommendations: list[Recommendation]

    @field_validator("recommendations")
    @classmethod
    def _validate_recommendations(
        cls, value: list[Recommendation]
    ) -> list[Recommendation]:
        if len(value) != 3:
            raise ValueError("Exactly 3 recommendations required.")
        return value


def validate_dashboard(data: dict[str, Any], session_id: UUID) -> dict[str, Any]:
    """
    Validate and normalize dashboard output, forcing the provided session_id.
    """

    payload = {**data, "session_id": str(session_id)}
    dashboard = Dashboard.model_validate(payload)
    return dashboard.model_dump()
