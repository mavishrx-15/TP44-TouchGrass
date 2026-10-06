"""Complete CBD map data and database-backed facts, without tree downloads."""

from types import SimpleNamespace
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.cbd import boundary, contains, coverage_bounds
from app.db import SessionDep
from app.routers.map_data import (
    Bounds,
    Coordinates,
    Density,
    Zone,
    ZoneProfile,
    _density,
    _profiles,
    _zone,
)

router = APIRouter()


class Outline(BaseModel):
    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[tuple[float, float]]]


class CbdZone(Zone):
    label: str


class CbdZones(BaseModel):
    boundary: Outline
    bounds: Bounds
    zoneCount: int
    densityCounts: dict[Density, int]
    zones: list[CbdZone]


class SpeciesFact(BaseModel):
    commonName: str
    count: int


class ZoneFacts(BaseModel):
    zoneId: str
    treeCount: int
    density: Density
    topSpecies: list[SpeciesFact]


@router.get("/cbd/zones", response_model=CbdZones)
def cbd_zones(session: SessionDep) -> CbdZones:
    """All zones whose stored centre lies in the CBD; no pagination cap.

    Bounds retain the original grid cells. canopy is ranked across this CBD
    set; distanceKm is from the outline's vertex mean, not a user's location.
    """
    bounds = coverage_bounds()
    rows = session.execute(
        text(
            """
            SELECT cluster_id, center_lat, center_lon, tree_count, precinct, street_name
            FROM zones
            WHERE center_lat BETWEEN :south AND :north
              AND center_lon BETWEEN :west AND :east
            ORDER BY tree_count DESC, cluster_id
            """
        ),
        bounds,
    ).all()
    rows = [r for r in rows if contains(r.center_lat, r.center_lon)]
    profiles = _profiles({r.cluster_id for r in rows}, session) if rows else {}
    ring = boundary()
    vertices = ring[:-1]
    origin = Coordinates(
        lat=sum(lat for _, lat in vertices) / len(vertices),
        lng=sum(lng for lng, _ in vertices) / len(vertices),
    )
    # Equivalent to PERCENT_RANK, including ties, over the coverage set.
    counts = sorted(r.tree_count for r in rows)
    ranks = {}
    for index, count in enumerate(counts):
        ranks.setdefault(count, index / (len(counts) - 1) if len(counts) > 1 else 0)
    zones = []
    density_counts: dict[Density, int] = {"High": 0, "Medium": 0, "Low": 0}
    for row in rows:
        ranked = SimpleNamespace(**row._mapping, canopy_rank=ranks[row.tree_count])
        zone = _zone(ranked, profiles.get(row.cluster_id, ZoneProfile()), origin)
        label = f"{row.precinct} · {row.street_name}" if row.street_name else row.precinct
        zones.append(CbdZone(**zone.model_dump(), label=label))
        density_counts[zone.density] += 1
    return CbdZones(
        boundary=Outline(coordinates=[ring]),
        bounds=Bounds(**bounds),
        zoneCount=len(zones),
        densityCounts=density_counts,
        zones=zones,
    )


@router.get("/zones/{zone_id}/facts", response_model=ZoneFacts)
def zone_facts(zone_id: str, session: SessionDep) -> ZoneFacts:
    """Use the exact API zone id, including any stored float noise.

    Counts are aggregated from every tree in the zone, not a capped download
    or genus category. No species are invented when names are missing.
    """
    zone = session.execute(
        text("SELECT tree_count FROM zones WHERE cluster_id = :id"), {"id": zone_id}
    ).first()
    if zone is None:
        raise HTTPException(status_code=404, detail="Unknown zone.")
    species = session.execute(
        text(
            """
            SELECT TRIM(common_name) AS common_name, COUNT(*) AS n
            FROM trees
            WHERE cluster_id = :id AND NULLIF(TRIM(common_name), '') IS NOT NULL
            GROUP BY TRIM(common_name)
            ORDER BY n DESC, common_name ASC
            LIMIT 2
            """
        ),
        {"id": zone_id},
    ).all()
    return ZoneFacts(
        zoneId=zone_id,
        treeCount=zone.tree_count,
        density=_density(zone.tree_count),
        topSpecies=[SpeciesFact(commonName=r.common_name, count=r.n) for r in species],
    )
