-- WP-6c (launch blocker 2): priors that respect upstream fair use and never retry an empty answer.
--   * prior_jobs.empty_sources records sources that definitively returned nothing (SoilGrids masks
--     built-up land, for example): "no prior" is a terminal state, not a failure (SPEC I3).
--   * prior_cell_cache keeps static lookups per resolution-9 cell; it reveals where people have
--     contributed, so it is server-only.
--   * upstream_buckets + take_upstream_token() enforce fair-use rates across every invocation (I14).
--   * claim_prior_job_attempt() distinguishes a contributor's one-time start from service retries.

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
    'WP-6c: token buckets shared by every prior lookup. SoilGrids asks for at most 5 calls a minute.';

insert into public.upstream_buckets (source, capacity, refill_per_minute, tokens)
values
    ('soilgrids', 5, 5, 5),
    ('ssurgo', 30, 30, 30),
    ('open_meteo', 60, 60, 60)
on conflict (source) do nothing;

alter table public.upstream_buckets enable row level security;
revoke all on public.upstream_buckets from public, anon, authenticated;
grant select, update on public.upstream_buckets to service_role;
create policy upstream_buckets_server_only on public.upstream_buckets
    for all to anon, authenticated using (false) with check (false);

create or replace function public.take_upstream_token(p_source text, p_cost integer default 1)
returns boolean
language plpgsql
volatile
security invoker
set search_path = ''
as $$
declare
    bucket public.upstream_buckets;
    moment timestamptz := clock_timestamp();
    available numeric;
begin
    if p_cost is null or p_cost < 1 then
        raise exception 'token cost must be at least 1' using errcode = '22023';
    end if;
    select * into bucket from public.upstream_buckets b where b.source = p_source for update;
    if not found then
        raise exception 'unknown upstream source %', p_source using errcode = '22023';
    end if;
    available := least(
        bucket.capacity::numeric,
        bucket.tokens + greatest(0, extract(epoch from (moment - bucket.refilled_at))) / 60.0
            * bucket.refill_per_minute
    );
    if available < p_cost then
        update public.upstream_buckets
        set tokens = available, refilled_at = moment
        where source = p_source;
        return false;
    end if;
    update public.upstream_buckets
    set tokens = available - p_cost, refilled_at = moment
    where source = p_source;
    return true;
end;
$$;

revoke all on function public.take_upstream_token(text, integer) from public, anon, authenticated;
grant execute on function public.take_upstream_token(text, integer) to service_role;

comment on function public.take_upstream_token(text, integer) is
    'Service role only: atomically takes tokens from a shared upstream bucket; false means defer.';

-- Owners could previously re-run a completed job at will, each run calling every upstream source.
drop function if exists public.claim_prior_job_attempt(uuid);

create or replace function public.claim_prior_job_attempt(
    p_submission_id uuid,
    p_owner_request boolean default false
)
returns smallint
language sql
volatile
security invoker
set search_path = ''
as $$
    update public.prior_jobs
    set
        attempts = attempts + 1,
        last_error = null,
        started_at = now(),
        status = 'processing',
        updated_at = now()
    where submission_id = p_submission_id
      and attempts < 32
      and (
          (p_owner_request and status = 'pending' and attempts = 0)
          or (not p_owner_request and status in ('pending', 'dead_letter'))
      )
    returning attempts;
$$;

comment on function public.claim_prior_job_attempt(uuid, boolean) is
    'Atomically claims one prior-enrichment attempt. A contributor request may start only an unstarted job; only the service worker retries. Service role only.';

revoke all on function public.claim_prior_job_attempt(uuid, boolean) from public, anon, authenticated;
grant execute on function public.claim_prior_job_attempt(uuid, boolean) to service_role;

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
    set status = 'pending', last_error = 'stale_processing_requeued', updated_at = now()
    where status = 'processing' and updated_at < now() - p_older_than;
    get diagnostics requeued = row_count;
    return requeued;
end;
$$;

revoke all on function public.requeue_stale_prior_jobs(interval) from public, anon, authenticated;
grant execute on function public.requeue_stale_prior_jobs(interval) to service_role;

comment on function public.requeue_stale_prior_jobs(interval) is
    'Returns prior jobs stuck in processing (a killed invocation) to pending. Service role only.';
