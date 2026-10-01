begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;

select plan(6);

select ok(
    not has_function_privilege(
        'anon',
        'public.claim_prior_job_attempt(uuid)',
        'execute'
    ),
    'anon cannot claim a prior job attempt'
);
select ok(
    not has_function_privilege(
        'authenticated',
        'public.claim_prior_job_attempt(uuid)',
        'execute'
    ),
    'authenticated clients cannot claim a prior job attempt'
);

set local role service_role;
select is(
    public.claim_prior_job_attempt('73f0400e-5c64-5a6e-90d1-6a7686935317'),
    1::smallint,
    'service-role worker claims the first attempt'
);
select is(
    public.claim_prior_job_attempt('73f0400e-5c64-5a6e-90d1-6a7686935317'),
    2::smallint,
    'a second service-role claim increments from the stored value'
);
update public.prior_jobs
set attempts = 31
where submission_id = '73f0400e-5c64-5a6e-90d1-6a7686935317';
select is(
    public.claim_prior_job_attempt('73f0400e-5c64-5a6e-90d1-6a7686935317'),
    32::smallint,
    'service-role worker can consume the final retry'
);
select is(
    public.claim_prior_job_attempt('73f0400e-5c64-5a6e-90d1-6a7686935317'),
    null,
    'the database refuses attempts beyond the retry budget'
);

select * from finish();
rollback;
