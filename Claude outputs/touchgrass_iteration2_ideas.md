# TouchGrass — Iteration 2 ideas, checked against the actual repo

I went through the frontend and backend code (not just the screenshots) to see what's really there before judging any of this. Short version: the reminder idea is workable but described a bit more finished than the codebase currently is, and there are two features that need zero new data collection because you're already gathering the inputs and just not using them yet. Details below.

## 1. Checking the reminder/nudge idea against the code

| Claim in the pitch | What the repo actually shows |
|---|---|
| "Your tech stack already has Firebase in it" | True, but only for Hosting. `firebase.json` deploys the built frontend as a static site. There's no `firebase` package in `frontend/package.json`, no service worker file, and no Firebase Admin SDK anywhere in the backend. Cloud Messaging would be new work on top of an existing project, not a switch you flip. |
| "No accounts and no login" | Confirmed. `backend/app` has no auth module, no user table, nothing in `schema.sql` about people, only `zones`, `trees`, `species`. The device-token approach is the right call given that. |
| "Store last visit timestamp against the token" | There's currently no concept of a "visit" anywhere in the app. The flow only plans routes (`POST /api/routes` returns a fastest and a green option); nothing logs that someone arrived, and there's no mood-check screen in `onboarding.ts` or any view file. Step 6 is a sketch, not code yet. |
| "The plumbing isn't the hard part" | Mostly right, but three things need building that the write-up glosses over: a `device_tokens` table (token, last_visit_at), a `POST /visits` endpoint the mood-check screen calls, and a scheduler. FastAPI has no built-in cron, so "3 days later, check and fire" needs Cloud Scheduler hitting a Cloud Run endpoint, or a scheduled Cloud Function. Worth its own card on the board so it doesn't get missed during estimation. |

Net read: feasible, and the reasoning about identity (device token, not accounts) is sound and fits how the app is built. Just budget for the visit-logging endpoint and the scheduler as real tasks, not as things that come free with "Firebase's already there."

## 2. Two features that cost you almost nothing, because you're collecting the data and throwing it away

This is the part worth raising with your team first, because it's smaller than either the reminder feature or the AI-text idea, and it fixes a gap between what onboarding promises and what the map actually does.

**Allergy avoidance isn't wired up yet.** `onboarding.ts` collects `hasAllergies` in its own step, but `discovery.ts` never reads it, and `/api/zones` doesn't accept it as a parameter. Someone who says "yes, I get hay fever" currently gets routed through zones exactly as if they'd said no. The data to fix this already exists: `family_display_category` on trees and the `dominantGenus` field on zones. A backend filter that down-ranks or excludes zones dominated by the classic high-pollen genera (Eucalyptus, Casuarina/Allocasuarina, Platanus, which are already in your `TreeGenus` type) closes this without collecting anything new.

**Noise tolerance has no data to answer it with yet, but you're closer than it looks.** `noiseTolerance` is captured on a 1 to 7 scale and also goes nowhere. Unlike allergies, there's genuinely no "how quiet is this zone" field in `schema.sql`. But `TreeRecord.locatedIn` (`'Park' | 'Street'`) already exists per tree, which is a reasonable proxy: street trees sit next to traffic, park trees generally don't. A zone-level "share of park vs street trees" computed from data you already have would let a low noise-tolerance answer favour park-heavy zones, without a new data source.

Both of these are backend filter logic plus a couple of new query params, not new infrastructure, and they make the onboarding questions your team already designed actually mean something.

## 3. Extending the green-path idea you've already built

Your route scoring in `routes.py` already does something clever: it decodes both Google Route candidates and counts trees within 100m of each, picking the greenest as an alternative to the fastest. That's a real point of differentiation worth building on rather than past.

**Time-budget-aware destination picking.** `timeBudget` (5 / 15 / 30+ minutes) is captured in onboarding and, like the other two, isn't used downstream. A cheap win: instead of the user always searching for a destination, use the zones already loaded for their precinct and suggest the nearest zone whose round-trip walking time roughly matches their budget (a rough distance-to-minutes conversion using the same haversine helper already in `discovery.ts` gets you 80% of the way there without calling the Routes API for every candidate).

