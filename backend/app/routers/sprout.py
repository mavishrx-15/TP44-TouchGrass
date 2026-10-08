from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text

from app.cbd import polygons, require_inside
from app.config import settings
from app.db import SessionDep
from app.routers.map_data import _bounds, _density
from app.routers.routes import Coordinates, _decode_polyline, _distance_m, _duration_seconds

router = APIRouter()
BANDS = {5: (3, 7), 10: (8, 12), 15: (13, 17), 20: (18, 30), None: (5, 15)}
PREFERENCE_LABELS = {
    "canopy": {"open": "Open canopy", "mixed": "Mixed canopy", "dense": "Deep canopy"},
    "shade": {"sunny": "Sunny and open", "mixed": "Some shade", "cool": "Cool and shaded"},
    "noise": {"quiet": "Quieter", "lively": "Lively"},
    "allergy": {"avoid": "Avoid high pollen"},
}


class Preferences(BaseModel):
    canopy: Literal["open", "mixed", "dense"] | None = None
    shade: Literal["sunny", "mixed", "cool"] | None = None
    noise: Literal["quiet", "lively"] | None = None
    allergy: Literal["avoid"] | None = None
    walkingTime: Literal[5, 10, 15, 20] | None = None


class AreasRequest(BaseModel):
    origin: Coordinates
    preferences: Preferences = Preferences()
    excludeZoneIds: list[str] = Field(default_factory=list)
    limit: int = Field(default=3, ge=1, le=20)


class RouteRequest(AreasRequest):
    pass


def _candidates(session: SessionDep, req: AreasRequest) -> list[dict]:
    rings = polygons()
    statement = text("""
        SELECT z.cluster_id, z.center_lat, z.center_lon, z.tree_count, z.precinct,
               SUM(CASE WHEN lower(t.located_in) = 'park' THEN 1 ELSE 0 END) AS park_count,
               SUM(CASE WHEN lower(t.common_name) IN :pollen THEN 1 ELSE 0 END) AS pollen_count
        FROM zones z LEFT JOIN trees t ON t.cluster_id = z.cluster_id
        GROUP BY z.cluster_id, z.center_lat, z.center_lon, z.tree_count, z.precinct
    """).bindparams(bindparam("pollen", expanding=True))
    rows = session.execute(statement, {"pollen": settings.high_pollen_list or ["__none__"]}).all()
    low, high = BANDS[req.preferences.walkingTime]
    result = []
    for row in rows:
        if row.cluster_id in req.excludeZoneIds:
            continue
        if not any(_contains_ring(ring, row.center_lat, row.center_lon) for ring in rings):
            continue
        distance = _distance_m(req.origin.lat, req.origin.lng, row.center_lat, row.center_lon)
        estimate = distance * 1.3 / 80
        density = _density(row.tree_count)
        if req.preferences.canopy == "dense" and density == "Low":
            continue
        if req.preferences.canopy == "mixed" and density == "Low":
            continue
        park_share = (row.park_count or 0) / max(row.tree_count, 1)
        shade_fit = {"sunny": -park_share, "mixed": -abs(park_share - .5), "cool": park_share}.get(req.preferences.shade, 0)
        result.append({"id": row.cluster_id, "center": {"lat": row.center_lat, "lng": row.center_lon},
                       "treeCount": row.tree_count, "density": density, "bounds": _bounds(row.cluster_id).model_dump(),
                       "precinct": row.precinct,
                       "parkShare": park_share, "pollenCount": row.pollen_count or 0, "estimate": estimate,
                       "inBand": low <= estimate <= high, "bandGap": max(low - estimate, 0, estimate - high),
                       "distance": distance, "shadeFit": shade_fit,
                       "unmetPreferences": _unmet(req.preferences, density, park_share, row.pollen_count or 0,
                                                  low <= estimate <= high)})
    return sorted(result, key=lambda z: (not z["inBand"], z["bandGap"],
                                         z["pollenCount"] if req.preferences.allergy == "avoid" else 0,
                                         -z["shadeFit"], -z["treeCount"], z["distance"]))


def _unmet(preferences: Preferences, density: str, park_share: float, pollen: int, in_band: bool) -> list[str]:
    missed = []
    if not in_band:
        missed.append("walkingTime")
    if preferences.noise:
        missed.append("noise")
    if preferences.allergy == "avoid" and (pollen or not settings.high_pollen_list):
        missed.append("allergy")
    if preferences.shade == "sunny" and park_share > .8:
        missed.append("shade")
    if preferences.shade == "cool" and park_share < .2:
        missed.append("shade")
    if preferences.shade == "mixed" and abs(park_share - .5) > .3:
        missed.append("shade")
    return missed


def _contains_ring(ring: list[list[float]], lat: float, lng: float) -> bool:
    inside = False
    for i, (x1, y1) in enumerate(ring):
        x2, y2 = ring[(i + 1) % len(ring)]
        if (y1 > lat) != (y2 > lat) and lng < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


