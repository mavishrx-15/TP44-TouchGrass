# Iteration 2: Epics 3 and 4

Branch: `feature/iteration2-personalised-routes`, based on `origin/dev`.
The existing Iteration 1 deployment and Cloud Run backend are unchanged.

## Preview

Run `npm ci` then `npm run dev` in `frontend`. Existing maps, Places search,
precincts, zones, trees and walking routes use the real backend by default.
Set `VITE_API_BASE_URL` to the existing Cloud Run URL (or your running local API).
Use `http://localhost:5173` locally; that origin is allowed by the deployed API.
`VITE_USE_MOCK_DATA=true` is an explicit, isolated fixture mode for tests only.
The new access endpoint is independently mocked with `VITE_MOCK_ACCESS=true`.
Use the public demo password `touchgrass-demo`. This password exercises the UI
only; it is **not** deployment protection. Never put a real access password into
a `VITE_` variable. No username, registration, user database, or localStorage is used.

Routes:

- `/access`: password-only session gate.
- `/`: starting location and optional preferences.
- `/explore`: exactly one route, editable origin/destination, WALK/TRANSIT toggle.
- `/explore/recommendations`: up to three always-expanded cards.
- `/map`: retained legacy tree browser with a single-route compatibility adapter.

In fixture mode only, mock areas are geographically relative to the selected/nearest covered precinct;
straight-line distances use the actual resolved origin. Sample route geometry,
tree counts, genus mix, and environmental metrics are illustrative, not Google
directions. All mock screens disclose this. The sample search recognises the
five precincts plus Flinders Street, Kensington Station, and Geelong Station.
Browser geolocation is real and has permission/error handling.

Desktop recommendations have three columns. Below 760px, all three remain fully
expanded in one column with an explicit area count. The route map and panel stack
on mobile; controls remain touch-sized. No separate Area Details page exists.

## Proposed backend handoff (not yet implemented)

Keep `VITE_USE_MOCK_DATA=false` for normal development. The live adapter supports
the CURRENT backend as well as the proposed enriched responses below; missing new
fields do not prevent real maps/routes from working. There is no silent fixture
fallback if a real request fails. Set `VITE_MOCK_ACCESS=false` once the real access
verification endpoint is deployed.

Current-backend compatibility:

- Real zones retain their IDs, bounds, centres and counts. Missing street names
  fall back to the precinct. Real trees provide the genus breakdown and markers.
- Tree density provides a provisional canopy proxy. Shade/noise use park-side
  share only when all trees for a zone are present in the bounded response;
  incomplete zone samples and unimplemented allergy scores remain unknown.
- Existing walking alternatives retain their exact Google polylines, distance
  and time. The adapter selects ONE using available tree counts/time and labels
  full preference scoring as pending. It never substitutes a schematic path.
- The old backend ignores `travelMode`. A WALK response is never shown as TRANSIT;
  until real transit is supported, the UI offers an external Google Maps link.
- Fixture session locations use a separate storage key from live locations.

1. `POST /api/access/verify`, request `{ "password": "..." }`, response
   `{ "token": "<signed token>", "expiresIn": 3600 }`. Wrong password: 401/403.
   Store the password and signing key only on the backend. The browser keeps the
   token in sessionStorage, attaches it as Bearer auth, and clears access on a 401.
   The backend must enforce token validation on protected APIs; a router guard
   alone is not API security. Short token lifetime is supported; expiry re-prompts.
2. Existing `/api/precincts`, `/api/places/autocomplete`, and `/api/places/{id}`
   retain their current shape. Suggestions start at two characters and are debounced.
3. `/api/zones?precinct=...&limit=500`: retain existing zone fields and add
   `nearestStreet: string | null`, `metrics`, `genera`, and optional `dataNotes`
   according to `src/types/personalisation.ts`. Metrics are normalised scores,
   **not measured canopy coverage or percentiles**. Missing street names fall back
   to precinct names. No invented street, water, or official park names are used.
   Allergy data may be null and must then be marked unknown, not matched.
4. `POST /api/routes` receives:

   ```json
   {
     "origin": { "lat": -37.7934, "lng": 144.9305 },
     "destination": { "lat": -37.7894, "lng": 144.9345 },
     "precinctId": "kensington",
     "travelMode": "WALK",
     "preferences": {
       "canopy": 90,
       "shade": 85,
       "noise": "quiet",
       "allergy": "lower",
       "walkingTime": 15
     }
   }
   ```

   Respond with one `PersonalisedRoute` (or a one-item array). Include time,
   distance, encodedPolyline, metrics, match, candidateCount, and optional message.
   Match/explanation data must come from the same scoring as selection. TRANSIT
   must replace the entire WALK result and have no environmental scoring claims.
   The adapter accepts the current two-route response and selects one, while
   explicitly stating that full personalised scoring is pending.

## Prototype rules requiring team confirmation

- Coverage notice: more than 5 km from every precinct with available zones.
- Walking-time tolerance: 2 minutes. `20+ min` is open-ended.
- Mock environmental score: mean of only selected dimensions. Sliders use
  closeness to the requested level; noise uses park share (or inverse for lively).
  Lower-allergy/avoid thresholds are illustrative; no real allergy taxonomy has
  been implemented. Backend weighting and the taxonomy still require agreement.
  Match badges use the same High/Medium/Low and shade categories as overview
  labels: partial shade cannot be labelled a match for "Cooler & shaded".
- Time is a constraint before score ranking. If no route qualifies, return one
  best available route with an explicit time-budget message.
- Park-side tree share is a shade/noise proxy, not a temperature/noise measurement.
- Recommendations show straight-line distance from the real origin, with walk
  estimates at 4.8 km/h. Route stats instead use the route response.

## Remaining content and release checks

- Supply the **verbatim canopy and shade info-panel bodies and Sources lines**
  from the canonical Epic 3 document. The supplied attachment omitted them;
  `PreferenceInfo.vue` deliberately shows pending copy rather than invented text.
- Implement/deploy real access verification, Google alternative scoring, transport,
  and enriched zone responses before treating backend ACs as complete.
- Enrichment scripts/schema mentioned in the handoff are not in this branch's
  base; coordinate with the backend branch before database changes.
- Do not add the old Basic Auth middleware to this branch unless a deliberate
  additional deployment gate is wanted; otherwise visitors get two prompts.
- Navigation opens external Google Maps with the exact origin/destination and
  selected mode. Google may choose a different route. No live turn-by-turn
  navigation or custom pollen-avoidance detour is claimed.

## Verification

`npm test` checks legacy live API compatibility, matching, budget tolerance, real-origin ranking, session access,
state restoration, stale-response rejection, and WALK/TRANSIT cache behaviour.
`npm run test:e2e` runs Chrome on desktop and a 390px mobile viewport, covering
the access gate, input validation, full journey, refresh, and coverage notices.
It uses installed Google Chrome, an isolated Vite server on port 5178, and mock
data. Screenshots/traces are written to ignored `test-results/`.
`npm run lint`, `npm run format:check`, and `npm run build` are also required.

Suggested commit boundaries: (1) state and mock/API adapters; (2) access and
responsive screens; (3) browser verification and integration notes.