**"Why this route" explanation, no AI needed.** You already compute `treeCount` for each route option. Surfacing that as a one-line comparison ("Green Path passes 340 more trees for 4 extra minutes") on `GreenPlaceCard.vue` turns a number you're already computing into the kind of transparency that's easy to demo and costs a template string, not a feature.

**Precinct-level "canopy equity" framing.** `map_data.py`'s own comments show the team already found that Brunswick, Fishermans Bend, Richmond, and two others have almost no zones despite having trees, ie the flat-out low-canopy suburbs the project is about. A simple "your suburb has the least canopy in this dataset" comparison view, built entirely from `/api/precincts` data you already serve, speaks directly to the project's problem statement (low-canopy Melbourne suburbs) in a way the current per-precinct search doesn't foreground.

## 4. Where the AI-personalised message idea fits

The single LLM-call version in your write-up (one backend call that drafts reminder text, no chat UI) is the right scope call for the reasons you gave: it rides on top of the reminder feature once that plumbing exists, and a real back-and-forth chatbot is a separate, much bigger piece of session/state handling you don't need for this problem. I'd sequence it after the reminder MVP and after the allergy/noise wiring above, since the personalised message is more convincing once "favourite zone" and mood are actually being tracked, rather than being your very next PR.

## Suggested order for iteration 2

1. Wire up allergy filtering (data exists, smallest change, fixes a real gap)
2. Wire up noise tolerance via the park/street proxy (data exists, small change)
3. Route explanation line using existing tree-count scoring (no new data, no new endpoint)
4. Visit logging endpoint + mood-check screen (net new, needed before reminders can work at all)
5. Device-token reminder via FCM, including the Cloud Scheduler piece
6. AI-personalised reminder text as a stretch goal on top of 5

Worth naming 4 and 5 explicitly as two separate cards when you scope this for your mentor, since "the reminder feature" is really "build the thing that logs a visit" plus "build the thing that reminds you," and the write-up bundles them into one MVP.

## 5. What the research actually says about tree canopy and stress, and what it implies for the app

This is worth having in your back pocket for your mentor or a report, since it turns "trees are calming" from a vibe into a citable justification for building a *tree canopy* app rather than a generic parks app.

**Trees specifically, not green space generally, is the finding that matters most for you.** A 2019 study of about 46,000 adults across Sydney, Newcastle and Wollongong (Astell-Burt & Feng, published in *JAMA Network Open*) found adults living somewhere with 30% or more tree canopy within 1.6km of home had 31% lower odds of psychological distress and 33% lower odds of poor general health over six years, and that open grass alone showed no such benefit. That's the strongest possible evidence for TouchGrass's actual premise: it's the canopy, not just "outdoor space," that your existing `density` tiers (High/Medium/Low, based on tree count per zone) should be understood as a proxy for. Worth a line of copy on a zone card ("high canopy zones like this are linked to lower psychological distress in Australian research") rather than a new feature, since you already compute the tier.

**There's a real dose, and your current time-budget options don't quite match it.** A 2019 University of Michigan study (Hunter, Gillespie & Chen, *Frontiers in Psychology*) tracked cortisol across repeated nature breaks and found the biggest drop happens in the 20 to 30 minute range, with benefits continuing after that but at a much slower rate. Your onboarding's `TimeBudget` currently offers 5 / 15 / 30+ minutes. That's fine as a UX constraint (a stressed student between classes genuinely might only have 5), but it's worth being honest in the copy about which option gets the research-backed effect, something like the 30+ option's subtitle noting "this is the range shown to lower stress hormones most" rather than implying all three options are equivalent. Free, and it's the kind of detail a marker who's read the same literature will notice either way.

