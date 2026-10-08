"""Shared database aggregates and zone conversion; no HTTP routing."""

import re
from datetime import date
from math import asin, cos, radians, sin, sqrt

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.schemas.common import Coordinates
from app.schemas.map_data import AreaMetrics, Bounds, Density, Zone, ZoneGenus

DENSITY_HIGH = 37
DENSITY_LOW = 10
GRID_HALF = 0.0005
OTHER = "Other"
GENERA_SHOWN = 3  # the recommendation card has room for three
HIGH_POLLEN_GENERA = ("Platanus", "Casuarina", "Allocasuarina", "Quercus", "Ulmus")
HIGH_POLLEN_FAMILIES = ("Cupressaceae", "Oleaceae")
EARTH_RADIUS_KM = 6371.0


def _density(tree_count: int) -> Density:
    if tree_count > DENSITY_HIGH:
        return "High"
    if tree_count >= DENSITY_LOW:
        return "Medium"
    return "Low"


def _slug(precinct: str) -> str:
    """Precinct name to url-safe id. "North Melbourne" -> "north-melbourne"."""
    return re.sub(r"[^a-z0-9]+", "-", precinct.lower()).strip("-")


def _planting_age(year_planted: str | None) -> str:
    """Planting year to the age chip the card shows.

    A third of the trees record "Established (exact year unknown)" instead of
    a year. Those get "Established" rather than an invented number.
    """
    if year_planted and year_planted.isdigit():
        return f"~{date.today().year - int(year_planted)} yrs"
    return "Established"


def _distance_km(from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> float:
    """Great-circle distance, rounded to the 100m the cards display."""
    d_lat = radians(to_lat - from_lat)
    d_lng = radians(to_lng - from_lng)
    a = sin(d_lat / 2) ** 2 + cos(radians(from_lat)) * cos(radians(to_lat)) * sin(d_lng / 2) ** 2
    return round(2 * EARTH_RADIUS_KM * asin(sqrt(a)), 1)


class ZoneProfile:
    """Per-zone tallies, assembled from the grouped rows.

    "Other" is left out of the genus mix throughout. It covers 30,898 trees —
    38% of the dataset — so it wins the count in most zones while telling the
    reader nothing, and a card listing "Other, 58 trees" is worse than one
    listing two real genera.
    """

    def __init__(self) -> None:
        self.total = 0
        self.park = 0
        self.high_pollen = 0
        self.genera: dict[str, int] = {}

    def ranked(self) -> list[ZoneGenus]:
        top = sorted(self.genera.items(), key=lambda item: (-item[1], item[0]))
        return [ZoneGenus(name=name, count=count) for name, count in top[:GENERA_SHOWN]]

    def dominant(self) -> str | None:
        ranked = self.ranked()
        return ranked[0].name if ranked else None

    def metrics(self, canopy_percentile: int) -> AreaMetrics:
        return AreaMetrics(
            canopy=canopy_percentile,
            parkShare=self._share(self.park),
            lowAllergyShare=self._share(self.total - self.high_pollen),
            highPollenTrees=self.high_pollen,
        )

    def _share(self, part: int) -> int:
        return round(100 * part / self.total) if self.total else 0


def _bounds(cluster_id: str) -> Bounds:
    """The 0.001-degree cell a cluster_id names.

    Rounded to six decimals — a tenth of a metre, far finer than the grid —
    because binary floats turn -37.795 - 0.0005 into -37.795500000000004, and
    neighbouring cells drawn from unrounded edges can show a hairline seam.
    """
    lat, lng = (float(part) for part in cluster_id.split("_"))
    return Bounds(
        north=round(lat + GRID_HALF, 6),
        south=round(lat - GRID_HALF, 6),
        east=round(lng + GRID_HALF, 6),
        west=round(lng - GRID_HALF, 6),
    )


def _zone(row, profile: ZoneProfile, origin: Coordinates) -> Zone:
    return Zone(
        id=row.cluster_id,
        precinctId=_slug(row.precinct),
        precinctName=row.precinct,
        center=Coordinates(lat=row.center_lat, lng=row.center_lon),
        bounds=_bounds(row.cluster_id),
        treeCount=row.tree_count,
        density=_density(row.tree_count),
        dominantGenus=profile.dominant(),
        distanceKm=_distance_km(origin.lat, origin.lng, row.center_lat, row.center_lon),
        nearestStreet=row.street_name,
        metrics=profile.metrics(round(100 * row.canopy_rank)),
        genera=profile.ranked(),
        dataNotes=_data_notes(row.street_name),
    )


def _data_notes(street_name: str | None) -> list[str]:
    """What this area cannot tell you, said out loud.

    The design decision is explicit: a gap is flagged on the card, not hidden
    and not filled with something invented. Both of these are real gaps today.
    """
    notes = ["Pollen indicators are species-based proxies, not live pollen measurements."]
    if street_name is None:
        notes.insert(0, "No nearby street resolved; named by precinct.")
    return notes


def _profiles(zone_ids: set[str], session: Session) -> dict[str, ZoneProfile]:
    """Genus mix and park share for every zone in one query.

    Grouping by category and location together means the genus breakdown, the
    dominant genus and the park share all fall out of the same rows, instead of
    a query per card.
    """
    rows = session.execute(
        text(
            """
            SELECT cluster_id, display_category, family, located_in, COUNT(*) AS n
            FROM trees
            WHERE cluster_id IN :ids
            GROUP BY cluster_id, display_category, family, located_in
            """
        ).bindparams(bindparam("ids", expanding=True)),
        {"ids": list(zone_ids)},
    ).all()

    profiles: dict[str, ZoneProfile] = {}
    for row in rows:
        profile = profiles.setdefault(row.cluster_id, ZoneProfile())
        profile.total += row.n
        if row.located_in == "Park":
            profile.park += row.n
        if row.display_category in HIGH_POLLEN_GENERA or row.family in HIGH_POLLEN_FAMILIES:
            profile.high_pollen += row.n
        if row.display_category != OTHER:
            profile.genera[row.display_category] = (
                profile.genera.get(row.display_category, 0) + row.n
            )
    return profiles
