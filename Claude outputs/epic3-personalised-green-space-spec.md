# Epic 3 — Personalised Green Space (Iteration 2 spec for frontend + backend)

Written after reading the current repo (`HomeView.vue`, `discovery.ts`, `discovery.service.ts`, `routes.py`, `map_data.py`, `schema.sql`), so every claim below about what's feasible is checked against what's actually in the database and the API contract, not assumed.

**Important context for the team:** the current `HomeView.vue` on `main` is still the old five-step onboarding wizard (splash → time → noise → allergies → location, one question per screen). The single-page "Personalise Your Green Space" layout in the screenshots doesn't exist in code yet — this doc is the spec for building it, replacing the wizard.

---

## 1. Rewritten user stories

### US 3.0 — App access gate (new, goes first)

> As a team member testing an unreleased build, I want to enter a shared password before the homepage loads, so that the app stays private during iteration 2 without building full user accounts.

**Feasibility check:** confirmed there is no auth of any kind in the repo — no user table in `schema.sql`, no auth module in `backend/app`, and the README lists "Authentication" under "Not decided yet." So this is net-new, and it should stay net-new in the *simplest* form: one shared password, not per-person accounts, so it doesn't collide with US 3.1's AC11 (no sign-in required) or invent scope Epic 3 doesn't need yet.

Acceptance Criteria:
1. Given the user opens the TouchGrass link, when the app loads, then a single password field is shown before any homepage content, with no username field and no "create account" option.
2. Given the user enters the correct shared password, when they submit it, then they are taken directly to the Home page and the password is not asked again for the rest of that browser session.
3. Given the user enters an incorrect password, when they submit it, then an inline error is shown and the homepage is not loaded.
4. Given the user has already unlocked the app in this browser, when they refresh or navigate between TouchGrass pages, then they are not asked for the password again (satisfies existing AC11 — this must not turn into a login).
5. Given the browser session ends (tab/browser closed) or local storage is cleared, when the user returns, then the password prompt is shown again.

**Direction for backend:** one endpoint, `POST /api/access/verify { password }`, compares against a single value in an environment variable (never hard-coded, never returned to the frontend), returns a short-lived signed token on success. No new database table needed.

