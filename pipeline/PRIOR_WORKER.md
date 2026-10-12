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

`prior-attach` runs behind the gateway's JWT check (`verify_jwt = true` in `supabase/config.toml`). It
is in service mode only when the bearer token is exactly the service-role key (compared in constant
time); a decoded token claim is never trusted. Everyone else is a contributor, whose read of the
submission goes through row-level security, so they can only start their own.

Claiming a job and paying for its upstream calls is one database step, `begin_prior_attempt(id,
owner_request, costs)`. The function first works out which calls it needs (cache misses, plus a
precipitation call unless the capture time is outside the forecast and archive ranges), then:

- **claimed**: the job is now `processing`, its attempt is counted and every needed token is spent;
- **deferred**: a bucket is short; nothing is claimed or spent, and the answer carries a wait in
  seconds (202 with `Retry-After`);
- **not claimable**: nothing is claimed or spent (409). A contributor may only start their own
  unstarted job; only the service worker retries, and never past 32 attempts. Completed jobs are
  never re-run.

The buckets are shared by every invocation. SoilGrids holds a single token refilled five times a
minute, so calls are at least 12 seconds apart and no 60-second window holds more than five (ISRIC's
published limit, which counts retries); SSURGO allows 30 a minute and Open-Meteo 60. Every upstream
call costs one token and is made once: there are no immediate retries, because the job retry is the
retry. A definitive rejection (a 4xx other than 408 or 429) counts as an empty answer.

A job that can never succeed (its stored geometry is unusable) is ended with `fail_prior_job`, which
dead-letters it with the attempt budget spent, so it cannot hold the head of the queue.

## Service drain

Every five minutes `pipeline.prior_worker` returns claims stuck in `processing` for 15 minutes to
`pending` (or to `dead_letter` once their 32 attempts are spent), then works through `pending` and
`dead_letter` jobs, oldest update first:

- on a deferral it waits for `Retry-After` (bounded to 1–300 seconds) and retries the same job, but
  only while the wait fits the run's 240-second budget, and it starts no new job once the budget is
  spent, so a run normally ends before the next is due;
- a job whose invocation failed is moved behind the rest of the queue (only while it is still
  `pending` or `dead_letter`; a `processing` claim is never touched, so stale-claim detection keeps
  working);
- the run exits non-zero while any job remains retryable, which surfaces upstream outages.

Empty answers complete the job and are recorded in `prior_jobs.empty_sources`; only failures
dead-letter, and their successful sources are kept and cached. Prior rows upsert on the canonical
composite key, so reruns are safe. CI uses recorded responses only and makes no live API calls;
`deno check` type-checks the function.
