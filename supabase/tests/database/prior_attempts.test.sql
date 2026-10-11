-- WP-4 and WP-6c: atomic claim-and-spend, stale requeue, terminal failures and the server-only cache.
begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;

select plan(30);

-- Privileges: every prior-job and bucket function and table is server-only.
select ok(
    not has_function_privilege('anon', 'public.begin_prior_attempt(uuid, boolean, jsonb)', 'execute')
    and not has_function_privilege('authenticated', 'public.begin_prior_attempt(uuid, boolean, jsonb)', 'execute'),
    'clients cannot claim prior attempts or spend upstream tokens'
);
select ok(
    not has_function_privilege('anon', 'public.requeue_stale_prior_jobs(interval)', 'execute')
    and not has_function_privilege('authenticated', 'public.requeue_stale_prior_jobs(interval)', 'execute'),
    'clients cannot requeue prior jobs'
);
select ok(
    not has_function_privilege('anon', 'public.fail_prior_job(uuid, text)', 'execute')
    and not has_function_privilege('authenticated', 'public.fail_prior_job(uuid, text)', 'execute'),
    'clients cannot end prior jobs'
);
select ok(
    not has_table_privilege('anon', 'public.prior_cell_cache', 'select')
    and not has_table_privilege('authenticated', 'public.prior_cell_cache', 'select'),
    'the resolution-9 prior cache is server-only (its keys reveal where people contributed)'
);
select ok(
    not has_table_privilege('anon', 'public.upstream_buckets', 'select')
    and not has_table_privilege('authenticated', 'public.upstream_buckets', 'select'),
    'upstream buckets are server-only'
);
select hasnt_function(
    'public', 'claim_prior_job_attempt', array['uuid'],
    'the old claim without owner rules or token accounting is gone'
);

set local role service_role;
update public.upstream_buckets set tokens = capacity, refilled_at = clock_timestamp();

-- A service retry of a pending job: claimed, and its tokens are spent.
select results_eq(
    $$select outcome, attempts, retry_after_seconds from public.begin_prior_attempt(
        '73f0400e-5c64-5a6e-90d1-6a7686935317', false, '{"soilgrids": 1, "open_meteo": 2}')$$,
    $$values ('claimed'::text, 1::smallint, null::integer)$$,
    'the service worker claims a pending job'
);
select is(
    (select round(tokens) from public.upstream_buckets where source = 'soilgrids'),
    0::numeric,
    'a claimed attempt spends its SoilGrids token'
);
select is(
    (select round(tokens) from public.upstream_buckets where source = 'open_meteo'),
    58::numeric,
    'a claimed attempt spends its Open-Meteo tokens'
);