@router.get("/cbd/zones")
def cbd_zones(session: SessionDep) -> dict:
    rings = polygons()
    rows = session.execute(text("SELECT cluster_id, center_lat, center_lon, tree_count FROM zones")).all()
    zones = []
    for row in rows:
        if any(_contains_ring(ring, row.center_lat, row.center_lon) for ring in rings):
            zones.append({"id": row.cluster_id, "center": {"lat": row.center_lat, "lng": row.center_lon},
                          "bounds": _bounds(row.cluster_id).model_dump(), "treeCount": row.tree_count,
                          "density": _density(row.tree_count)})
    boundary = {"type": "Polygon", "coordinates": rings} if len(rings) == 1 else {
        "type": "MultiPolygon", "coordinates": [[ring] for ring in rings]}
    return {"boundary": boundary, "zones": zones}


@router.post("/sprout/areas")
def areas(request: AreasRequest, session: SessionDep) -> list[dict]:
    require_inside(request.origin.lat, request.origin.lng)
    return [_area_card(row, request.preferences) for row in _candidates(session, request)[:request.limit]]


def _area_card(row: dict, preferences: Preferences) -> dict:
    minutes = round(row["estimate"])
    return {"id": row["id"], "label": f"CBD · Tree zone {row['id']}", "destination": _public_zone(row),
            "walkingTimeMinutes": minutes, "distanceMeters": round(row["distance"]),
            "preferenceChips": _chips(preferences), "unmetPreferences": row["unmetPreferences"]}


def _public_zone(area: dict, label: str | None = None) -> dict:
    return {"id": area["id"], "label": label or f"{area['precinct']} · Tree zone {area['id']}",
            "center": area["center"], "bounds": area["bounds"], "treeCount": area["treeCount"],
            "density": area["density"]}


def _chips(preferences: Preferences) -> list[str]:
    return [PREFERENCE_LABELS[key][value] for key in PREFERENCE_LABELS
            if (value := getattr(preferences, key))]


@router.post("/sprout/route")
def sprout_route(request: RouteRequest, session: SessionDep) -> dict:
    require_inside(request.origin.lat, request.origin.lng)
    if not settings.google_maps_api_key:
        raise HTTPException(status_code=503, detail="Google Routes API key is not configured.")
    candidates = _candidates(session, request)
    if not candidates:
        raise HTTPException(status_code=404, detail="No CBD zones match the selected canopy preference.")
    routed = []
    for area in candidates[:3]:
        route = _google_route(request.origin, area["center"])
        minutes = _duration_seconds(route["duration"]) / 60
        routed.append((area, route, minutes))
    low, high = BANDS[request.preferences.walkingTime]
    fitting = [item for item in routed if low <= item[2] <= high]
    area, route, minutes = min(fitting or routed, key=lambda x: (
        x[0]["pollenCount"] if request.preferences.allergy == "avoid" else 0,
        -x[0]["treeCount"], x[2])) if fitting else min(
        routed, key=lambda x: (max(low - x[2], 0, x[2] - high),
                               x[0]["pollenCount"] if request.preferences.allergy == "avoid" else 0,
                               -x[0]["treeCount"], x[2]))
    unmet = _unmet(request.preferences, area["density"], area["parkShare"], area["pollenCount"], low <= minutes <= high)
    chips = _chips(request.preferences)
    decoded = _decode_polyline(route["polyline"]["encodedPolyline"])
    dense = session.execute(text("SELECT center_lat, center_lon FROM zones WHERE tree_count >= 10")).all()
    dense_share = round(sum(1 for lat, lng in decoded if any(
        abs(lat - z.center_lat) <= .0005 and abs(lng - z.center_lon) <= .0005 for z in dense
    )) / max(len(decoded), 1), 2)
    missed = ", ".join(unmet)
    explanation = (f"This route offers {area['treeCount']} trees for {chips[0] if chips else 'your walk'}. "
                   + (f"The {minutes:.0f}-minute walk misses your selected {missed} preference." if missed
                      else f"It takes about {minutes:.0f} minutes through tree-dense areas."))
    return {"destination": _public_zone(area),
            "walkingTimeMinutes": round(minutes), "distanceMeters": route["distanceMeters"],
            "denseZoneShare": dense_share, "preferenceChips": chips, "unmetPreferences": unmet,
            "explanation": explanation, "encodedPolyline": route["polyline"]["encodedPolyline"],
            "steps": _steps(route)}


def _google_route(origin: Coordinates, dest: dict) -> dict:
    response = httpx.post("https://routes.googleapis.com/directions/v2:computeRoutes",
        json={"origin": {"location": {"latLng": {"latitude": origin.lat, "longitude": origin.lng}}},
              "destination": {"location": {"latLng": {"latitude": dest['lat'], "longitude": dest['lng']}}},
              "travelMode": "WALK", "languageCode": "en-AU", "units": "METRIC"},
        headers={"X-Goog-Api-Key": settings.google_maps_api_key,
                 "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,routes.legs.steps.navigationInstruction.instructions,routes.legs.steps.startLocation,routes.legs.steps.distanceMeters"}, timeout=15)
    try:
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Google Routes could not calculate this walk.") from exc
    routes = response.json().get("routes", [])
    if not routes:
        raise HTTPException(status_code=404, detail="No walking route was found.")
    return routes[0]


def _steps(route: dict) -> list[dict]:
    return [{"instruction": s.get("navigationInstruction", {}).get("instructions", ""),
             "startLocation": s.get("startLocation", {}).get("latLng", {}), "distanceMeters": s.get("distanceMeters", 0)}
            for leg in route.get("legs", []) for s in leg.get("steps", [])]
