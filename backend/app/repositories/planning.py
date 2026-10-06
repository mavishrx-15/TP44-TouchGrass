"""Destination queries owned by the route developer; share CBD coverage rules."""

from sqlalchemy.orm import Session

from app.schemas.cbd import CbdZone


def candidate_zones(session: Session) -> list[CbdZone]:
    # TODO: query all CBD zones with aggregates; no nearest-precinct cap.
    raise NotImplementedError("Destination candidate query is not implemented.")
