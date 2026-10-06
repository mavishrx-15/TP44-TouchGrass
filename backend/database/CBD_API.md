# Iteration 3: CBD and tree data handoff

Implemented on `feature/iteration3-cbd-data`, based on `origin/dev` at
`0cd21d1`. No schema migration is needed. The existing zones.street_name
column is required, as on dev; apply migration 001 to an older database.

## Boundary confirmation still needed

The design PDF says Hoddle Grid and 186 zones but supplies no coordinates.
`app/config.py` currently contains a **provisional**, rotated outline. It is
not an official cadastral boundary or the team's confirmed prototype box.
Against the checked-in dataset it includes 156 zones (0 High, 91 Medium,
65 Low), not the PDF's 186. Confirm the outline with the frontend/data owner
before deployment or acceptance testing. Do not hard-code the PDF's count.

Set `CBD_BOUNDARY` to a JSON list of `[longitude, latitude]` vertices; the
last vertex is automatically closed if necessary. Restart the backend after
changing it. The map, zone selection, Places validation and route endpoint
all use this same configured polygon, with edges included. A zone is selected
by its stored centre. Its original grid cell is returned unchanged, so the
frontend may clip cell fills at the coverage edge if needed.

## Authentication

Both new GET endpoints require the same `Authorization: Bearer <token>` as
the existing APIs. Obtain it from `/api/access/verify`. No mood, GPS history,
points or visits are stored by these changes.

## GET /api/cbd/zones

Returns an object:

- `boundary`: GeoJSON Polygon, coordinate order `[longitude, latitude]`.
- `bounds`: `{north, south, east, west}`, the polygon's enclosing rectangle.
- `zoneCount`: actual number returned; no default limit or pagination cap.
- `densityCounts`: `{High, Medium, Low}` counts for the entire returned set.
- `zones`: existing Zone fields plus `label`, formatted `precinct · street`
  or precinct alone if street_name is absent.

Density preserves existing thresholds: High >37, Medium 10–37, Low <10.
`metrics.canopy` is a 0–100 percentile across the CBD set (ties share a rank),
not measured canopy cover. Existing `/api/zones?precinct=…` remains intact.
`distanceKm` on this map response is measured from the outline's vertex mean,
not the user: compute user-relative distance separately for recommendations.
Pollen information remains a species/family proxy, not live measurement.
Use each zone's exact `id` and `bounds`; do not reconstruct ids by rounding GPS.

## GET /api/zones/{zone_id}/facts

Example response:

```json
{
  "zoneId": "-37.818_144.974",
  "treeCount": 143,
  "density": "High",
  "topSpecies": [
    {"commonName": "Red flowering ironbark", "count": 95},
    {"commonName": "Flooded gum", "count": 42}
  ]
}
```

Example values are illustrative of the design document, not a guarantee the
zone is inside the final boundary. `treeCount` comes from zones.tree_count;
topSpecies is grouped directly from trees.common_name across all trees in
that zone, with descending count then alphabetical name for stable ties.
Names are trimmed and blank names omitted; fewer than two names is valid.
This is common-name grouping, as requested in the build doc, not genus data.
Unknown ids return 404. Existing known zones outside the CBD can still supply
facts for compatibility; only the CBD endpoint selects map destinations.

## Shared coverage validation

- `/api/places/autocomplete` uses Google's `locationRestriction.rectangle`,
  replacing the former 50 km location bias. It then resolves prediction
  coordinates and filters them against the actual rotated polygon.
- `/api/places/{place_id}` independently validates the resolved position.
- `/api/routes` rejects either endpoint outside coverage before calling Google.
- Outside coverage returns HTTP 422 with `{"detail":"outside_cbd"}`.
- Future pin and Sprout route modules should reuse `app.cbd.require_inside`.
- No positions were added to query strings or request-body logs.

Prediction validation adds one Place Details call per prediction. This is a
correctness tradeoff for polygon filtering, with extra Google latency/usage;
frontend search should remain debounced. Upstream failures remain explicit
errors rather than silently offering unchecked places.

Google reference:
https://developers.google.com/maps/documentation/places/web-service/place-autocomplete

## Verification

From backend: `python -m pytest -q`, `black --check .`, `ruff check .`.
Tests use temporary SQLite and mocked Google responses, including >50 zones,
polygon edges, outside points within the bounding rectangle, density
thresholds, missing species, exact ids, permissions and rejection before a
paid Routes request. Shared Supabase and live paid APIs are not exercised.

No Sprout templates, route ranking, weather, uploads or frontend UI changes
are included in this task.
