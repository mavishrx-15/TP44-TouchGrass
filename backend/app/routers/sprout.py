from math import isfinite
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text

from app.cbd import contains_in_geometry, geometry, require_inside
from app.config import settings
from app.db import SessionDep
from app.route_metrics import dense_zone_share, high_pollen_tree_count
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
CANOPY_DENSITY = {"open": "Low", "mixed": "Medium", "dense": "High"}


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
    boundary = geometry()
    pollen_names = settings.high_pollen_list
    pollen_sql = (
        "SUM(CASE WHEN lower(trim(t.common_name)) IN :pollen THEN 1 ELSE 0 END) AS pollen_count"
        if pollen_names
        else "NULL AS pollen_count"
    )
    statement = text(
        f"""
        SELECT z.cluster_id, z.center_lat, z.center_lon, z.tree_count, z.precinct,
               {pollen_sql}
        FROM zones z LEFT JOIN trees t ON t.cluster_id = z.cluster_id
        GROUP BY z.cluster_id, z.center_lat, z.center_lon, z.tree_count, z.precinct
        """
    )
    if pollen_names:
        statement = statement.bindparams(bindparam("pollen", expanding=True))
        rows = session.execute(statement, {"pollen": pollen_names}).all()
    else:
        rows = session.execute(statement).all()

    low, high = BANDS[req.preferences.walkingTime]
    result = []
    for row in rows:
        if row.cluster_id in req.excludeZoneIds:
            continue
        if not contains_in_geometry(boundary, row.center_lat, row.center_lon):
            continue

        distance = _distance_m(req.origin.lat, req.origin.lng, row.center_lat, row.center_lon)
        estimate = distance * 1.3 / 80
        density = _density(row.tree_count)
        pollen_count = row.pollen_count if pollen_names else None
        in_band = low <= estimate <= high
        canopy_match = (
            req.preferences.canopy is None or density == CANOPY_DENSITY[req.preferences.canopy]
        )
        result.append(
            {
                "id": row.cluster_id,
                "center": {"lat": row.center_lat, "lng": row.center_lon},
                "treeCount": row.tree_count,
                "density": density,
                "bounds": _bounds(row.cluster_id).model_dump(),
                "precinct": row.precinct,
                "pollenCount": pollen_count,
                "estimate": estimate,
                "inBand": in_band,
                "bandGap": max(low - estimate, 0, estimate - high),
                "distance": distance,
                "canopyMatch": canopy_match,
            }
        )

    return sorted(
        result,
        key=lambda area: (
            not area["inBand"],
            area["bandGap"],
            (
                area["pollenCount"]
                if req.preferences.allergy == "avoid" and area["pollenCount"] is not None
                else 0
            ),
            not area["canopyMatch"],
            -area["treeCount"],
            area["distance"],
        ),
    )


def _unmet(
    preferences: Preferences,
    density: str,
    pollen_count: int | None,
    in_band: bool,
) -> list[str]:
    missed = []
    if not in_band and preferences.walkingTime is not None:
        missed.append("walkingTime")
    if preferences.canopy is not None and density != CANOPY_DENSITY[preferences.canopy]:
        missed.append("canopy")
    if preferences.allergy == "avoid" and pollen_count is not None and pollen_count > 0:
        missed.append("allergy")
    return missed


def _unverified_preferences(
    preferences: Preferences, pollen_configured: bool, route_measured: bool
) -> list[dict[str, str]]:
    unverified = []
    if preferences.noise:
        unverified.append(
            {
                "preference": "noise",
                "reason": (
                    "No street-noise dataset is configured, so this preference " "was not verified."
                ),
            }
        )
    if preferences.shade:
        unverified.append(
            {
                "preference": "shade",
                "reason": (
                    "No shade or sun-exposure dataset is configured; tree density "
                    "is not a direct shade measurement."
                ),
            }
        )
    if preferences.allergy == "avoid":
        if not pollen_configured:
            reason = (
                "HIGH_POLLEN_SPECIES is not configured, so pollen exposure "
                "could not be verified."
            )
        elif not route_measured:
            reason = (
                "The walking route has not been calculated, so route pollen exposure is unverified."
            )
        else:
            reason = ""
        if reason:
            unverified.append({"preference": "allergy", "reason": reason})
    return unverified


def _preference_chips(preferences: Preferences) -> list[str]:
    return [
        PREFERENCE_LABELS[key][value]
        for key in PREFERENCE_LABELS
        if (value := getattr(preferences, key))
    ]


