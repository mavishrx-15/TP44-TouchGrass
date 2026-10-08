import json

from fastapi import HTTPException

from app.config import settings


def polygons() -> list[list[list[float]]]:
    if not settings.cbd_boundary_geojson:
        raise HTTPException(status_code=503, detail={"code": "cbd_boundary_unconfigured"})
    try:
        geo = json.loads(settings.cbd_boundary_geojson)
        rings = [geo["coordinates"][0]] if geo["type"] == "Polygon" else [p[0] for p in geo["coordinates"]]
        if geo["type"] not in ("Polygon", "MultiPolygon") or any(len(r) < 4 for r in rings):
            raise ValueError
        return [[[float(p[0]), float(p[1])] for p in ring] for ring in rings]
    except (ValueError, KeyError, TypeError, IndexError):
        raise HTTPException(status_code=503, detail={"code": "cbd_boundary_invalid"}) from None


def contains(lat: float, lng: float) -> bool:
    for ring in polygons():
        inside = False
        for i, (x1, y1) in enumerate(ring):
            x2, y2 = ring[(i + 1) % len(ring)]
            if (y1 > lat) != (y2 > lat) and lng < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
                inside = not inside
        if inside:
            return True
    return False


def require_inside(lat: float, lng: float) -> None:
    if not contains(lat, lng):
        raise HTTPException(status_code=422, detail={"code": "outside_cbd", "message": "Location must be inside the Hoddle Grid."})
