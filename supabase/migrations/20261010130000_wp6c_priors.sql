-- WP-6c (launch blocker 2): priors that respect upstream fair use and never retry an empty answer.
--   * prior_jobs.empty_sources records sources that definitively returned nothing (SoilGrids masks
--     built-up land, for example): "no prior" is a terminal state, not a failure (SPEC I3).
--   * prior_cell_cache keeps static lookups per resolution-9 cell; it reveals where people have
--     contributed, so it is server-only.
--   * begin_prior_attempt() claims a job and spends its upstream tokens atomically, so a request
--     that cannot be claimed or must wait spends nothing (I14). A contributor may only start their
--     own unstarted job; only the service worker retries.

alter table public.prior_jobs add column empty_sources text[] not null default '{}';
comment on column public.prior_jobs.empty_sources is
    'Sources that answered definitively with no data for this location; never retried.';

create table public.prior_cell_cache (
    h3_r9 text not null check (h3_r9 ~ '^89[0-9a-f]{13}$'),
    source text not null check (source in ('soilgrids', 'ssurgo', 'elevation')),
    payload jsonb not null,
    retrieved_at timestamptz not null default now(),
    primary key (h3_r9, source)
);

comment on table public.prior_cell_cache is
    'WP-6c: static prior lookups per resolution-9 cell centre. Server-only: the keys reveal where people contributed.';

alter table public.prior_cell_cache enable row level security;
revoke all on public.prior_cell_cache from public, anon, authenticated;
grant select, insert, update, delete on public.prior_cell_cache to service_role;
create policy prior_cell_cache_server_only on public.prior_cell_cache
    for all to anon, authenticated using (false) with check (false);

create table public.upstream_buckets (
    source text primary key check (source in ('soilgrids', 'ssurgo', 'open_meteo')),
    capacity integer not null check (capacity > 0),
    refill_per_minute numeric not null check (refill_per_minute > 0),
    tokens numeric not null check (tokens >= 0),
    refilled_at timestamptz not null default clock_timestamp()
);

comment on table public.upstream_buckets is
    'WP-6c: token buckets shared by every prior lookup. SoilGrids holds one token refilled 5 times a minute, so calls are at least 12 s apart and no 60 s window holds more than 5 (ISRIC fair use).';

insert into public.upstream_buckets (source, capacity, refill_per_minute, tokens)
values
    ('soilgrids', 1, 5, 1),
    ('ssurgo', 30, 30, 30),
    ('open_meteo', 60, 60, 60)
on conflict (source) do nothing;

alter table public.upstream_buckets enable row level security;
revoke all on public.upstream_buckets from public, anon, authenticated;
grant select, update on public.upstream_buckets to service_role;
create policy upstream_buckets_server_only on public.upstream_buckets
    for all to anon, authenticated using (false) with check (false);

-- Owners could previously re-run a completed job at will, each run calling every upstream source.
drop function if exists public.claim_prior_job_attempt(uuid);

-- Claim a job and pay for its upstream calls in one transaction. Tokens are spent only when the
-- claim succeeds, and the claim succeeds only when every needed token is available, so an
-- unclaimable or deferred request can never drain a bucket (SPEC I14).
create or replace function public.begin_prior_attempt(
    p_submission_id uuid,
    p_owner_request boolean,
    p_costs jsonb
)
returns table (outcome text, attempts smallint, retry_after_seconds integer)
language plpgsql
volatile
security invoker
set search_path = ''
as $$
declare
    job_status text;
    job_attempts smallint;
    claimed smallint;
    moment timestamptz;
    bucket record;
    cost numeric;
    available numeric;
    shortfall boolean := false;
    wait_seconds numeric := 0;
    unknown_sources text[];
