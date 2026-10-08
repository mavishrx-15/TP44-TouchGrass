"""Destination candidates for route planning.

Every zone citywide is a candidate — not CBD-only any more (team decision),
and there is no nearest-precinct cap either, which is what used to send a
start at the State Library to a one-zone precinct. app.services.cbd_data
already assembles this zone shape with the tree statistics planning ranks
on, so all_zones() is reused rather than querying twice.
"""

from sqlalchemy.orm import Session

from app.schemas.cbd import CbdZone
from app.services.cbd_data import all_zones


def candidate_zones(session: Session) -> list[CbdZone]:
    return all_zones(session)
