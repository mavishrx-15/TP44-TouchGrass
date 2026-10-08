"""Map and zone endpoints for Epic 1, plus the zone data Epic 2 routing needs.

API CONTRACT — agreed between frontend and backend before implementation.
Change this file and tell the other side; do not change response shapes silently.

Base path: /api

    GET /api/precincts              suburbs available in the search dropdown
    GET /api/species                genera available in the map filter panel
    GET /api/zones?precinct=...     tree-dense areas, ranked (US1.1, US1.2)
    GET /api/trees?zoneId=...       individual trees for map rendering (US1.3)

Every rule below comes from "16 Acceptance Criteria" in the governance
portfolio, not from a guess made here. Where the criteria name a formula or a
threshold, that formula is used verbatim, because the criteria are what the
build is assessed against.

Responses are camelCase and match frontend/src/types/discovery.ts field for
field, so the frontend can swap discovery.mock.ts for a fetch without touching
a component. The database columns are snake_case; the mapping happens here.

    database column           API field         why
    ------------------------  ----------------  ---------------------------
    zones.cluster_id          id                frontend calls it id
    zones.center_lat/_lon     center.lat/.lng   nested, like every map library
    trees.display_category    genus             the real name for the value
    year_planted_display      plantingAge       "2012" is not what a card shows

A precinct is addressed by slug ("north-melbourne"), which is what
/api/precincts returns as id. The display name works too, so either side can
use whichever it has.

Error handling:

    unknown precinct              404 with {"detail": "..."}
    missing/invalid parameter     422 (FastAPI default)
    valid query, nothing matches  200 with []

TWO DEFINITIONS OF A PRECINCT
-----------------------------
The acceptance criteria use trees.precinct in US1.1 and zones.precinct in
US1.2, and 1,586 trees (1.9%) disagree between the two — boundary effects from
the clustering. Both are implemented as written:

    /api/precincts   counts through trees.precinct     (US1.1)
    /api/zones       lists through zones.precinct      (US1.2)

For Kensington that is 7,552 trees / 216 zones in the snapshot against 209
zones in the list. The home page shows the snapshot and at most three zone
cards, never a total of the list, so the two never appear side by side as
numbers that ought to match. Raised with the team; this file follows the
criteria until they say otherwise.

All 20 precincts in trees.precinct are returned, including the five
(Brunswick, Brunswick West, Fishermans Bend, North And West Melbourne,
Richmond) that hold 202 trees between them but own no zones. They are the
case Epic 1's Definition of Done asks for — "a clear message is displayed
when a searched precinct has no matching data" — so hiding them would leave
that criterion untestable. /api/zones returns [] for them, which is the
signal to show that message.

DENSITY TIERS (US1.2)
---------------------
The 25th and 75th percentiles of zones.tree_count, which are 10 and 37:

    High     > 37 trees      595 zones (25%)
    Medium   10-37 trees   1,235 zones (52%)
    Low      < 10 trees      558 zones (23%)

ZONE GEOMETRY (US1.3)
---------------------
Zones draw as translucent squares, not circles. cluster_id is the rounded
centre of a 0.001-degree grid cell ("-37.795_144.915"), so the cell spans
that point plus or minus 0.0005 — roughly 110m north-south, 88m east-west at
this latitude. Verified: all 82,058 trees fall inside their own cell. The
bounds are returned rather than left to the frontend, so both sides draw the
same square.

DISTANCE (US1.2)
----------------
distanceKm is measured from the precinct's reference point — the mean
latitude and longitude of its trees — to the zone centre, not from the user's
live position. It is a fixed property of the zone, so it is computed here
once instead of in the browser.

The distance *filter* in US1.3 is a different thing: it measures from the
map's current centre as the user pans, and belongs in the frontend.

PAYLOAD SIZES
-------------
Parkville holds 28,497 trees; returning them unbounded is several megabytes
per request. Render zones first, load trees for one zone when the user opens
it. US1.2 asks for at most three zone cards on the home page — pass limit=3.

NOT RETURNED, ON PURPOSE
------------------------
    label, description   display text; US1.2 gives the label format
                         ("Tree-Dense Zone — Kensington") and it needs no
                         database lookup
    mapPosition          placeholder geometry from the mock map; use bounds

Not covered here: parks. The dataset has no park names or boundaries, so
park cards and the Green Spaces layer were cut for this iteration and
replaced by zone cards. Epic 2's route endpoints are a separate module.
"""

import re
from datetime import date
from math import asin, cos, radians, sin, sqrt
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import bindparam, text

from app.db import SessionDep
from app.security import require_access_token

router = APIRouter()


@router.get("/zones/{zone_id}/facts", dependencies=[Depends(require_access_token)])
def zone_facts(zone_id: str, session: SessionDep) -> dict:
    zone = session.execute(text("SELECT tree_count FROM zones WHERE cluster_id=:id"), {"id": zone_id}).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Unknown zone.")
    names = session.execute(text("""SELECT common_name, COUNT(*) AS n FROM trees
        WHERE cluster_id=:id GROUP BY common_name ORDER BY n DESC, common_name LIMIT 2"""), {"id": zone_id}).all()
    return {"treeCount": zone.tree_count, "density": _density(zone.tree_count),
            "commonNames": [row.common_name for row in names]}