begin
    if p_costs is null or jsonb_typeof(p_costs) <> 'object' then
        raise exception 'costs must be a JSON object' using errcode = '22023';
    end if;
    select array_agg(key) into unknown_sources
    from jsonb_object_keys(p_costs) as key
    where key not in (select b.source from public.upstream_buckets b);
    if unknown_sources is not null then
        raise exception 'unknown upstream source(s): %', array_to_string(unknown_sources, ', ')
            using errcode = '22023';
    end if;
    if exists (
        select 1 from jsonb_each_text(p_costs) as c (key, value)
        join public.upstream_buckets b on b.source = c.key
        where c.value !~ '^[0-9]+$' or c.value::integer > b.capacity
    ) then
        raise exception 'token costs must be whole numbers within bucket capacity'
            using errcode = '22023';
    end if;

    select j.status, j.attempts into job_status, job_attempts
    from public.prior_jobs j
    where j.submission_id = p_submission_id
    for update;
    if not found or job_attempts >= 32 or not (
        (p_owner_request and job_status = 'pending' and job_attempts = 0)
        or (not coalesce(p_owner_request, false) and job_status in ('pending', 'dead_letter'))
    ) then
        return query select 'not_claimable'::text, null::smallint, null::integer;
        return;
    end if;

    -- Lock the needed buckets in a fixed order, then read the clock: a transaction that waited
    -- for a lock must not write an earlier refill time.
    perform 1 from public.upstream_buckets b
    where (p_costs ->> b.source)::integer > 0
    order by b.source
    for update;
    moment := clock_timestamp();

    for bucket in
        select b.source, b.capacity, b.refill_per_minute, b.tokens, b.refilled_at
        from public.upstream_buckets b
        where (p_costs ->> b.source)::integer > 0
        order by b.source
    loop
        cost := (p_costs ->> bucket.source)::numeric;
        available := least(
            bucket.capacity::numeric,
            bucket.tokens
                + greatest(0, extract(epoch from (moment - bucket.refilled_at))) / 60.0
                * bucket.refill_per_minute
        );
        if available < cost then
            shortfall := true;
            wait_seconds := greatest(wait_seconds, (cost - available) / bucket.refill_per_minute * 60.0);
        end if;
        update public.upstream_buckets b
        set tokens = available, refilled_at = greatest(b.refilled_at, moment)
        where b.source = bucket.source;
    end loop;

    if shortfall then
        return query select 'deferred'::text, null::smallint, ceil(wait_seconds)::integer;
        return;
    end if;

    update public.upstream_buckets b
    set tokens = b.tokens - (p_costs ->> b.source)::numeric
    where (p_costs ->> b.source)::integer > 0;

    update public.prior_jobs j
    set
        attempts = j.attempts + 1,
        last_error = null,
        started_at = now(),
        status = 'processing',
        updated_at = now()
    where j.submission_id = p_submission_id
    returning j.attempts into claimed;
    return query select 'claimed'::text, claimed, null::integer;
end;
$$;

revoke all on function public.begin_prior_attempt(uuid, boolean, jsonb) from public, anon, authenticated;
grant execute on function public.begin_prior_attempt(uuid, boolean, jsonb) to service_role;

comment on function public.begin_prior_attempt(uuid, boolean, jsonb) is
    'Service role only. Atomically claims one prior-enrichment attempt and spends its upstream tokens: claimed, deferred (with a retry-after in seconds, nothing spent or claimed) or not_claimable. A contributor request may start only an unstarted job; only the service worker retries.';

create or replace function public.fail_prior_job(p_submission_id uuid, p_reason text)
returns void
language sql
volatile
security invoker
set search_path = ''
as $$
    update public.prior_jobs
    set status = 'dead_letter', attempts = 32, last_error = left(p_reason, 1000), updated_at = now()
    where submission_id = p_submission_id;
$$;

revoke all on function public.fail_prior_job(uuid, text) from public, anon, authenticated;
grant execute on function public.fail_prior_job(uuid, text) to service_role;

comment on function public.fail_prior_job(uuid, text) is
    'Service role only: ends a job that can never succeed (invalid geometry), so it cannot block the drain.';

create or replace function public.requeue_stale_prior_jobs(p_older_than interval default interval '15 minutes')
returns integer
language plpgsql
volatile
security invoker
set search_path = ''
as $$
declare
    requeued integer;
begin
    update public.prior_jobs
    set
        status = case when attempts >= 32 then 'dead_letter' else 'pending' end,
        last_error = case
            when attempts >= 32 then 'retry_budget_exhausted'
            else 'stale_processing_requeued'
        end,
        updated_at = now()
    where status = 'processing' and updated_at < now() - p_older_than;
    get diagnostics requeued = row_count;
    return requeued;
end;
$$;

revoke all on function public.requeue_stale_prior_jobs(interval) from public, anon, authenticated;
grant execute on function public.requeue_stale_prior_jobs(interval) to service_role;

comment on function public.requeue_stale_prior_jobs(interval) is
    'Returns prior jobs stuck in processing (a killed invocation) to pending, or to dead_letter once their 32 attempts are spent. Service role only.';
