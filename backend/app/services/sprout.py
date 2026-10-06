"""Sprout's explanation of a route: fixed templates, never an AI model.

Every sentence is assembled from the route's own facts and the same matched
flags the card shows, so the explanation cannot contradict the numbers beside
it. Two rules from the acceptance criteria shape it:

- It names at least one preference the user chose and at least one fact about
  the route (US5.6).
- A preference the route missed is said out loud, not dressed up as a match.

With no preferences chosen it describes the walk without calling it
personalised.
"""

from app.schemas.planning import PlannedRoute, PreferenceMatch, Preferences

# The design doc's pollen wording (section 2). A raw count is never shown.
NO_POLLEN = "No high-pollen trees nearby"
LOWEST_POLLEN = "Lowest-pollen route"
LOWEST_AVAILABLE = "Lowest-pollen route available"

NAMES = {
    "canopy": {"open": "open sky", "mixed": "bit of canopy", "dense": "deep canopy"},
    "shade": {"sunny": "sunshine", "mixed": "bit of shade", "cool": "shade"},
    "noise": {"quiet": "quiet streets", "lively": "livelier streets"},
    "allergy": {"avoid": "lower pollen"},
}


def explain_route(route: PlannedRoute, preferences: Preferences) -> str:
    facts = (
        f"about {round(route.durationMinutes)} min, with "
        f"{round(route.denseZoneShare * 100)}% of the walk through tree-dense zones"
    )
    place = route.destination.label

    if not route.matches:
        return f"Here's a walk to {place} — {facts}."

    met = [_name(match, preferences) for match in route.matches if match.matched]
    missed = [_name(match, preferences) for match in route.matches if not match.matched]

    if met:
        first = f"I picked {place} for your {_join(met)} — {facts}."
    else:
        first = f"{place} is the closest match I found — {facts}."

    caveats = []
    if missed:
        caveats.append(f"it doesn't quite fit your {_join(missed)}")
    if any(match.detail == LOWEST_AVAILABLE for match in route.matches):
        caveats.append("a few pollen trees are still on the way")
    if not caveats:
        return first
    second = " and ".join(caveats)
    return f"{first} {second[0].upper()}{second[1:]}."


def _name(match: PreferenceMatch, preferences: Preferences) -> str:
    if match.key == "time":
        return "walking time"
    return NAMES[match.key][getattr(preferences, match.key)]


def _join(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} and {items[-1]}"
