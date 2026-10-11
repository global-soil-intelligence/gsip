-- WP-4 and WP-6c: prior job claims, stale requeue, token buckets and the server-only cache.
begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;

select plan(22);

select ok(
    not has_function_privilege('anon', 'public.claim_prior_job_attempt(uuid, boolean)', 'execute'),
    'anon cannot claim a prior job attempt'
);
select ok(
    not has_function_privilege(
        'authenticated', 'public.claim_prior_job_attempt(uuid, boolean)', 'execute'
    ),
    'authenticated clients cannot claim a prior job attempt'
);
select ok(
    not has_function_privilege('authenticated', 'public.take_upstream_token(text, integer)', 'execute')
    and not has_function_privilege('anon', 'public.take_upstream_token(text, integer)', 'execute'),
    'clients cannot spend upstream tokens'
);
select ok(
    not has_table_privilege('anon', 'public.prior_cell_cache', 'select')
    and not has_table_privilege('authenticated', 'public.prior_cell_cache', 'select'),
    'the resolution-9 prior cache is server-only (its keys reveal where people contributed)'
);
select ok(
    not has_table_privilege('authenticated', 'public.upstream_buckets', 'select'),
    'upstream buckets are server-only'
);

set local role service_role;

-- Service retries
select is(
    public.claim_prior_job_attempt('73f0400e-5c64-5a6e-90d1-6a7686935317'),
    1::smallint,
    'service-role worker claims the first attempt of a pending job'
);
select is(
    public.claim_prior_job_attempt('73f0400e-5c64-5a6e-90d1-6a7686935317'),
    null,
    'a job already in processing cannot be claimed twice'
);
update public.prior_jobs set status = 'dead_letter'
where submission_id = '73f0400e-5c64-5a6e-90d1-6a7686935317';
select is(
    public.claim_prior_job_attempt('73f0400e-5c64-5a6e-90d1-6a7686935317'),
    2::smallint,
    'the service worker retries a dead-lettered job, counting from the stored value'
);
update public.prior_jobs set attempts = 31, status = 'dead_letter'
where submission_id = '73f0400e-5c64-5a6e-90d1-6a7686935317';
select is(
    public.claim_prior_job_attempt('73f0400e-5c64-5a6e-90d1-6a7686935317'),
    32::smallint,
    'service-role worker can consume the final retry'
);
update public.prior_jobs set status = 'dead_letter'
where submission_id = '73f0400e-5c64-5a6e-90d1-6a7686935317';
select is(
    public.claim_prior_job_attempt('73f0400e-5c64-5a6e-90d1-6a7686935317'),
    null,
    'the database refuses attempts beyond the retry budget'
);
update public.prior_jobs set status = 'completed', attempts = 1
where submission_id = 'd3445494-bdf6-5834-903e-ed01c056f883';
select is(
    public.claim_prior_job_attempt('d3445494-bdf6-5834-903e-ed01c056f883'),
    null,
    'a completed job is never re-run'
);

-- Contributor-initiated starts
select is(
    public.claim_prior_job_attempt('e6defa07-930a-57d2-95e3-09be6332bd2a', true),
    1::smallint,
    'a contributor request starts an unstarted pending job'
);
update public.prior_jobs set status = 'dead_letter'
where submission_id = 'e6defa07-930a-57d2-95e3-09be6332bd2a';
select is(
    public.claim_prior_job_attempt('e6defa07-930a-57d2-95e3-09be6332bd2a', true),
    null,
    'a contributor request cannot retry a job (only the service worker retries)'
);
select is(
    public.claim_prior_job_attempt('d3445494-bdf6-5834-903e-ed01c056f883', true),
    null,
    'a contributor request cannot re-run a completed job'
);

-- Stale processing claims
update public.prior_jobs
set status = 'processing', updated_at = now() - interval '20 minutes'
where submission_id = '649541e9-80b2-57d7-889a-95e8835f1215';
select is(public.requeue_stale_prior_jobs(), 1, 'one stale processing job is requeued');
select is(
    (select status from public.prior_jobs where submission_id = '649541e9-80b2-57d7-889a-95e8835f1215'),
    'pending',
    'the stale job is pending again'
);

-- Token buckets (SoilGrids: 5 a minute)
update public.upstream_buckets set tokens = capacity, refilled_at = clock_timestamp();
select is(
    (select count(*) filter (where taken) from (
        select public.take_upstream_token('soilgrids') as taken from generate_series(1, 7)
    ) attempts),
    5::bigint,
    'the SoilGrids bucket grants at most five calls at once'
);
select is(public.take_upstream_token('soilgrids'), false, 'an empty bucket defers');
update public.upstream_buckets
set refilled_at = clock_timestamp() - interval '12 seconds'
where source = 'soilgrids';
select is(public.take_upstream_token('soilgrids'), true, 'the bucket refills over time');
select is(public.take_upstream_token('soilgrids'), false, 'refill is proportional to elapsed time');
select throws_ok(
    $$select public.take_upstream_token('wosis')$$,
    '22023',
    'unknown upstream source wosis',
    'unknown sources are refused'
);
select ok(public.take_upstream_token('open_meteo', 3), 'multi-token costs are supported');

select * from finish();
rollback;
