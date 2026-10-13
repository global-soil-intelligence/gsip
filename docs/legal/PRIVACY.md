# GSIP privacy notice

> **Draft — requires counsel review.** Not in force. Lawful bases, retention periods and transfer
> mechanisms marked **[DECISION]** need counsel's confirmation.

## Who is responsible

**Viridis LLC**, [registered address — DECISION], stewards GSIP and is the controller of the
personal data described here. Privacy contact: [address — DECISION]. **[EU/UK representative, if
required — DECISION.]**

## What we collect and why

| Data                                                                                                                                                   | Why                                                                                                                                                                                                                                                             | Basis **[DECISION]**                |
| ------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| Account: an anonymous account identifier, or your e-mail address if you add one                                                                        | To let you contribute and manage your data from your devices                                                                                                                                                                                                    | Contract                            |
| Observation: precise position (device GPS with its accuracy, or a pin you place), capture time, coarse device model, your one-tap answers              | To place, check and use your observation scientifically                                                                                                                                                                                                         | Contract                            |
| Photographs: the originals until they are checked, then copies with all embedded metadata removed                                                      | Soil estimates, quality checks and the open dataset                                                                                                                                                                                                             | Contract                            |
| Attribution name and grant: the name you chose (or the default pseudonym), the terms version and when you accepted it                                  | To credit your photographs and keep a record of the licences you granted                                                                                                                                                                                        | Contract; consent for a typed name  |
| Derived data: hexagonal map cells, quality checks, soil-map, elevation and rainfall values looked up for your area                                     | Quality checks and estimates                                                                                                                                                                                                                                    | Legitimate interests (data quality) |
| Rights requests: what you asked, when, and when it was done                                                                                            | To carry out and evidence withdrawals and deletions                                                                                                                                                                                                             | Legal obligation                    |
| Requests to GSIP's public data interface, from people or AI agents: the requester's IP address, and the map cell asked about (resolution 8 or coarser) | To answer them, share capacity fairly and limit abuse. GSIP's own code holds the address only in memory while it runs. Supabase's request logs record each request's address and requested web address, which contains the cell when it is asked in the address | Legitimate interests (security)     |
| Technical and audit logs kept by our hosting providers (IP address, browser, requested web address, sign-in events)                                    | Security and abuse prevention                                                                                                                                                                                                                                   | Legitimate interests (security)     |

We do not sell personal data, show advertising, or build profiles of contributors.

### The phone app

The GSIP phone app collects the same data as the website. It asks for the camera, and for your
location while you use the app, only when you first use each; it never uses location in the
background. On Android the position comes from your phone's own location services (which on
many phones include Google Play services, as your phone's settings decide), and GSIP receives
only the result. Photos you take for an observation, and observations waiting to sync, stay in
the app's storage on your phone until they sync or you discard them; your phone's own backups
may include that storage **[DECISION]**.

## What becomes public

The open dataset (nightly, under ODbL 1.0 and CC BY-SA 4.0) and the public map contain, for each
released observation: a hexagonal area that at least **three different contributors** share
(resolution 8, 6 or 4, about 0.7 km², 36 km² or 1,770 km²), the capture **date** (never the time),
your one-tap answers, quality checks (location-based checks as pass or fail only), and the
sanitized photographs credited to the default pseudonym or to a typed name we have approved. If a
typed name has not been approved, the observation is released without its photographs and the name
appears nowhere.

Never public: your precise position, GPS accuracy, finer map cells, account identifiers, e-mail
address, device model, original photographs or any photo metadata, and soil-map values looked up
for your position. An observation that cannot yet meet the three-contributor rule is held back.
The public map's counts are recomputed with each nightly release. GSIP's public data interface
for people and AI agents serves the same published cells and release records, and nothing else.

Photographs can show more than soil: please follow the rules on what to photograph.

## Processors and external services

Our processors (Supabase, which stores everything, and GitHub, whose runners execute GSIP's
workers) handle your precise position on our behalf. The data sources we query (ISRIC, USDA and
Open-Meteo) never receive it: soil-map, elevation and rainfall lookups send only the centre of your
observation's resolution-9 cell (about 0.1 km²).

