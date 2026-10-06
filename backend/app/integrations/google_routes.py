"""Google adapter owned by the route developer; keep external calls out of routers."""

from app.schemas.common import Coordinates


def walking_alternatives(origin: Coordinates, destination: Coordinates) -> list[dict]:
    # TODO: timeout, safe upstream errors, polyline + distance + duration + steps.
    # Reuse existing route decoding/scoring logic, but do not invoke HTTP handlers.
    raise NotImplementedError("Google walking route adapter is not implemented.")
