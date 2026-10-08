"""Existing map contracts, shared without importing a router."""

from typing import Literal

from pydantic import BaseModel

from app.schemas.common import Coordinates

Density = Literal["High", "Medium", "Low"]


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


class ZoneGenus(BaseModel):
    """One line of a card's tree breakdown. Named apart from Genus, which is
    the filter-panel shape and uses the frontend's older field names."""

    name: str
    count: int


class AreaMetrics(BaseModel):
    """Scores out of 100, none of them a measurement.

    canopy is a percentile within the precinct, not across the city: 85 means
    this area holds more trees than 85% of the other zones in the same suburb.
    It is the same tree_count behind the existing High/Medium/Low tiers, read
    as a number rather than three buckets — so it says nothing about crown area,
    which the dataset does not record.

    Ranking per precinct rather than citywide is what makes it useful on a
    card: the cards only ever compare areas inside one suburb, and a citywide
    scale would leave every zone in a leafy precinct at the top and every zone
    in a sparse one at the bottom.

    parkShare is the share of trees standing in a park rather than on a street
    — the only shade or noise signal the data carries.

    lowAllergyShare and highPollenTrees come from a species-name proxy, not
    pollen measurement, and the card labels them as such.
    """

    canopy: int
    parkShare: int
    lowAllergyShare: int | None = None
    highPollenTrees: int | None = None


class Zone(BaseModel):
    """A tree-dense area. center and treeCount are also what Epic 2 reads when
    scoring candidate routes."""

    id: str
    precinctId: str
    precinctName: str
    center: Coordinates
    bounds: Bounds
    treeCount: int
    density: Density
    dominantGenus: str | None  # null when the zone holds nothing but "Other"
    distanceKm: float
    nearestStreet: str | None  # null when reverse geocoding found no nearby road
    metrics: AreaMetrics
    genera: list[ZoneGenus]
    dataNotes: list[str]  # gaps the card shows rather than hides


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