**Walking to somewhere green measurably beats either walking or greenery alone.** The "green exercise" literature (Barton & Pretty's meta-analysis is the usual citation, with more recent systematic reviews confirming it) consistently finds that combining physical activity with a natural setting produces a bigger mood and stress effect than the same exercise indoors or the same green space while sitting still. This directly validates the core mechanic you've already built, the walking route that maximises tree exposure, rather than a "find a bench" feature. It's a reason to lean further into route framing (see the "why this route" idea above) rather than add a static "nearby zone" browsing mode as a competing primary flow.

**Attention Restoration Theory gives you a name for the "avoid the busy street" idea from before.** Kaplan's ART names four ingredients for a restorative environment: being away (psychological distance from routine demands), extent (feels like a coherent world, not a strip of grass between buildings), soft fascination (interest without effort, like leaves moving), and compatibility (fits what you're there to do). "Being away" specifically is the theoretical backing for the park-vs-street proxy from the noise question I flagged earlier, a street-tree-heavy route running alongside traffic scores lower on "being away" than a park interior even with the same tree count, which is a genuinely different thing from what `treeCount` alone measures. If you want one sentence in a report justifying that feature, ART is it.

**Birdsong and nature sounds: evidence is genuinely mixed, so I would not build an audio feature around it.** Some studies find birdsong reduces anxiety and paranoia; at least one urban field study found no measurable effect on stress recovery specifically in cities (traffic noise likely swamps it). Given your team already trimmed scope elsewhere (Epic 5/6), a soundscape feature would be spending build time on the least certain part of the literature. Worth naming this explicitly as "considered, not pursued, evidence too mixed" if it comes up with your mentor.

**You're already building a recognised category, not just an app.** "Green social prescribing," clinicians formally recommending nature-based activity for mental health, is an active NHS program in the UK and a growing area of public health practice. Framing TouchGrass as a self-directed, no-friction version of that (no GP referral, no account, just "here's your 10-minute dose") is a legitimate positioning line for your problem statement, not just marketing language.

### What this changes in the idea list above

Nothing here adds new build scope beyond what's already suggested. It mostly reprioritises and strengthens the case for two things already on the list: the route-explanation copy (now backed by canopy-threshold and dose numbers you can actually cite) and the park-vs-street "being away" proxy (now grounded in ART rather than just being a reasonable-sounding proxy). The one new, purely-copy idea is the time-budget subtitle above, and the one thing I'd actively deprioritise is any birdsong or soundscape feature, since the evidence doesn't support the build cost.

Sources:
- [Association of Urban Green Space With Mental Health and General Health Among Adults in Australia (JAMA Network Open)](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2739050)
- [Increasing tree cover may be like a "superfood" for community mental health (The Conversation)](https://theconversation.com/increasing-tree-cover-may-be-like-a-superfood-for-community-mental-health-119930)
- [Mounting evidence says trees, but not grass, improve mental health (ScienceAlert)](https://www.sciencealert.com/increasing-urban-tree-cover-gives-community-mental-health-a-boost-says-new-study)
- [Stressed? Take a 20-minute "nature pill" (ScienceDaily, on Hunter et al., Frontiers in Psychology 2019)](https://www.sciencedaily.com/releases/2019/04/190404074915.htm)
- [A 20-minute nature break relieves stress (Harvard Health)](https://health.harvard.edu/mind-and-mood/a-20-minute-nature-break-relieves-stress)
- [Minimum Time Dose in Nature to Positively Impact Mental Health of College-Aged Students (scoping review, PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6970969/)
- [Attention restoration theory (Wikipedia overview)](https://en.wikipedia.org/wiki/Attention_restoration_theory)
- [What is Kaplan's Attention Restoration Theory? (Positive Psychology)](https://positivepsychology.com/attention-restoration-theory/)
- [Regular Doses of Nature: The Efficacy of Green Exercise Interventions for Mental Wellbeing (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7084199/)
- [Effects of Outdoor Walking on Positive and Negative Affect: Nature Contact Makes a Big Difference (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9206539/)
- [Birdsongs alleviate anxiety and paranoia in healthy participants (Scientific Reports)](https://www.nature.com/articles/s41598-022-20841-0)
- [Sounds of Nature in the City: No Evidence of Bird Song Improving Stress Recovery (PubMed)](https://pubmed.ncbi.nlm.nih.gov/30999690/)
- [The effect of exposure to natural sounds on stress reduction: a systematic review and meta-analysis](https://www.tandfonline.com/doi/full/10.1080/10253890.2024.2402519)
- [NHS England: Green social prescribing](https://www.england.nhs.uk/personalisedcare/social-prescribing/green-social-prescribing/)
