# Epic 3 & 4 implementation

All implementation is on `access-gate`. The existing map and routes foundation
was merged from `origin/main` at `eef4ec0`; other local branches are unchanged.
The pre-existing AI endpoint is retained (format/lint fixes only).

## Implemented

- **US3.0**: password verification against environment settings, HMAC-SHA256
  tokens with bounded lifetime, sessionStorage only, one global router guard.
  Unicode passwords work. Missing/short signing keys fail closed. The frontend
  clears expired sessions both on a timer and on a protected API's 401, then
  sends the user to the password page. Protected GET and POST requests carry
  the token. Map, Places, routes, DB check and AI APIs enforce the gate.
- **US3.1**: rebuilt homepage, shared `stores/journey.ts` location/preference
  state, 0–5 canopy/shade/noise/allergy weights, walking time, genus/family
  avoidance selection, resolved Places/precinct/device location, debounced
  autocomplete with cancellation, canopy/shade information dialogs, coverage
  validation using the shared haversine helper. Homepage backend needs only
  existing precinct and Places endpoints.
- **US3.2**: `/api/routes` still returns a list for compatibility, but exactly
  one `id: recommended` result. Tree-count canopy logic is preserved. Park
  share supplies the shade/noise proxy. Allergy score is the share of corridor
  trees outside the selected genera/families (OR, counted once per tree).
  All 0–1 scores are combined by the preference weights. Candidate canopy
  counts are normalised by the maximum candidate count. Within-budget walks
  take priority, followed by score and shorter duration; if none fits, the
  result explicitly says so. All-zero weights use the shortest available route.
  No tree samples means unknown park/allergy evidence, never a fabricated match.
- **US4.1**: `/personalised-route` has shared origin, editable destination,
  Walking/Transport toggle (`WALK`/`TRANSIT`), one route card and polyline,
  match-based “Why This Route?” copy, cancellation of outdated calculations,
  and a Google Maps directions link. Map overlay also uses one route.
- **US4.2**: `/recommendations` has three expanded cards per desktop row,
  stacking on mobile. Cards show Area Overview / Tree Info / Why This Area
  Matches. Zone API includes `nearestStreet` and an additive grouped
  `treeProfile` so ranking does not need a request per zone. Labels use precinct
  and nearest street with a precinct-only fallback. Haversine distances are
  recomputed from the resolved origin. Selecting a card opens its route.

## Explicit assumptions awaiting the full AC / Section B

- AC12 coverage: `VITE_COVERAGE_RADIUS_KM=5`, measured to the nearest supported
  precinct's reference point. This is configurable; it is not an assertion
  that the missing acceptance criteria specify five kilometres.
- “Best match” means weighted score >= 0.70 and within walking budget; otherwise
  the result says closest available match. Exact AC4/AC7 wording/thresholds were
  not provided. A transit journey does not apply a walking-only time cap.
- Walking time defaults to 30 minutes, configurable in the UI from 5–180.
  Recommendation estimates use straight-line distance at 4.8 km/h; actual route
  duration is displayed after calculation. Ranking considers up to 500 zones
  in the nearest precinct and returns the top three; fewer/no zones are handled.
- Shade/noise are park-tree proxies, not measured canopy, shadows or decibels.
  Allergy avoidance uses the user's chosen categories, not a medical risk table.
  No selected allergy category means the user must complete that preference.
- In-app live turn-by-turn navigation is deferred for the team. Google Maps
  may recalculate a different route from the same endpoints; the link says so.

## Run locally

1. Install backend dependencies: `cd backend` then
   `uv pip install --python .venv/bin/python -r requirements-dev.txt` (or pip).
2. Set `ACCESS_PASSWORD`, a random `ACCESS_TOKEN_SECRET` of at least 32 bytes,
   and optionally `ACCESS_TOKEN_TTL_SECONDS` (60–86400; default 3600).
3. For a fresh local dataset DB use `python -m app.seed`. **This replaces the
   local `backend/touchgrass.db`; never use it for a shared database.** Set
   `DATABASE_URL=sqlite:///./touchgrass.db`. The application also uses this
   SQLite URL if no database URL is supplied.
4. Existing PostgreSQL databases need the additive migration
   `backend/database/migrations/001_zone_street.sql` before this backend version.
   Existing SQLite databases need `ALTER TABLE zones ADD COLUMN street_name TEXT`
   once, or an explicit local re-seed.
5. Set backend `GOOGLE_MAPS_API_KEY` with Routes and Places APIs enabled and
   frontend `VITE_GOOGLE_MAPS_API_KEY` for map display. Set `VITE_API_BASE_URL`
   and `CORS_ORIGINS` to matching local origins.
6. Run `uvicorn app.main:app --reload --port 8080`; in frontend run `npm ci`
   followed by `npm run dev`.

## Street enrichment — explicit operator step

Contrary to the supplied baseline notes, neither `origin/main` nor `origin/dev`
contained the street column or enrichment script at inspection. The migration,
loader and `backend/database/enrich_zones.py` have now been added.
No deployment database or external geocoding service was modified during this work.
Until enriched, zones correctly display the precinct-only fallback.

From `backend`, enrich the local dataset in resumable batches:

```sh
python database/enrich_zones.py --contact YOUR_CONTACT_EMAIL --cache /tmp/touchgrass-streets.json --limit 100
```

The script caches responses, waits 1.1 seconds between uncached calls, stops on
HTTP errors, and allows a custom `--endpoint`. It follows the
[Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/).
After reviewing dataset changes and applying the migration to the intended DB,
run `python database/load_data.py --update-streets` with that DB's environment.
This mode updates only nonempty street names and preserves all other records;
rerunning the original full loader against an existing populated DB is unnecessary.
Attribution for enriched data: © OpenStreetMap contributors.

Public transport requests use Google's documented
[TRANSIT mode](https://developers.google.com/maps/documentation/routes/transit-route).

## Validation

- Backend: `python -m pytest -q`, `black --check .`, `ruff check .`.
- Frontend: `npm test`, `npm run format:check`, `npm run lint`, `npm run build`.
- Tests isolate SQLite and mock Google APIs; no shared DB or paid API is called.
- CI now runs these tests alongside its existing format/lint/build checks.
- Live Routes/Places responses and deployed street enrichment require the
  deployment's credentials and operator setup; mocked tests do not verify those.
