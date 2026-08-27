"""Map and zone endpoints for Epic 1, plus the zone data Epic 2 routing needs.

API CONTRACT — agreed between frontend and backend before implementation.
Change this file and tell the other side; do not change response shapes silently.

Base path: /api

    GET /api/precincts              suburbs available in the search dropdown
    GET /api/species                genera available in the map filter panel
    GET /api/zones?precinct=...     tree-dense areas, ranked (US1.1, US1.2)
    GET /api/trees?zoneId=...       individual trees for map rendering (US1.3)

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

That last rule matters: an empty result is not an error. Five precincts
(Brunswick, Brunswick West, Fishermans Bend, North And West Melbourne,
Richmond) hold 202 trees but have no zones at all, which is why
/api/precincts only lists the 15 that do — the dropdown cannot produce a
precinct that returns nothing.

A precinct means one thing here: the precinct of the zone. 1,586 trees
(1.9%) carry a trees.precinct that disagrees with the precinct of the zone
they sit in — boundary effects from the clustering. Counting one way for
zones and the other for trees makes the two halves of the same screen
disagree, so /api/trees?precinct= matches through zones as well. The
figures a user sees always add up.

dominantGenus is nullable. 270 of 2,388 zones (11%) hold nothing but
"Other", and a zone labelled "Other" tells the reader less than no label at
all. Render the chip only when the field is present.

Density labels are derived, not stored. Cut points come from the actual
distribution of zones.tree_count (median 20, 90th percentile 74, max 767):

    High     >= 75 trees     top 10% of zones
    Medium   20-74 trees
    Low      < 20 trees      bottom half

Payload sizes are the reason /api/trees is capped. Parkville alone holds
28,567 trees; returning them unbounded is several megabytes per request.
Render zones first, load trees for one zone when the user opens it.

Deliberately not returned, because the data cannot support them honestly:

    label, description   display text — build them in the component
    distanceKm           needs the browser's geolocation; compute it there
                         from center.lat/.lng so it updates as the user moves
    mapPosition          placeholder geometry for the mock map; a real map
                         positions from center.lat/.lng
    speciesCount         every precinct has 8 or 9 genera, so the number
                         cannot tell two cards apart — use zoneCount

Not covered here: parks. The dataset has no park names or boundaries, so
park cards and the Green Spaces layer were cut for this iteration and
replaced by zone cards. Species table (679 rows) is Epic 3.
"""

import re
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import bindparam, text

from app.db import SessionDep

router = APIRouter()

DENSITY_HIGH = 75
DENSITY_MEDIUM = 20

Density = Literal["High", "Medium", "Low"]


def _density(tree_count: int) -> Density:
    if tree_count >= DENSITY_HIGH:
        return "High"
    if tree_count >= DENSITY_MEDIUM:
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


class Coordinates(BaseModel):
    lat: float
    lng: float


class Precinct(BaseModel):
    """One entry in the search dropdown."""

    id: str
    name: str
    referencePoint: Coordinates  # noqa: N815 - matches the frontend type
    treeCount: int  # noqa: N815
    zoneCount: int  # noqa: N815


class Genus(BaseModel):
    """One entry in the map filter panel. Replaces the hard-coded Figma list,
    which offered Jacaranda (zero trees in the data) and omitted five genera
    that hold thousands."""

    genus: str
    treeCount: int  # noqa: N815


class Zone(BaseModel):
    """A tree-dense area. center and treeCount are also what Epic 2 reads when
    scoring candidate routes."""

    id: str
    precinctId: str  # noqa: N815
    center: Coordinates
    treeCount: int  # noqa: N815
    density: Density
    dominantGenus: str | None  # noqa: N815 - null when the zone is all "Other"