**Direction for frontend:** store the token in `sessionStorage` (not `localStorage` — that's what gives you "asked again when the browser session ends" in AC5), gate the router with a `beforeEach` check rather than wrapping every view.

---

### US 3.1 — Set environmental preferences on the homepage

> As a city worker stressed and wanting to go somewhere quieter, I want to select the environmental conditions that matter to me at that moment, so that my experience can better suit my current needs.

This is your original story — it was already written in the right format, so it's reproduced as-is below with the ACs unchanged, since they're solid and grounded in what the screenshots show.

Acceptance Criteria:
1. Given the user opens the Home page, when the preference section is loaded, then the following five preference categories are visible without navigating to another page: Tree Canopy, Shade / Thermal Comfort, Noise Level, Allergy Preference, Preferred Walking Time.
2. Given the Tree Canopy slider is visible, when the user moves the slider toward the dense-canopy end, then the preference summary displays "More tree canopy."
3. Given the Shade / Thermal Comfort slider is visible, when the user moves the slider toward the shaded end, then the preference summary displays "Cooler and shaded."
4. Given the Noise Level control is visible, when the user selects "Quieter surroundings," then that option is visually selected, the previous noise option is deselected, and the preference summary displays "Quieter surroundings."
5. Given the Allergy Preference control is visible, when the user selects "Prefer lower-allergy areas," then that option is visually selected, the previous allergy option is deselected, and the preference summary displays "Lower-allergy preference."
6. Given the Walking Time control is visible, when the user selects one option, then exactly one of 5 min / 10 min / 15 min / 20+ min / No preference is active.
7. Given the user selects 15 min, then the preference summary displays "Within 15 minutes."
8. Given the user has selected Tree Canopy, Noise Level and Walking Time, when they change only Noise Level, then the Noise Level summary updates while Tree Canopy and Walking Time remain unchanged.
9. Given the user leaves one or more categories as "No preference" or unselected, when they continue to the personalised flow, then no validation error is displayed.
10. Given the user has selected preferences, when they continue to the personalised recommendation or route flow, then the same selected preference values are displayed in that flow.
11. Refreshing or navigating between TouchGrass pages during the same session must not require the user to create an account or sign in.

---

### US 3.2 — Calculate and show the personalised route (new — answers your open question)

Yes, this needs its own story. Here's why: US 3.1 only covers *choosing* preferences — none of its ACs mention a route or a result appearing. Without a separate story, "what happens when the user is done choosing" has no acceptance criteria at all, and your backend/frontend devs have nothing to build against for the moment preferences turn into an actual green route. Given your scope note ("one route for the user, personalised"), this story is where that scope gets written down.

> As a city worker who has set my preferences, I want TouchGrass to calculate and show me one personalised green route based on those preferences, so that I don't have to manually compare zones myself while I'm stressed and short on time.

Acceptance Criteria:
1. Given the user has set preferences on the Home page (US 3.1) and provided or allowed a starting location, when they choose to continue, then the app calculates exactly one recommended route without asking the user to compare or choose between multiple options.
2. Given the calculation is in progress, when it takes more than a moment, then a loading state is shown rather than a blank screen.
3. Given a route is found, when the calculation finishes, then the user is taken to the route/map view and sees the route drawn, its walking time, and a short line stating which of their preferences it matches (e.g. "High tree canopy, quieter route").
4. Given the user's Walking Time preference is set (e.g. 15 min), when the route is calculated, then the recommended destination's round-trip walking time is within a reasonable tolerance of that budget rather than ignoring it.
5. Given the user's Allergy Preference is "Prefer lower-allergy areas," when zones are scored, then zones dominated by high-pollen genera are down-ranked or excluded from candidates.
6. Given no zone or route can be found that reasonably satisfies the selected preferences (e.g. an isolated precinct with too few zones), when the calculation finishes, then a clear message is shown instead of a broken or empty screen, and the user is offered the nearest available alternative.
7. Given the user goes back and changes a preference, when they recalculate, then a new route is generated reflecting the change, replacing the previous one rather than appending to it.

---

## 2. Data feasibility — what each slider can actually calculate from, today

Checked against `backend/app/routers/map_data.py`, `routes.py`, and `schema.sql`. Nothing below requires new data collection except where marked.

| Preference | Feasible now? | What it calculates from |
|---|---|---|
| **Tree Canopy** | Yes, fully | `zones.tree_count`. You already compute High/Medium/Low tiers off the 25th/75th percentiles (10 and 37 trees) in `map_data.py`. For a continuous slider rather than three buckets, convert `tree_count` to a percentile score (0–100) per zone within its precinct, and map the slider position to a minimum percentile threshold. No new data. |
| **Shade / Thermal Comfort** | Not with real thermal data — proxy only, see below | There is no temperature, shade, or canopy-cover-percentage field anywhere in `zones` or `trees`. This is the one slider that needs a decision from you (see section 3). |
| **Noise Level** | Yes, as a proxy | `trees.located_in` ('Park' vs 'Street') already exists per tree and isn't used anywhere yet. Compute the share of a zone's trees that are Park vs Street; a Park-heavy zone is a reasonable "quieter" proxy since street trees sit next to traffic. Not wired up in `map_data.py` currently — needs one new aggregate query. |
| **Allergy Preference** | Yes, fully | `trees.display_category` (the 9-genus classification already used for the species filter) lets you flag Eucalyptus, Casuarina/Allocasuarina, and Platanus — the classic high-pollen genera already in your `TreeGenus` type — and down-rank or exclude zones dominated by them. Not wired up yet, but the data exists. |
| **Preferred Walking Time** | Yes, fully | `distanceKm` is already computed (haversine, in both `discovery.service.ts` and `map_data.py`). Convert to minutes at an average walking pace (~80m/min is a standard planning figure) to filter candidate zones or score route options against the selected time budget. |

### On the Shade / Thermal Comfort slider specifically

I looked for a City of Melbourne (or Victorian Government) dataset you could overlay onto your existing 0.001° zone grid:

- **Tree Canopies 2021 (Urban Forest)** on the [Victorian Government open data directory](https://discover.data.vic.gov.au/dataset/tree-canopies-2021-urban-forest) — this is a *canopy cover polygon* dataset (actual leaf-area footprint, not just tree points), also mirrored on the [City of Melbourne Open Data Portal](https://data.melbourne.vic.gov.au/explore/dataset/tree-canopies-2021-urban-forest/). This is closer to a true canopy dataset than your current tree-count proxy, and worth a look for iteration 3, but swapping it in now means a new spatial-join pipeline (polygon-to-grid overlay) — likely too much for this iteration's timeline given you already dropped Epic 5/6 for scope reasons.
- **Metropolitan Melbourne Urban Heat Islands and Urban Vegetation 2018** — a [Victorian Government / RMIT research dataset](https://discover.data.vic.gov.au/dataset/metropolitan-melbourne-urban-heat-islands-and-urban-vegetation-2018) built from Landsat land-surface-temperature imagery. This is real thermal data at metro scale, but it's a raster (image-based) dataset, not a CSV — using it means reprojecting and spatially joining a raster onto your grid cells, which is a GIS pipeline task on its own, on top of everything else in your data science backlog.

**My recommendation:** don't block Epic 3 iteration 2 on either of those. Ship the slider now using a proxy built from data you already have — the same tree-density + park/street split used for Tree Canopy and Noise, since dense, park-heavy zones are also generally cooler and more shaded (this is a reasonable simplification, not a stretch — it's the same underlying mechanism ART and the canopy-mental-health literature describe). Label it honestly in any report or demo as a proxy, not measured temperature, and put the LST raster integration on the list for a later iteration if there's time. This keeps Shade/Thermal Comfort inside your existing pipeline instead of opening a new one under deadline.

---

## 3. Making the homepage feel less cluttered

Looking at the screenshots: five full-width controls (two sliders, three pill-button rows) all stacked vertically, plus a persistent summary panel beside them, all visible at once with no visual hierarchy between them. A few concrete changes, all buildable with what's already in the stack (Vue 3 + Element Plus, per `package.json`):

1. **Default to a "quick pick" and hide the sliders behind it.** Most users won't want to fine-tune five things while stressed. Show 3–4 mood chips up top ("Quiet & shaded," "Lots of trees," "Quick walk," "Custom") that set sensible preference defaults in one tap. Put the five detailed controls behind a "Fine-tune your preferences" expandable section (Element Plus's `el-collapse` does this natively) that's closed by default. This directly serves the "stressed city worker" persona in the story — one tap should get them moving.
2. **Merge the live summary into the controls instead of a separate column.** Right now the "Your Green Space Preference" panel repeats information already shown by each control's own selected state. Show the summary as small inline chips directly under each control, or as a single line of text above the "Continue" button ("Quieter, more tree canopy, within 15 min") instead of a whole second panel — this removes one of the two vertical blocks the eye has to scan.
3. **Group by relatedness, not by list order.** Tree Canopy and Shade/Thermal Comfort are both "how green/cool" — pair them under one small heading. Noise and Allergy are both "what to avoid" — pair those. Walking Time stands alone as the constraint. Three groups read faster than five loose rows.
4. **Cut the "Based on X data" badges from the default view.** They're useful context but add a second line of text to every control, doubling the vertical space each one takes. Move them into a tooltip/info icon instead of always-on text.
5. **Sliders only where the value is genuinely continuous.** Tree Canopy and Shade/Thermal Comfort are fine as sliders since they map to a percentile score. But consider whether Walking Time (already discrete: 5/10/15/20+/No preference) needs a slider *and* a pill row, or just the pills — matching the control type to the underlying data type (continuous vs. categorical) removes visual redundancy.

None of this needs new components beyond what Element Plus already ships (`el-collapse`, `el-tag` for chips, `el-tooltip`), so it's a layout and information-architecture change, not a new dependency.

---

## 4. Summary for the team

- **Backend:** one new lightweight `/api/access/verify` endpoint for US 3.0 (no new table). For US 3.2, extend `/api/zones` (or add a `/api/recommend` endpoint) to accept the five preference values as query params and return one ranked zone/route instead of a flat list — reuse the percentile/proxy logic in section 2, all of it works off columns that already exist except the two new aggregate queries for Park/Street ratio and high-pollen genus flags.
- **Frontend:** rebuild `HomeView.vue` as the single-page layout from the screenshots (replacing the current step wizard), wire the five controls to a new preferences store (the existing `onboarding.ts` store already captures three of these fields — `timeBudget`, `noiseTolerance`, `hasAllergies` — extend rather than replace it), and add the password gate as a router guard ahead of everything else.
- **Open question worth raising with your mentor/team, not decided here:** whether Shade/Thermal Comfort ships as the tree-density proxy for iteration 2, or whether the team wants to spend a card on integrating the Tree Canopies 2021 polygon dataset instead. Both are legitimate; the proxy is the lower-risk choice given your timeline.
