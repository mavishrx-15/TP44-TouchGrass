"""Google Routes adapter: walking alternatives, with the steps Epic 6 needs.

Kept out of the routers. The request and error handling reuse the existing
Google helper rather than its HTTP handler, so a key or upstream failure here
reads exactly like one from /api/routes.
"""

from app.routers.routes import _google_request, _lat_lng
from app.schemas.common import Coordinates

COMPUTE_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

# The steps fields are what the walk's direction tips are built from (US6.3).
# They are on top of what /api/routes already requests; the design doc asks for
# a check that they stay in the same Google billing tier, which has not been
# confirmed yet.
FIELD_MASK = ",".join(
    [
        "routes.duration",
        "routes.distanceMeters",
        "routes.polyline.encodedPolyline",
        "routes.legs.steps.navigationInstruction.instructions",
        "routes.legs.steps.startLocation",
        "routes.legs.steps.distanceMeters",
    ]
)


def walking_alternatives(origin: Coordinates, destination: Coordinates) -> list[dict]:
    """Google's walking routes between two points, alternatives included.

    An empty list means Google found nothing, which is an answer, not an error:
    the caller moves on to its next candidate destination.
    """
    data = _google_request(
        "POST",
        COMPUTE_ROUTES_URL,
        field_mask=FIELD_MASK,
        json={
            "origin": {"location": {"latLng": _lat_lng(origin)}},
            "destination": {"location": {"latLng": _lat_lng(destination)}},
            "travelMode": "WALK",
            "computeAlternativeRoutes": True,
            "languageCode": "en-AU",
            "units": "METRIC",
        },
    )
    return data.get("routes", [])
