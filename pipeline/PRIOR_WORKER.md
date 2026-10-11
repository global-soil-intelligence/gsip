# Prior-attach worker

`prior-attach` is a JWT-protected Supabase Edge Function. Every new submission receives a durable
`prior_jobs` row from the database trigger; the capture client then invokes the function once. The
decisions live in `packages/schema/src/priorJob.ts`, which is unit-tested with fake dependencies; the
function only adapts them to the database and `fetch`.

## Privacy

External services never see a contributor's precise point (SPEC I7). Every lookup uses the centre of
the submission's resolution-9 H3 cell (about 0.1 km², within one SoilGrids 250 m pixel of the point),
which is also the cache key. The cache table `prior_cell_cache` is server-only, because its keys reveal
where people have contributed.

## Sources

- SoilGrids mean/Q05/Q95 for the native 0–5, 5–15 and 15–30 cm layers; GSIP stores 0–5 cm and a
  thickness-weighted 0–30 cm aggregate. Averaging layer quantiles gives a conservative (wider than
  exact) interval. SoilGrids answers `null` where it has no estimate (it masks built-up land, water and
  rock): a property with a null mean yields no row, and an all-null answer is a definitive **no prior**.
- In CONUS, SSURGO major-component horizons, thickness and component weighted.
- Open-Meteo GLO-90 elevation.
- Precipitation in the **72 hours before capture** (hourly values ending at `captured_at`): the
  forecast API for captures within 90 days, the archive API before that. The flag means at least 1 mm.

SoilGrids, SSURGO and elevation results, including empty answers, are cached per cell for 365 days. A
second observation in the same cell fetches only its own precipitation window.

## Fair use and retries

Every upstream call first takes a token from a database bucket shared by all invocations
(`take_upstream_token`): SoilGrids 5 a minute (ISRIC's published limit), SSURGO 30, Open-Meteo 60.
Without a token the job is **deferred** before it is claimed, so it consumes no attempt; the function
answers 202 and the drain stops for that run. SoilGrids gets a single call per claimed attempt because
ISRIC's limit counts retries; the other sources allow one quick retry.

A contributor's request can start only their own unstarted job (`claim_prior_job_attempt(id, true)`);
completed jobs are never re-run. The five-minute service drain (`pipeline.prior_worker`) first returns
claims stuck in `processing` for 15 minutes to `pending`, then retries `pending` and `dead_letter` jobs
up to the 32-attempt cap. Empty answers complete the job and are recorded in
`prior_jobs.empty_sources`; only failures dead-letter, and their successful sources are kept and
cached. Prior rows upsert on the canonical composite key, so reruns are safe. CI uses recorded
responses only and makes no live API calls; `deno check` type-checks the function.
