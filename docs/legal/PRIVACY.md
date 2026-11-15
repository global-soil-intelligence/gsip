# GSIP privacy notice

> **Draft — awaiting product-owner adoption.** Not in force. Proposed terms version on adoption: `2026-11-14-v1`.
> Proposed choices for the invited pilot are filled in below (WP-COLLECT-5, WP-COLLECT-5B). They are proposals prepared by an agent, not legal advice, and take effect only if the product owner adopts them.

## Who is responsible

**Viridis LLC** stewards GSIP. Proposed for the invited pilot: the product owner's Montana company,
referred to here by the working name "Viridis North" (its registered name is to be confirmed before
adoption), is the controller of the personal data described here and is "we" in this notice.
How the steward and this company relate is to be settled before adoption; see the [legal README](README.md). Privacy contact: **[owner input: privacy and legal contact mailbox, and postal address]**. The invited pilot is offered only to adults who live in the United
States, so no representative in the European Union or the United Kingdom is appointed. That must
be decided again before GSIP is offered to people there.

## The invited pilot

In the invited pilot your account is created by invitation with the e-mail address you gave the
organizer. There are no anonymous accounts, so every mention of an anonymous account below
describes the later public service. Nothing you submit in the pilot is published. The organizer
confirms that each participant is an adult who lives in the United States; the app asks you to
confirm your age and does not ask where you live.

## What we collect and why

| Data                                                                                                                                                   | Why                                                                                                                                                                                                                                                             | Basis                               |
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
the app's storage on your phone until they sync or you discard them.

Optional native sync reminders ask for notification permission only after you choose to enable
them. They are scheduled on your device without a push service or new location lookup. The OS
receives one opaque local ID and fixed generic text, never your queue contents, photos, names,
coordinates or account/session identifiers. Private opt-in/account binding and bounded
cycle/cleanup state remain in the app's local storage. Turning reminders off does not delete
unsynced work. Sign-out, rights requests, successful sync, an empty queue and observed capture
closure cancel the owned reminder; uncertain device cleanup stays pending for retry on reopening.
An offline app cannot observe remote closure instantly or retract an already displayed OS alert.

Our policy excludes the app's private queue, photo drafts and account session from cloud
backups. Android builds exclude these stores from cloud backup; on Android 12 or newer,
direct device-to-device transfer may retain them without sending them to cloud storage.
Older Android versions exclude both backup and transfer. Physical-device backup/restore and
transfer checks are required before release. Backups a provider already holds cannot be
erased retroactively by updating the app.

**iOS implementation is blocked/unverified:** the app's current WebKit storage has no verified
cloud-backup exclusion yet. iOS store release waits for a separately reviewed storage solution
and physical-device backup/restore checks; we do not claim that a simulator build or a setting
for unrelated files excludes this data.

Once the platform's cloud exclusion is implemented and verified, a fresh install or cloud
restore starts a new anonymous account and does not recover unsynced work. Current iOS
cloud-restore behavior is unverified, and older backups may still restore private data.
A verified direct Android transfer may preserve the old account and queue. Until in-app
e-mail linking ships, contributions from an inaccessible old account can be withdrawn through
the privacy contact. Keep the old phone until its queued work has synced.

## What becomes public

**Current collection/release status:** public capture and hosted library uploads are closed.
The proposed first collection mode stores finalized photographs, sample context and optional
bounded instrument declarations privately and unverified. It publishes no pilot observation,
photo or spectrum and does not train a field model. Exact audience, contact, retention and
processor notices must be adopted before that mode is enabled. An instrument declaration does
not verify its source file, calibration or physical pairing. The paragraphs below describe the
later eligible public-release plan, not an automatic consequence of private collection. Photo
publication additionally waits for deployed screening and owner-approved calibration.

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

