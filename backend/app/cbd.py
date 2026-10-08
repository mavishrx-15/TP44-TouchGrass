"""Shared CBD coverage for maps, Places, routes and future tree pins.

CBD_BOUNDARY overrides the default outline with a JSON GeoJSON coordinate
ring ([longitude, latitude]). Return this same ring to clients; never round a
position to invent a zone id.
"""

from math import isfinite

from fastapi import HTTPException

from app.config import settings


def boundary() -> list[tuple[float, float]]:
    ring = list(settings.cbd_boundary)
    if len(set(ring)) < 3 or any(
        not isfinite(lng) or not isfinite(lat) or not (-180 <= lng <= 180 and -90 <= lat <= 90)
        for lng, lat in ring
    ):
        raise HTTPException(status_code=503, detail="CBD boundary is not configured correctly.")
    if ring[-1] != ring[0]:
        ring.append(ring[0])
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:], strict=False))
    if abs(area) < 1e-12:
        raise HTTPException(status_code=503, detail="CBD boundary has no area.")
    return ring


def coverage_bounds() -> dict[str, float]:
    ring = boundary()
    return {
        "north": max(lat for _, lat in ring),
        "south": min(lat for _, lat in ring),
        "east": max(lng for lng, _ in ring),
        "west": min(lng for lng, _ in ring),
    }


def contains(lat: float, lng: float) -> bool:
    """Point-in-polygon, including points on its edge. Reject nonfinite input."""
    if not isfinite(lat) or not isfinite(lng) or not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return False
    ring = boundary()
    inside = False
    for (ax, ay), (bx, by) in zip(ring, ring[1:], strict=False):
        cross = (lng - ax) * (by - ay) - (lat - ay) * (bx - ax)
        if (
            abs(cross) <= 1e-12
            and min(ax, bx) - 1e-10 <= lng <= max(ax, bx) + 1e-10
            and min(ay, by) - 1e-10 <= lat <= max(ay, by) + 1e-10
        ):
            return True
        if (ay > lat) != (by > lat) and lng < ax + (lat - ay) * (bx - ax) / (by - ay):
            inside = not inside
    return inside


def require_inside(lat: float, lng: float) -> None:
    if not contains(lat, lng):
        raise HTTPException(status_code=422, detail="outside_cbd")


def center() -> dict[str, float]:
    """One point to stand for the CBD: the middle of the outline's bounding box.

    The live temperature is read for a single location. Deriving it from the
    outline rather than keeping a second hard-coded point means the CBD has one
    definition, not two that can drift apart.
    """
    bounds = coverage_bounds()
    return {
        "lat": (bounds["south"] + bounds["north"]) / 2,
        "lng": (bounds["west"] + bounds["east"]) / 2,
    }
