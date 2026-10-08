"""CBD map and facts implementation, independent of HTTP routing."""

from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.cbd import boundary, contains, coverage_bounds
from app.schemas.cbd import CbdZone, CbdZones, Outline, SpeciesFact, ZoneFacts
from app.schemas.common import Coordinates
from app.schemas.map_data import Bounds, Density
from app.services.zone_data import ZoneProfile, _density, _profiles, _zone


def _zones_from_rows(
    rows, session: Session, origin: Coordinates
) -> tuple[list[CbdZone], dict[Density, int]]:
    """CbdZone objects and density tallies for a set of `zones` table rows.

    Shared by cbd_zones() (CBD-bounded, for the /api/cbd/zones map) and
    all_zones() (citywide, for Sprout's route planning) so the two only ever
    differ in which rows they pass in, not in how a row becomes a CbdZone.
    """
    profiles = _profiles({r.cluster_id for r in rows}, session) if rows else {}
    # Equivalent to PERCENT_RANK, including ties, over the row set passed in.
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
    return zones, density_counts


def cbd_zones(session: Session) -> CbdZones:
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
    ring = boundary()
    vertices = ring[:-1]
    origin = Coordinates(
        lat=sum(lat for _, lat in vertices) / len(vertices),
        lng=sum(lng for lng, _ in vertices) / len(vertices),
    )
    zones, density_counts = _zones_from_rows(rows, session, origin)
    return CbdZones(
        boundary=Outline(coordinates=[ring]),
        bounds=Bounds(**bounds),
        zoneCount=len(zones),
        densityCounts=density_counts,
        zones=zones,
    )


def all_zones(session: Session) -> list[CbdZone]:
    """Every zone citywide, not just the CBD - for Sprout's route planning.

    Team decision: Sprout and the live walk are no longer CBD-only, so
    candidate destinations are every precinct's zones, the same set
    /api/precincts + /api/zones already serve the old Explore map. The CBD
    polygon and /api/cbd/zones are untouched here - this is a second, wider
    view over the same `zones` table, not a replacement for the first.
    """
    rows = session.execute(
        text(
            """
            SELECT cluster_id, center_lat, center_lon, tree_count, precinct, street_name
            FROM zones
            ORDER BY tree_count DESC, cluster_id
            """
        )
    ).all()
    if not rows:
        return []
    origin = Coordinates(
        lat=sum(r.center_lat for r in rows) / len(rows),
        lng=sum(r.center_lon for r in rows) / len(rows),
    )
    zones, _ = _zones_from_rows(rows, session, origin)
    return zones


def zone_facts(zone_id: str, session: Session) -> ZoneFacts:
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
