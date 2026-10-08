# Backend deployment configuration

Set these values in the backend runtime's secret/environment configuration.
Do not commit real values or expose server-side credentials through frontend
build variables such as `VITE_*`.

## Required configuration

| Variable | Required value |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy connection URL for PostgreSQL in deployment. `sqlite:///./touchgrass.db` is suitable only for local development. |
| `ACCESS_TOKEN` | A long, randomly generated bearer token. Every `/api/*` endpoint requires `Authorization: Bearer <token>`; `/health` is the only public endpoint. |
| `CBD_BOUNDARY_GEOJSON` | Authoritative Hoddle Grid GeoJSON as a `Polygon` or `MultiPolygon`, including any interior rings. The API fails closed when it is missing or invalid; do not replace it with a guessed rectangle or precinct boundary. |
| `GOOGLE_MAPS_API_KEY` | Server-side key enabled and restricted to the Google Places and Routes APIs. Required for place lookup and walking-route calculation. |

`CORS_ORIGINS` should list only the deployed frontend origins, comma-separated.
`HIGH_POLLEN_SPECIES` should be a comma-separated list of exact
`trees.common_name` values designated high-pollen by the project data source.
If it is empty, pollen ranking cannot claim a low-pollen route and the
preference is reported as unverified.

There is no street-noise or sun-exposure dataset configured. Quiet/lively and
shade preferences are therefore returned as unverified. The repository also
has no authoritative zone-to-street-name mapping. Until one is supplied, area
labels use the real precinct plus a stable tree-zone ID, for example
`Kensington · Tree zone -37.795_144.915`. To use the prototype's
`precinct · nearest street` label, supply a maintained zone-to-street mapping
with documented provenance; do not infer or invent street names.

## Private photo storage

Photo upload and signed-photo reads require `SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_STORAGE_BUCKET`. Create the bucket
in Supabase Storage with **Public bucket disabled**, keep it private, and grant
access only through the backend service role. The API checks that the bucket is
private before upload or signed-URL generation and will fail rather than make
it public. Never put the service-role key in the frontend.

## Database setup

1. Create the PostgreSQL database and apply `database/schema.sql`. This creates
   the core tree tables and the current weather/pin tables.
2. Load the tree dataset using the project's controlled data-loading process.
3. Run `python -m database.migrate` from `backend/`. The migration runner
   records the existing migration tables from `schema.sql` rather than trying
   to create them again; on a database with only the core tables, it applies
   the numbered SQL migrations.
4. Set the runtime variables above and start the API with the deployment's
   normal ASGI command, for example `uvicorn app.main:app`.

For local tests, run `DATABASE_URL=sqlite:// .venv/bin/pytest` from
`backend/`. The suite exercises the SQLite schema and migration path. A live
PostgreSQL service is not part of the local test suite.

## Access-token limitation

`ACCESS_TOKEN` is a shared bearer credential, not user authentication. Do not
embed it in a public browser application. A production browser client needs a
trusted server-side gateway/session flow that adds this credential without
exposing it; that frontend/auth integration is not implemented by this
backend-only change.

On the first pin created for a new `deviceId`, the API returns a random
`deviceToken` once. The client must retain it and send it in the
`X-Device-Token` header with `X-Device-ID` when reading that device's pending
content or submitting a message/report. Subsequent pin creation for that
device also requires the token. Do not log or expose the token; only a hash is
stored. Existing pre-migration device IDs have no proof of ownership and
cannot be reclaimed; their pending content is withheld until it is re-submitted
under a newly registered device ID.

The device token is a transferable bearer capability, not user authentication.
The client still chooses device IDs, so creating additional IDs can reset the
per-device rate limit. This remains best-effort abuse control; account
authentication and broader rate limits require a trusted identity or gateway.
