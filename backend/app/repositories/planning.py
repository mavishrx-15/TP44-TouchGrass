"""Destination candidates for route planning.

Every zone inside the CBD outline is a candidate — there is no nearest-precinct
cap, which is what used to send a start at the State Library to a one-zone
precinct. The CBD map already assembles exactly this set, with the tree
statistics planning ranks on, so it is reused rather than queried twice.
"""

from sqlalchemy.orm import Session

from app.schemas.cbd import CbdZone
from app.services.cbd_data import cbd_zones


def candidate_zones(session: Session) -> list[CbdZone]:
    return cbd_zones(session).zones