def _public_zone(area: dict, label: str | None = None) -> dict:
    zone_label = label or f"{area['precinct']} · Tree zone {area['id']}"
    return {
        "id": area["id"],
        "label": zone_label,
        "center": area["center"],
        "bounds": area["bounds"],
        "treeCount": area["treeCount"],
        "density": area["density"],
    }


def _area_card(area: dict, preferences: Preferences) -> dict:
    unmet = _unmet(
        preferences,
        area["density"],
        pollen_count=None,
        in_band=area["inBand"],
    )
    label = f"{area['precinct']} · Tree zone {area['id']}"
    return {
        "id": area["id"],
        "label": label,
        "destination": _public_zone(area, label),
        "walkingTimeMinutes": round(area["estimate"]),
        "distanceMeters": round(area["distance"]),
        "preferenceChips": _preference_chips(preferences),
        "unmetPreferences": unmet,
        "unverifiedPreferences": _unverified_preferences(
            preferences, bool(settings.high_pollen_list), route_measured=False
        ),
    }


@router.get("/cbd/zones")
def cbd_zones(session: SessionDep) -> dict:
    boundary = geometry()
    rows = session.execute(
        text("SELECT cluster_id, center_lat, center_lon, tree_count, precinct FROM zones")
    ).all()
    zones = []
    for row in rows:
        if contains_in_geometry(boundary, row.center_lat, row.center_lon):
            label = f"{row.precinct} · Tree zone {row.cluster_id}"
            zones.append(
                {
                    "id": row.cluster_id,
                    "label": label,
                    "precinct": row.precinct,
                    "center": {"lat": row.center_lat, "lng": row.center_lon},
                    "bounds": _bounds(row.cluster_id).model_dump(),
                    "treeCount": row.tree_count,
                    "density": _density(row.tree_count),
                }
            )
    return {"boundary": boundary, "zones": zones}


@router.post("/sprout/areas")
def areas(request: AreasRequest, session: SessionDep) -> list[dict]:
    require_inside(request.origin.lat, request.origin.lng)
    return [
        _area_card(area, request.preferences)
        for area in _candidates(session, request)[: request.limit]
    ]


@router.post("/sprout/route")
def sprout_route(request: RouteRequest, session: SessionDep) -> dict:
    require_inside(request.origin.lat, request.origin.lng)
    if not settings.google_maps_api_key:
        raise HTTPException(status_code=503, detail={"code": "google_maps_unconfigured"})
    candidates = _candidates(session, request)
    if not candidates:
        raise HTTPException(status_code=404, detail={"code": "no_matching_cbd_zones"})

    routed = []
    for area in candidates[:3]:
        require_inside(area["center"]["lat"], area["center"]["lng"])
        route = _google_route(request.origin, area["center"])
        try:
            path = _decode_polyline(route["polyline"]["encodedPolyline"])
            minutes = _duration_seconds(route["duration"]) / 60
            distance_m = float(route["distanceMeters"])
        except (KeyError, TypeError, ValueError, IndexError) as error:
            raise HTTPException(
                status_code=502, detail={"code": "google_routes_invalid_response"}
            ) from error
        if not path or not isfinite(distance_m) or distance_m < 0:
            raise HTTPException(status_code=502, detail={"code": "google_routes_invalid_response"})
        pollen_count = high_pollen_tree_count(path, settings.high_pollen_list, session)
        routed.append(
            {
                "area": area,
                "route": route,
                "path": path,
                "minutes": minutes,
                "distanceMeters": distance_m,
                "pollenCount": pollen_count,
                "denseZoneShare": dense_zone_share(path, session),
            }
        )

    low, high = BANDS[request.preferences.walkingTime]
    selected = min(
        routed,
        key=lambda item: (
            not low <= item["minutes"] <= high,
            max(low - item["minutes"], 0, item["minutes"] - high),
            (
                item["pollenCount"]
                if request.preferences.allergy == "avoid" and item["pollenCount"] is not None
                else 0
            ),
            not item["area"]["canopyMatch"],
            -item["area"]["treeCount"],
            item["distanceMeters"],
        ),
    )
    area = selected["area"]
    minutes = selected["minutes"]
    pollen_count = selected["pollenCount"]
    unmet = _unmet(
        request.preferences,
        area["density"],
        pollen_count=pollen_count,
        in_band=low <= minutes <= high,
    )
    unverified = _unverified_preferences(
        request.preferences,
        bool(settings.high_pollen_list),
        route_measured=True,
    )
    preference_chips = _preference_chips(request.preferences)
    destination_label = f"{area['precinct']} · Tree zone {area['id']}"
    explanation = _explanation(
        area,
        minutes,
        selected["distanceMeters"],
        selected["denseZoneShare"],
        request.preferences,
        pollen_count,
    )
    return {
        "destination": _public_zone(area, destination_label),
        "walkingTimeMinutes": round(minutes),
        "distanceMeters": round(selected["distanceMeters"]),
        "denseZoneShare": selected["denseZoneShare"],
        "preferenceChips": preference_chips,
        "unmetPreferences": unmet,
        "unverifiedPreferences": unverified,
        "explanation": explanation,
        "encodedPolyline": selected["route"]["polyline"]["encodedPolyline"],
        "steps": _steps(selected["route"]),
    }