| Service                                         | Role                                                                                                                                                                                                                        | What it receives                                                                              | Hosts                                                                                                                                |
| ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Supabase                                        | Database, sign-in, private photo storage, server functions                                                                                                                                                                  | Everything in "What we collect", including precise positions and e-mail addresses             | `*.supabase.co`                                                                                                                      |
| Sign-in e-mail delivery (provider not selected) | Sends sign-in links, as the e-mail sender configured in Supabase Auth. No provider is selected or configured. A provider is a new processor and needs the product owner's approval and audit first; Resend is one candidate | Your e-mail address and the sign-in link                                                      | (to be listed when a provider is approved)                                                                                           |
| GitHub                                          | Hosts the website (GitHub Pages) and runs GSIP's scheduled workers (Actions)                                                                                                                                                | Visitors' IP addresses and browser details; workers process private data inside their runs    | `github.com`, `*.github.io`                                                                                                          |
| Hugging Face                                    | Hosts the open dataset                                                                                                                                                                                                      | The public release only                                                                       | `huggingface.co`                                                                                                                     |
| ISRIC – World Soil Information                  | SoilGrids soil maps for estimates and map layers                                                                                                                                                                            | Cell centres (server); map visitors' browsers load map images directly (IP address)           | `rest.isric.org`, `maps.isric.org`, `files.isric.org`                                                                                |
| USDA NRCS Soil Data Access                      | US soil survey values                                                                                                                                                                                                       | Cell centres within the United States (server)                                                | `sdmdataaccess.sc.egov.usda.gov`                                                                                                     |
| Open-Meteo                                      | Elevation, and rainfall in the three days before capture                                                                                                                                                                    | Cell centres and the capture date window (server)                                             | `api.open-meteo.com`, `archive-api.open-meteo.com`                                                                                   |
| Map tile host: GitHub Pages                     | Serves GSIP's SoilGrids-derived prior map tiles from the same origin as the website, once the publication checks pass and `VITE_PRIOR_TILES_BASE` is set                                                                    | Visitors' IP addresses and browser details; no contributor observations or precise positions  | `*.github.io`, `globalsoilintelligence.com` after the DNS cutover                                                                    |
| Squarespace                                     | Served the `globalsoilintelligence.com` holding page before the site moved. As observed on 14 November 2026 the site is served by GitHub Pages. Squarespace may still hold the domain's DNS and e-mail records              | Visitors' IP addresses and browser details                                                    | `globalsoilintelligence.com`                                                                                                         |
| Build dependency/licence repositories           | CI-only retrieval of public open build artifacts and licence/notice evidence; no app runtime request                                                                                                                        | CI runner IP and public artifact coordinates; no contributor data, session, photo or location | `dl.google.com`, `repo.maven.apache.org`, `release-assets.githubusercontent.com`, `raw.githubusercontent.com`, `codeload.github.com` |
| Public licence/source references                | Passive licence/source URLs retained in dependency metadata and reviewed manually; neither the app nor audit collector requests them automatically                                                                          | No contributor data; a reviewer who opens a link shares their own IP/browser details          | `www.apache.org`, `chromium.googlesource.com`, `www.eclipse.org`, `www.opensource.org`                                               |

The product owner approved GitHub Pages as the prior-tile host on 2026-10-11, conditional
on the [tile-host publication checks](../PRIOR_TILE_HOSTING.md). The archives contain only
SoilGrids-derived values, not contributor observations or their private locations. Until those
checks pass, the map continues to load ISRIC's WMS images directly; those requests disclose the
visitor's IP address to ISRIC, as listed above. This hosting decision does not put this draft
notice in force or authorize publication.

**International transfers:** these providers may process data in the United States and in other
countries. The invited pilot is offered only to adults who live in the United States. The
repository records the Supabase project's region as `us-east-1` (United States); that record and
a transfer mechanism for each provider must be confirmed before GSIP is offered to people outside
the United States.

## How long we keep it

| Data                                    | Kept                                                                                                                                                                                                                                                                               |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Original uploads                        | Until checked, and never beyond about a day: an hourly job deletes any original older than 24 hours                                                                                                                                                                                |
| Account and observations                | Until you withdraw them or delete your account; then deleted within 30 days (normally within the hour)                                                                                                                                                                             |
| Observations that failed quality checks | Kept privately, flagged, to improve quality checks; deleted when you withdraw or delete your account. Proposed: also within 24 months of submission (no automated job enforces this yet)                                                                                           |
| Grant and withdrawal records            | The grant's identifier, terms version, date and licences, kept as the record of what was licensed; attribution names are replaced with the default pseudonym when an account is deleted                                                                                            |
| Your contributor record                 | After account deletion, a random identifier with no link to your sign-in, e-mail or name, kept so the grant and withdrawal records stay consistent                                                                                                                                 |
| Rights-request records                  | What was requested and when it was done, without content. Proposed: 3 years after the request was completed (no automated job enforces this yet)                                                                                                                                   |
| Cached map lookups                      | Soil-map and elevation answers for an area of about 0.1 km², with no link to any person, for up to a year                                                                                                                                                                          |
| Hosting, audit logs and backups         | As each provider keeps them: Supabase keeps database backups, its sign-in audit log and its request logs for the periods set by the service plan we choose. Those periods are not verified yet and must be stated here before adoption. GSIP's own worker logs contain counts only |

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