# US1.2: the 25th and 75th percentiles of zones.tree_count.
DENSITY_HIGH = 37
DENSITY_LOW = 10

# US1.3: cluster_id is the rounded centre of a 0.001-degree cell.
GRID_HALF = 0.0005

EARTH_RADIUS_KM = 6371.0

Density = Literal["High", "Medium", "Low"]


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


class Coordinates(BaseModel):
    lat: float
    lng: float


class Bounds(BaseModel):
    """The zone's grid cell, ready to hand to a map rectangle."""

    north: float
    south: float
    east: float
    west: float


class Precinct(BaseModel):
    """One entry in the search dropdown, and the US1.1 neighbourhood snapshot.

    All four figures are counted through trees.precinct, as US1.1 specifies.
    """

    id: str
    name: str
    referencePoint: Coordinates
    treeCount: int
    zoneCount: int
    speciesCount: int


class Genus(BaseModel):
    """One entry in the map filter panel. Replaces the hard-coded Figma list,
    which offered Jacaranda (zero trees in the data) and omitted five genera
    that hold thousands."""

    genus: str
    treeCount: int


class Zone(BaseModel):
    """A tree-dense area. center and treeCount are also what Epic 2 reads when
    scoring candidate routes."""

    id: str
    precinctId: str
    center: Coordinates
    bounds: Bounds
    treeCount: int
    density: Density
    dominantGenus: str | None  # null when the zone holds nothing but "Other"
    distanceKm: float


class Tree(BaseModel):
    """One tree, as rendered on the map and in the detail popup."""

    id: str  # trees.com_id, sent as a string to match the frontend type
    precinctId: str
    zoneId: str
    coordinates: Coordinates
    commonName: str
    scientificName: str
    family: str
    genus: str
    plantingAge: str
    lifeExpectancy: str
    locatedIn: Literal["Park", "Street"]


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


def _resolve_precinct(session: SessionDep, value: str) -> str:
    """Slug or display name to the canonical precinct name. 404 if neither.

    Validated against trees.precinct, so all 20 searchable precincts resolve —
    including the five that own no zones.
    """
    rows = session.execute(text("SELECT DISTINCT precinct FROM trees")).all()
    for (name,) in rows:
        if value == name or value == _slug(name):
            return name
    raise HTTPException(
        status_code=404,
        detail=f"Unknown precinct {value!r}. Use /api/precincts for valid values.",
    )


def _reference_point(session: SessionDep, precinct: str) -> Coordinates:
    """US1.1: the mean latitude and longitude of the precinct's trees."""
    row = session.execute(
        text("SELECT AVG(latitude) AS lat, AVG(longitude) AS lng FROM trees WHERE precinct = :p"),
        {"p": precinct},
    ).one()
    return Coordinates(lat=row.lat, lng=row.lng)


@router.get("/precincts", response_model=list[Precinct])
def list_precincts(session: SessionDep) -> list[Precinct]:
    """Searchable suburbs and their neighbourhood snapshot (US1.1).

    speciesCount counts distinct scientific_name, not the nine display
    genera — those would give every precinct the same 8 or 9 and tell the
    reader nothing. Kensington has 303 distinct species.
    """
    rows = session.execute(
        text(
            """
            SELECT precinct,
                   COUNT(*)                                          AS tree_count,
                   COUNT(DISTINCT cluster_id)                        AS zone_count,
                   COUNT(DISTINCT NULLIF(TRIM(scientific_name), '')) AS species_count,
                   AVG(latitude)                                     AS lat,
                   AVG(longitude)                                    AS lng
            FROM trees
            GROUP BY precinct
            ORDER BY tree_count DESC
            """
        )
    ).all()
    return [
        Precinct(
            id=_slug(r.precinct),
            name=r.precinct,
            referencePoint=Coordinates(lat=r.lat, lng=r.lng),
            treeCount=r.tree_count,
            zoneCount=r.zone_count,
            speciesCount=r.species_count,
        )
        for r in rows
    ]


@router.get("/species", response_model=list[Genus])
def list_species(session: SessionDep) -> list[Genus]:
    """Genera for the filter panel, most common first, with "Other" last.

    US1.3 names this legend exactly: Eucalyptus, Acacia, Ulmus, Platanus,
    Corymbia, Allocasuarina, Casuarina, Quercus, Other.
    """
    rows = session.execute(
        text(
            """
            SELECT display_category AS genus, COUNT(*) AS tree_count
            FROM trees
            GROUP BY display_category
            ORDER BY tree_count DESC
            """
        )
    ).all()
    found = [Genus(genus=r.genus, treeCount=r.tree_count) for r in rows]
    return [g for g in found if g.genus != "Other"] + [g for g in found if g.genus == "Other"]