def _explanation(
    area: dict,
    minutes: float,
    distance_m: float,
    dense_share: float,
    preferences: Preferences,
    pollen_count: int | None,
) -> str:
    label = f"{area['precinct']} · Tree zone {area['id']}"
    facts = [
        f"{label} is about {minutes:.0f} minutes and {distance_m / 1000:.1f} km away",
        f"its zone contains {area['treeCount']} trees ({area['density']} density)",
        f"{dense_share:.0%} of the route distance is inside zones with 10 or more trees",
    ]
    if preferences.walkingTime is not None:
        low, high = BANDS[preferences.walkingTime]
        if low <= minutes <= high:
            facts.append(
                f"that matches your {preferences.walkingTime}-minute target ({low}–{high} min)"
            )
        else:
            facts.append(
                f"that is outside your {preferences.walkingTime}-minute target ({low}–{high} min)"
            )
    if preferences.canopy:
        preferred_density = CANOPY_DENSITY[preferences.canopy]
        match_word = "matches" if area["density"] == preferred_density else "does not match"
        facts.append(
            f"your {PREFERENCE_LABELS['canopy'][preferences.canopy]} preference "
            f"{match_word} the {area['density']} density tier"
        )
    if preferences.allergy == "avoid":
        if pollen_count is None:
            facts.append("high-pollen exposure could not be verified")
        elif pollen_count == 0:
            facts.append("no configured high-pollen trees were detected within 100 m of the route")
        else:
            facts.append(
                f"the route passes within 100 m of {pollen_count} configured "
                "high-pollen tree(s), so this preference is not met"
            )
    if preferences.noise:
        facts.append("noise could not be verified because no street-noise data is available")
    if preferences.shade:
        facts.append("shade could not be verified because no sun-exposure data is available")
    return "; ".join(facts) + "."


def _google_route(origin: Coordinates, destination: dict[str, float]) -> dict:
    try:
        response = httpx.post(
            "https://routes.googleapis.com/directions/v2:computeRoutes",
            json={
                "origin": {
                    "location": {
                        "latLng": {
                            "latitude": origin.lat,
                            "longitude": origin.lng,
                        }
                    }
                },
                "destination": {
                    "location": {
                        "latLng": {
                            "latitude": destination["lat"],
                            "longitude": destination["lng"],
                        }
                    }
                },
                "travelMode": "WALK",
                "languageCode": "en-AU",
                "units": "METRIC",
            },
            headers={
                "X-Goog-Api-Key": settings.google_maps_api_key,
                "X-Goog-FieldMask": (
                    "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,"
                    "routes.legs.steps.navigationInstruction.instructions,"
                    "routes.legs.steps.startLocation,routes.legs.steps.distanceMeters"
                ),
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502, detail={"code": "google_routes_request_failed"}
        ) from error
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502, detail={"code": "google_routes_unavailable"}
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=502, detail={"code": "google_routes_invalid_response"}
        ) from error
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail={"code": "google_routes_invalid_response"})
    routes = data.get("routes")
    if not routes:
        raise HTTPException(status_code=404, detail={"code": "route_not_found"})
    if not isinstance(routes[0], dict):
        raise HTTPException(status_code=502, detail={"code": "google_routes_invalid_response"})
    return routes[0]


def _steps(route: dict) -> list[dict]:
    return [
        {
            "instruction": step.get("navigationInstruction", {}).get("instructions", ""),
            "startLocation": step.get("startLocation", {}).get("latLng", {}),
            "distanceMeters": step.get("distanceMeters", 0),
        }
        for leg in route.get("legs", [])
        for step in leg.get("steps", [])
    ]
