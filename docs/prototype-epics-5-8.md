# Epics 5–8 prototype completion

The current frontend keeps the prototype's six Sprout looks, 15-point unlock
price, 5 points per finished walk, and device-only rewards. Existing v1 rewards
saves retain their points and visits; Classic is always available. A purchase
is charged once and equips the new look. The wardrobe handles selecting and
wearing a skin; there is no skin selector in the topbar. The walk summary uses
a compact wardrobe and green points card beside the enlarged map.

The rewards page shows visits for the current calendar week and the last eight
check-ins, including skipped ratings. The walk summary keeps just points,
skins and nearby areas. Nearby recommendations
after a completed walk use the arrival location rather than the original start.
Without a usable GPS fix, the reached area's center is the next starting point.
Recommendation picks use `POST /api/sprout/route` with `destinationZoneId`,
keeping the chosen citywide area instead of calling the old CBD-only route
endpoint. A failed request keeps the current map and rewards visible for retry.
Restart the local backend after updating to load this optional request field.

The completion card shows the award for this walk beside the available balance,
which already includes purchases. The same area awards once per local calendar
day, including after a reload; another area or the next day can award again.
Switching owned looks is free. All reward leaf icons use SVG rather than font glyphs.

Local testing can set `POSTS_PER_DEVICE_PER_HOUR=0` in `backend/.env` to disable
posting limits; the default remains 10 for deployments without an override.
New-pin creation recovers a lost device credential once, using a fresh anonymous
identity. Photo and message ownership failures are not retried under another
identity. Browser-storage failures retain the current identity in memory.

The Walk screens share a calm cream/green design, 44px minimum touch targets,
consistent cards and clear primary/secondary actions. Desktop keeps a viewport-height
map beside an independently scrolling panel. On phones, arrival and subsequent
steps prioritise the task; Show map reveals the map when wanted. Step changes
reset the panel scroll and move keyboard focus to its labelled region.
GPS coordinates, report handoff actions and message history expand on request.
The full photo/report/check-in flow is exercised on desktop and a 320px phone
in `frontend/e2e/walk-ui.spec.ts`; test photos and API responses are fixtures.

The visual palette follows the supplied Epics 5–8 prototype: warm `#f5f2e8`,
forest green `#1f5a2c`, Fraunces headings, outlined pill buttons and Sprout's
white speech bubble. The simplified task layout and phone behaviour remain.

Damage reports are saved before sharing. The visitor can share a description
file plus the actual metadata-stripped photo on browsers that support file
sharing, download a self-contained report, or save the photo for the City of
Melbourne tree maintenance page. No report is automatically sent to the council.
Cancelling sharing does not discard the saved report or claim successful delivery.

The public care response now includes `kind` and returns both ordinary messages
and damage reports **only after admin approval**. Photos remain hidden until
their separate approval. The existing `X-Care-Admin` review endpoints still apply;
an operator must configure `CARE_ADMIN_TOKEN` and review posts. There is no new
public admin screen or automatic moderation.

Deploy both frontend and backend to publish these changes. No database migration
is needed for the additive care response field. The Cloud Run service is
`touchgrass-api` in `australia-southeast1`:

```powershell
gcloud run deploy touchgrass-api --source ./backend --region australia-southeast1
```

Existing care databases must also have migrations 004 and 005 (device
credentials and owner columns). Missing tables or columns make pin saves fail.
From `backend`, `python -m app.migrate_care_devices` applies those additive
changes in one transaction, preserves existing records, and can be repeated.
The configured Supabase database was repaired with this command on 9 October
2026. `Pin it anyway` reuses the GPS fix the visitor just confirmed, rather
than starting a second location lookup. Raw API paths are no longer shown as
pin-save errors.

Targeted browser checks run with `npx playwright test e2e/rewards.spec.ts` and
exercise desktop/mobile unlocks, insufficient points, persistence, and overflow.
Unit tests cover old saves, repeated purchases, report attachments, escaped
visitor text, and planning the next walk from the arrived area. Backend care
tests verify that reports and photos stay hidden until reviewed.
