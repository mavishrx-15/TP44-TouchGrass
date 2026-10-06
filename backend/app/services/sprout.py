"""Owner: Sprout developer. Fixed templates only; never call an AI model."""

from app.errors import feature_pending
from app.schemas.planning import PlannedRoute, Preferences


def explain_route(route: PlannedRoute, preferences: Preferences) -> str:
    # TODO: use route facts and matches; admit missed preferences; no invented facts.
    feature_pending("sprout.explanation")