@router.get("/zones", response_model=list[Zone])
def list_zones(
    session: SessionDep,
    precinct: Annotated[str, Query(description="Slug or name from /api/precincts")],
    density: Annotated[Density | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[Zone]:
    """Tree-dense areas in one precinct, densest first (US1.2).

    Powers both the home page area cards and the map's density overlays. The
    home page shows at most three, so pass limit=3 there.

    An empty list is a valid answer, not an error: five precincts own no
    zones, and that is the case the "no matching data" message exists for.
    """
    name = _resolve_precinct(session, precinct)

    clause = ""
    if density == "High":
        clause = f"AND tree_count > {DENSITY_HIGH}"
    elif density == "Medium":
        clause = f"AND tree_count >= {DENSITY_LOW} AND tree_count <= {DENSITY_HIGH}"
    elif density == "Low":
        clause = f"AND tree_count < {DENSITY_LOW}"

    rows = session.execute(
        text(
            f"""
            SELECT cluster_id, center_lat, center_lon, tree_count, precinct
            FROM zones
            WHERE precinct = :p {clause}
            ORDER BY tree_count DESC
            LIMIT :limit
            """
        ),
        {"p": name, "limit": limit},
    ).all()
    if not rows:
        return []

    origin = _reference_point(session, name)
    top = _dominant_genus({r.cluster_id for r in rows}, session)
    return [
        Zone(
            id=r.cluster_id,
            precinctId=_slug(r.precinct),
            center=Coordinates(lat=r.center_lat, lng=r.center_lon),
            bounds=_bounds(r.cluster_id),
            treeCount=r.tree_count,
            density=_density(r.tree_count),
            dominantGenus=top.get(r.cluster_id),
            distanceKm=_distance_km(origin.lat, origin.lng, r.center_lat, r.center_lon),
        )
        for r in rows
    ]


def _dominant_genus(zone_ids: set[str], session: SessionDep) -> dict[str, str]:
    """Most common genus per zone, ignoring "Other".

    "Other" covers 30,898 trees — 38% of the dataset — so it wins the count in
    most zones while telling the reader nothing. A zone whose trees are all
    "Other" gets no label rather than a useless one.
    """
    rows = session.execute(
        text(
            """
            SELECT cluster_id, display_category, COUNT(*) AS n
            FROM trees
            WHERE cluster_id IN :ids AND display_category <> 'Other'
            GROUP BY cluster_id, display_category
            ORDER BY cluster_id, n DESC
            """
        ).bindparams(bindparam("ids", expanding=True)),
        {"ids": list(zone_ids)},
    ).all()
    best: dict[str, str] = {}
    for r in rows:
        best.setdefault(r.cluster_id, r.display_category)
    return best


@router.get("/trees", response_model=list[Tree])
def list_trees(
    session: SessionDep,
    zoneId: Annotated[str | None, Query(description="Zone id — preferred")] = None,
    precinct: Annotated[str | None, Query(description="Whole suburb — always capped")] = None,
    genus: Annotated[str | None, Query(description="Value from /api/species")] = None,
    locatedIn: Annotated[Literal["Park", "Street"] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 500,
) -> list[Tree]:
    """Individual trees for map rendering and the detail popup (US1.3).

    Give either zoneId or precinct. zoneId is preferred: the largest zone
    holds 767 trees, while Parkville holds 28,497 and will silently hit the
    cap.

    genus backs the species filter, locatedIn backs the Street/Park search
    US1.3 asks the map's search box to accept.
    """
    if (zoneId is None) == (precinct is None):
        raise HTTPException(status_code=422, detail="Give exactly one of zoneId or precinct.")

    where = ["1 = 1"]
    params: dict[str, object] = {"limit": limit}
    if zoneId is not None:
        where.append("t.cluster_id = :zone_id")
        params["zone_id"] = zoneId
    else:
        where.append("z.precinct = :precinct")
        params["precinct"] = _resolve_precinct(session, precinct)
    if genus is not None:
        where.append("t.display_category = :genus")
        params["genus"] = genus
    if locatedIn is not None:
        where.append("t.located_in = :located_in")
        params["located_in"] = locatedIn

    rows = session.execute(
        text(
            f"""
            SELECT t.com_id, t.common_name, t.scientific_name, t.family,
                   t.latitude, t.longitude, t.display_category,
                   t.useful_life_expectency, t.year_planted_display,
                   t.located_in, t.cluster_id, z.precinct
            FROM trees t
            JOIN zones z ON z.cluster_id = t.cluster_id
            WHERE {" AND ".join(where)}
            ORDER BY t.com_id
            LIMIT :limit
            """
        ),
        params,
    ).all()
    return [
        Tree(
            id=str(r.com_id),
            precinctId=_slug(r.precinct),
            zoneId=r.cluster_id,
            coordinates=Coordinates(lat=r.latitude, lng=r.longitude),
            commonName=r.common_name,
            scientificName=r.scientific_name,
            family=r.family,
            genus=r.display_category,
            plantingAge=_planting_age(r.year_planted_display),
            lifeExpectancy=r.useful_life_expectency,
            locatedIn=r.located_in,
        )
        for r in rows
    ]