| Service                                | Role                                                                                                                                                     | What it receives                                                                             | Hosts                                                             |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Supabase                               | Database, sign-in, private photo storage, server functions                                                                                               | Everything in "What we collect", including precise positions and e-mail addresses            | `*.supabase.co`                                                   |
| Sign-in e-mail delivery **[DECISION]** | Sends sign-in links, configured in Supabase Auth                                                                                                         | Your e-mail address                                                                          | (the provider configured in Supabase Auth)                        |
| GitHub                                 | Hosts the website (GitHub Pages) and runs GSIP's scheduled workers (Actions)                                                                             | Visitors' IP addresses and browser details; workers process private data inside their runs   | `github.com`, `*.github.io`                                       |
| Hugging Face                           | Hosts the open dataset                                                                                                                                   | The public release only                                                                      | `huggingface.co`                                                  |
| ISRIC – World Soil Information         | SoilGrids soil maps for estimates and map layers                                                                                                         | Cell centres (server); map visitors' browsers load map images directly (IP address)          | `rest.isric.org`, `maps.isric.org`, `files.isric.org`             |
| USDA NRCS Soil Data Access             | US soil survey values                                                                                                                                    | Cell centres within the United States (server)                                               | `sdmdataaccess.sc.egov.usda.gov`                                  |
| Open-Meteo                             | Elevation, and rainfall in the three days before capture                                                                                                 | Cell centres and the capture date window (server)                                            | `api.open-meteo.com`, `archive-api.open-meteo.com`                |
| Map tile host: GitHub Pages            | Serves GSIP's SoilGrids-derived prior map tiles from the same origin as the website, once the publication checks pass and `VITE_PRIOR_TILES_BASE` is set | Visitors' IP addresses and browser details; no contributor observations or precise positions | `*.github.io`, `globalsoilintelligence.com` after the DNS cutover |
| Squarespace                            | Serves the `globalsoilintelligence.com` holding page until the domain moves to GitHub Pages **[DECISION: date]**                                         | Visitors' IP addresses and browser details                                                   | `globalsoilintelligence.com`                                      |

The product owner approved GitHub Pages as the prior-tile host on 2026-10-11, conditional
on the [tile-host publication checks](../PRIOR_TILE_HOSTING.md). The archives contain only
SoilGrids-derived values, not contributor observations or their private locations. Until those
checks pass, the map continues to load ISRIC's WMS images directly; those requests disclose the
visitor's IP address to ISRIC, as listed above. This hosting decision does not put this draft
notice in force or authorize publication.

**International transfers [DECISION]:** these providers may process data outside your country,
including in the United States. [Mechanism for each provider, and the Supabase project region.]

## How long we keep it **[DECISION]**

| Data                                    | Kept                                                                                                                                                                                                         |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Original uploads                        | Until checked, and never beyond about a day: an hourly job deletes any original older than 24 hours                                                                                                          |
| Account and observations                | Until you withdraw them or delete your account; then deleted within 30 days (normally within the hour)                                                                                                       |
| Observations that failed quality checks | Kept privately, flagged, to improve quality checks; deleted with your account **[period — DECISION]**                                                                                                        |
| Grant and withdrawal records            | The grant's identifier, terms version, date and licences, kept as the record of what was licensed; attribution names are replaced with the default pseudonym when an account is deleted                      |
| Your contributor record                 | After account deletion, a random identifier with no link to your sign-in, e-mail or name, kept so the grant and withdrawal records stay consistent                                                           |
| Rights-request records                  | What was requested and when it was done, without content **[period — DECISION]**                                                                                                                             |
| Cached map lookups                      | Soil-map and elevation answers for an area of about 0.1 km², with no link to any person, for up to a year                                                                                                    |
| Hosting, audit logs and backups         | As each provider keeps them: Supabase keeps database backups, its sign-in audit log and its request logs for their own retention periods **[period — DECISION]**; GSIP's own worker logs contain counts only |

## Your rights

You can withdraw your contributions or delete your account at any time from **Your data** in the
capture app; see [Withdrawal and deletion](WITHDRAWAL_AND_DELETION.md). You can also ask us for a
copy of your data, to correct it, or to stop a use based on legitimate interests, by writing to the
privacy contact; we answer within one month. You may complain to your data-protection authority.

If you contributed without an e-mail address, adding one in the app keeps the same account, so you
can manage your contributions from another device. Signing in to a different e-mail account leaves
the anonymous contributions with the anonymous account; withdraw them first if you want them gone.

Copies of earlier open releases that others have already downloaded cannot be recalled; the open
licences remain valid for them.

## Children

See [Classroom and minors](CLASSROOM_AND_MINORS.md).

## Security

Private data sits behind database row-level security in private storage; only GSIP's server-side
workers handle it. Original uploads are kept in a private quarantine until they are checked; the
copy we keep has all metadata removed, and it is checked again before release.

## Changes

We publish changes to this notice with a new version date. Material changes that affect existing
observations are announced in the app before they apply.
