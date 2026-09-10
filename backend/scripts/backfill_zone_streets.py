"""One-time batch job: reverse-geocode every zone's centre point to a street
name via Google's classic Geocoding API, and store it on zones.nearest_street.

Why this is a batch job and not a live lookup: the 2,388 zones are static
(they come from the offline tree-canopy clustering pipeline), so their
nearest street never changes on its own. Reverse-geocoding all of them once
and reading the stored column on every request is far cheaper and faster
than calling Google on every /api/zones request, and it means the frontend
never has to handle geocoding latency or failures at request time.

Usage:
    cd backend
    python -m scripts.backfill_zone_streets

Safe to re-run: it only selects rows where nearest_street IS NULL, so a
run that gets interrupted (rate limit, network blip, Ctrl-C) can just be
started again and will pick up where it left off. It commits periodically
rather than once at the end, for the same reason.

Requires GOOGLE_MAPS_API_KEY / DATABASE_URL to already be configured the
same way the FastAPI app reads them (see app/config.py).
"""

from __future__ import annotations

import time

import httpx
from sqlalchemy import text

from app.config import settings
from app.db import engine

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
BATCH_COMMIT_EVERY = 25
REQUEST_DELAY_SECONDS = 0.05  # be polite to the API; this is a one-off script, not a hot path


def main() -> None:
    if not settings.google_maps_api_key:
        raise SystemExit("GOOGLE_MAPS_API_KEY is not configured — see backend/app/config.py.")

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS nearest_street TEXT"))

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT cluster_id, center_lat, center_lon
                FROM zones
                WHERE nearest_street IS NULL
                ORDER BY cluster_id
                """
            )
        ).all()

    total = len(rows)
    if not total:
        print("Nothing to do — every zone already has a nearest_street.")
        return

    print(f"Reverse-geocoding {total} zone(s)...")
    updated = 0
    skipped = 0
    with engine.connect() as connection:
        for index, row in enumerate(rows, start=1):
            street = _reverse_geocode(row.center_lat, row.center_lon)
            if street is None:
                skipped += 1
            else:
                connection.execute(
                    text("UPDATE zones SET nearest_street = :street WHERE cluster_id = :id"),
                    {"street": street, "id": row.cluster_id},
                )
                updated += 1

            if index % BATCH_COMMIT_EVERY == 0 or index == total:
                connection.commit()
                print(f"  {index}/{total} processed ({updated} updated, {skipped} skipped)")

            time.sleep(REQUEST_DELAY_SECONDS)

    print(f"Done. {updated} zone(s) updated, {skipped} skipped (no street found).")


def _reverse_geocode(lat: float, lon: float) -> str | None:
    """Return the nearest street name for a coordinate, or None if Google
    returned nothing usable. Failures here are logged and skipped rather
    than raised, so one bad row doesn't abort the whole backfill."""
    try:
        response = httpx.get(
            GEOCODE_URL,
            params={
                "latlng": f"{lat},{lon}",
                "key": settings.google_maps_api_key,
                "result_type": "route",
                "language": "en-AU",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as error:
        print(f"  warning: geocoding request failed for ({lat}, {lon}): {error}")
        return None

    if data.get("status") != "OK" or not data.get("results"):
        return None

    # The "route" result type filter above biases results to street-level
    # matches; fall back to parsing the first address component named
    # "route" in case the filter still returns a broader result type.
    result = data["results"][0]
    for component in result.get("address_components", []):
        if "route" in component.get("types", []):
            return component["long_name"]
    return result.get("formatted_address")


if __name__ == "__main__":
    main()