class Tree(BaseModel):
    """One tree, as rendered on the map and in the detail popup."""

    id: str  # trees.com_id, sent as a string to match the frontend type
    precinctId: str  # noqa: N815
    zoneId: str  # noqa: N815
    coordinates: Coordinates
    commonName: str  # noqa: N815
    scientificName: str  # noqa: N815
    family: str
    genus: str
    plantingAge: str  # noqa: N815
    lifeExpectancy: str  # noqa: N815
    locatedIn: Literal["Park", "Street"]  # noqa: N815


def _resolve_precinct(session: SessionDep, value: str) -> str:
    """Slug or display name to the canonical precinct name. 404 if neither."""
    rows = session.execute(text("SELECT DISTINCT precinct FROM zones")).all()
    for (name,) in rows:
        if value == name or value == _slug(name):
            return name
    raise HTTPException(
        status_code=404,
        detail=f"Unknown precinct {value!r}. Use /api/precincts for valid values.",
    )


@router.get("/precincts", response_model=list[Precinct])
def list_precincts(session: SessionDep) -> list[Precinct]:
    """Suburbs the user can search, ranked by tree count.

    Only the 15 precincts that have zones. Precincts with trees but no zones
    are excluded on purpose — see the module docstring.

    referencePoint is the tree-weighted centre of the precinct's zones, which
    is where the map should sit when the user picks it: it leans towards the
    trees rather than the geometric middle of the suburb.
    """
    rows = session.execute(
        text(
            """
            SELECT precinct,
                   COUNT(*)                                          AS zone_count,
                   SUM(tree_count)                                   AS tree_count,
                   SUM(center_lat * tree_count) / SUM(tree_count)    AS lat,
                   SUM(center_lon * tree_count) / SUM(tree_count)    AS lng
            FROM zones
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
        )
        for r in rows
    ]


@router.get("/species", response_model=list[Genus])
def list_species(session: SessionDep) -> list[Genus]:
    """Genera for the filter panel, most common first, with "Other" last."""
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
    """Tree-dense areas in one precinct, densest first (US1.1, US1.2).

    Powers both the home page area cards and the density circles on the map.
    """
    name = _resolve_precinct(session, precinct)

    clause = ""
    if density == "High":
        clause = f"AND tree_count >= {DENSITY_HIGH}"
    elif density == "Medium":
        clause = f"AND tree_count >= {DENSITY_MEDIUM} AND tree_count < {DENSITY_HIGH}"
    elif density == "Low":
        clause = f"AND tree_count < {DENSITY_MEDIUM}"

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

    top = _dominant_genus({r.cluster_id for r in rows}, session)
    return [
        Zone(
            id=r.cluster_id,
            precinctId=_slug(r.precinct),
            center=Coordinates(lat=r.center_lat, lng=r.center_lon),
            treeCount=r.tree_count,
            density=_density(r.tree_count),
            dominantGenus=top.get(r.cluster_id),
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
    zoneId: Annotated[str | None, Query(description="Zone id — preferred")] = None,  # noqa: N803
    precinct: Annotated[str | None, Query(description="Whole suburb — always capped")] = None,
    genus: Annotated[str | None, Query(description="Value from /api/species")] = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 500,
) -> list[Tree]:
    """Individual trees for map rendering and the detail popup (US1.3).

    Give either zoneId or precinct. zoneId is preferred: the largest zone
    holds 767 trees, while Parkville holds 28,567 and will silently hit the
    cap.
    """
    if (zoneId is None) == (precinct is None):
        raise HTTPException(status_code=422, detail="Give exactly one of zoneId or precinct.")

    where = ["1 = 1"]
    params: dict[str, object] = {"limit": limit}
    if zoneId is not None:
        where.append("t.cluster_id = :zone_id")
        params["zone_id"] = zoneId
    else:
        # Matched through the zone, not trees.precinct — see the module docstring.
        where.append("z.precinct = :precinct")
        params["precinct"] = _resolve_precinct(session, precinct)
    if genus is not None:
        where.append("t.display_category = :genus")
        params["genus"] = genus

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
