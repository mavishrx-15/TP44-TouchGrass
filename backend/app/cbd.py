import json
from math import isfinite

from fastapi import HTTPException

from app.config import settings


def geometry() -> dict:
    if not settings.cbd_boundary_geojson:
        raise HTTPException(status_code=503, detail={"code": "cbd_boundary_unconfigured"})
    try:
        geo = json.loads(settings.cbd_boundary_geojson)
        geo_type = geo["type"]
        coordinates = geo["coordinates"]
        polygons = [coordinates] if geo_type == "Polygon" else coordinates
        if geo_type not in ("Polygon", "MultiPolygon") or not polygons:
            raise ValueError

        normalized = []
        for polygon in polygons:
            if not polygon:
                raise ValueError
            rings = []
            for ring in polygon:
                if not isinstance(ring, list) or len(ring) < 4:
                    raise ValueError
                points = []
                for point in ring:
                    if not isinstance(point, list) or len(point) < 2:
                        raise ValueError
                    lng, lat = float(point[0]), float(point[1])
                    if (
                        not isfinite(lng)
                        or not isfinite(lat)
                        or not -180 <= lng <= 180
                        or not -90 <= lat <= 90
                    ):
                        raise ValueError
                    points.append([lng, lat])
                if points[0] != points[-1] or len({tuple(point) for point in points[:-1]}) < 3:
                    raise ValueError
                rings.append(points)
            normalized.append(rings)

        return {
            "type": geo_type,
            "coordinates": normalized[0] if geo_type == "Polygon" else normalized,
        }
    except (ValueError, KeyError, TypeError, IndexError):
        raise HTTPException(status_code=503, detail={"code": "cbd_boundary_invalid"}) from None


def polygons() -> list[list[list[float]]]:
    """Return the exterior rings for bounding-box queries and compatibility."""
    geo = geometry()
    coordinates = geo["coordinates"]
    return [coordinates[0]] if geo["type"] == "Polygon" else [item[0] for item in coordinates]


def bounds() -> dict[str, float]:
    points = [point for ring in polygons() for point in ring]
    return {
        "west": min(point[0] for point in points),
        "south": min(point[1] for point in points),
        "east": max(point[0] for point in points),
        "north": max(point[1] for point in points),
    }


def _inside_ring(ring: list[list[float]], lat: float, lng: float) -> bool:
    inside = False
    for index, (x1, y1) in enumerate(ring):
        x2, y2 = ring[(index + 1) % len(ring)]
        if (y1 > lat) != (y2 > lat) and lng < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def contains(lat: float, lng: float) -> bool:
    return contains_in_geometry(geometry(), lat, lng)


def contains_in_geometry(geo: dict, lat: float, lng: float) -> bool:
    polygons_with_holes = [geo["coordinates"]] if geo["type"] == "Polygon" else geo["coordinates"]
    for rings in polygons_with_holes:
        exterior, *holes = rings
        if _inside_ring(exterior, lat, lng) and not any(
            _inside_ring(hole, lat, lng) for hole in holes
        ):
            return True
    return False


def require_inside(lat: float, lng: float) -> None:
    if not contains_in_geometry(geometry(), lat, lng):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "outside_cbd",
                "message": "Location must be inside the Hoddle Grid.",
            },
        )
