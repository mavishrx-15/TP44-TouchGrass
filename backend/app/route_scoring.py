"""Preference scoring; park share is a proxy, not measured shade or sound.

Allergy matching avoids the user's chosen genera/families. It does not infer
medical risk from taxonomy. Each tree is counted at most once in that match.
"""

from pydantic import BaseModel, Field, model_validator


class Preferences(BaseModel):
    canopy: float = Field(default=3, ge=0, le=5)
    shade: float = Field(default=3, ge=0, le=5)
    noise: float = Field(default=2, ge=0, le=5)
    allergy: float = Field(default=0, ge=0, le=5)
    walkingMinutes: int = Field(default=30, ge=5, le=180)
    avoidGenera: list[str] = Field(default_factory=list, max_length=30)
    avoidFamilies: list[str] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def allergy_targets_required(self):
        if self.allergy and not any(s.strip() for s in self.avoidGenera + self.avoidFamilies):
            raise ValueError("Choose at least one genus or family for allergy avoidance")
        return self


def park_score(rows) -> float:
    """Share of corridor trees located in a park, for both shade and noise."""
    return sum(r.located_in == "Park" for r in rows) / len(rows) if rows else 0.0


def allergy_score(rows, preferences: Preferences) -> float:
    genera = {s.strip().casefold() for s in preferences.avoidGenera}
    families = {s.strip().casefold() for s in preferences.avoidFamilies}
    if not rows:
        return 0.0
    avoided = sum(
        r.display_category.casefold() in genera or r.family.casefold() in families for r in rows
    )
    return 1 - avoided / len(rows)


def weighted_score(scores: dict[str, float], preferences: Preferences) -> float:
    total = sum(getattr(preferences, name) for name in scores)
    return (
        sum(value * getattr(preferences, name) for name, value in scores.items()) / total
        if total
        else 0.0
    )