-- Unclaimable requests spend nothing (the review's starvation scenario).
update public.upstream_buckets set tokens = capacity, refilled_at = clock_timestamp();
select is(
    (select outcome from public.begin_prior_attempt(
        '73f0400e-5c64-5a6e-90d1-6a7686935317', false, '{"soilgrids": 1, "open_meteo": 1}')),
    'not_claimable',
    'a job already in processing cannot be claimed twice'
);
update public.prior_jobs set status = 'completed', attempts = 1
where submission_id = 'd3445494-bdf6-5834-903e-ed01c056f883';
select is(
    (select outcome from public.begin_prior_attempt(
        'd3445494-bdf6-5834-903e-ed01c056f883', true, '{"soilgrids": 1, "open_meteo": 1}')),
    'not_claimable',
    'a contributor cannot re-run a completed job'
);
select is(
    (select outcome from public.begin_prior_attempt(
        'd3445494-bdf6-5834-903e-ed01c056f883', false, '{"soilgrids": 1, "open_meteo": 1}')),
    'not_claimable',
    'nobody re-runs a completed job'
);
select is(
    (select array_agg(round(tokens) order by source) from public.upstream_buckets),
    array[60, 1, 30]::numeric[],
    'unclaimable requests spend no tokens at all'
);

-- Deferral: nothing claimed, nothing spent, and a wait hint.
update public.upstream_buckets set tokens = 0, refilled_at = clock_timestamp() where source = 'soilgrids';
select results_eq(
    $$select outcome, attempts from public.begin_prior_attempt(
        'e6defa07-930a-57d2-95e3-09be6332bd2a', true, '{"soilgrids": 1, "open_meteo": 1}')$$,
    $$values ('deferred'::text, null::smallint)$$,
    'an empty SoilGrids bucket defers the start'
);
select ok(
    (select retry_after_seconds between 1 and 12 from public.begin_prior_attempt(
        'e6defa07-930a-57d2-95e3-09be6332bd2a', true, '{"soilgrids": 1}')),
    'a deferral says when to come back (12 s per SoilGrids token)'
);
select is(
    (select status || ':' || attempts from public.prior_jobs
     where submission_id = 'e6defa07-930a-57d2-95e3-09be6332bd2a'),
    'pending:0',
    'a deferred job is not claimed and keeps its attempts'
);
select is(
    (select round(tokens) from public.upstream_buckets where source = 'open_meteo'),
    60::numeric,
    'a deferral spends none of the other buckets either'
);

-- Contributor starts and service retries.
update public.upstream_buckets set tokens = capacity, refilled_at = clock_timestamp();
select is(
    (select attempts from public.begin_prior_attempt(
        'e6defa07-930a-57d2-95e3-09be6332bd2a', true, '{"open_meteo": 1}')),
    1::smallint,
    'a contributor request starts their unstarted job'
);
update public.prior_jobs set status = 'dead_letter'
where submission_id = 'e6defa07-930a-57d2-95e3-09be6332bd2a';
select is(
    (select outcome from public.begin_prior_attempt(
        'e6defa07-930a-57d2-95e3-09be6332bd2a', true, '{"open_meteo": 1}')),
    'not_claimable',
    'a contributor request cannot retry (only the service worker retries)'
);
select is(
    (select attempts from public.begin_prior_attempt(
        'e6defa07-930a-57d2-95e3-09be6332bd2a', false, '{"open_meteo": 1}')),
    2::smallint,
    'the service worker retries a dead-lettered job, counting from the stored value'
);
update public.prior_jobs set attempts = 32, status = 'dead_letter'
where submission_id = 'e6defa07-930a-57d2-95e3-09be6332bd2a';
select is(
    (select outcome from public.begin_prior_attempt(
        'e6defa07-930a-57d2-95e3-09be6332bd2a', false, '{"open_meteo": 1}')),
    'not_claimable',
    'the database refuses attempts beyond the retry budget'
);

-- Input validation.
select throws_ok(
    $$select * from public.begin_prior_attempt('e6defa07-930a-57d2-95e3-09be6332bd2a', false, '{"wosis": 1}')$$,
    '22023',
    'unknown upstream source(s): wosis',
    'unknown sources are refused'
);
select throws_ok(
    $$select * from public.begin_prior_attempt('e6defa07-930a-57d2-95e3-09be6332bd2a', false, '{"soilgrids": 2}')$$,
    '22023',
    'token costs must be whole numbers within bucket capacity',
    'a cost above capacity is refused rather than deferred forever'
);

-- Refill: SoilGrids holds one token and refills five a minute (calls at least 12 s apart).
update public.upstream_buckets set tokens = 0, refilled_at = clock_timestamp() - interval '13 seconds'
where source = 'soilgrids';
select is(
    (select outcome from public.begin_prior_attempt(
        '649541e9-80b2-57d7-889a-95e8835f1215', false, '{"soilgrids": 1}')),
    'claimed',
    'the SoilGrids bucket refills after 12 seconds'
);
select is(
    (select capacity from public.upstream_buckets where source = 'soilgrids'),
    1,
    'SoilGrids never banks a burst: at most 5 calls in any minute'
);

-- Stale claims and terminal failures.
update public.prior_jobs
set status = 'processing', updated_at = now() - interval '20 minutes', attempts = 3
where submission_id = '51e50bf8-3684-5869-9da1-fa0b9d88e481';
update public.prior_jobs
set status = 'processing', updated_at = now() - interval '20 minutes', attempts = 32
where submission_id = '04073bdf-ac5c-5eba-9265-35c543d37de0';
select is(public.requeue_stale_prior_jobs(), 2, 'both stale processing jobs are found');
select is(
    (select status from public.prior_jobs where submission_id = '51e50bf8-3684-5869-9da1-fa0b9d88e481'),
    'pending',
    'a stale job with attempts left is pending again'
);
select is(
    (select status from public.prior_jobs where submission_id = '04073bdf-ac5c-5eba-9265-35c543d37de0'),
    'dead_letter',
    'a stale job with no attempts left becomes terminal instead of pending forever'
);
select lives_ok(
    $$select public.fail_prior_job('510ddbd0-d1fb-5664-9816-2a7e7ee804bc', 'invalid_geometry')$$,
    'the service worker can end a job that can never succeed'
);
select is(
    (select status || ':' || attempts || ':' || last_error from public.prior_jobs
     where submission_id = '510ddbd0-d1fb-5664-9816-2a7e7ee804bc'),
    'dead_letter:32:invalid_geometry',
    'an ended job can never be claimed again'
);

select * from finish();
rollback;
