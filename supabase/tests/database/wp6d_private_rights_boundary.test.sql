begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;
-- Local transactional fixture only; never run this test file in production.
update public.service_state set capture_open=false where singleton;
-- Synthetic private records only; no observation, location or photo fixtures.
insert into public.contributors(id,
    auth_uid,
    handle) values('10000000-0000-4000-8000-0000000000aa',
    null,
    'local-security-proof');
insert into public.contribution_grants(id,contributor_id,terms_version,accepted_at,attribution_name)
values('10000000-0000-4000-8000-0000000000ab',
    '10000000-0000-4000-8000-0000000000aa',
    '2026-07-22-v1',
    now(),
    'Anonymous soil contributor');
set local role service_role;
insert into public.grant_withdrawals(grant_id,
    reason) values('10000000-0000-4000-8000-0000000000ab',
    'steward_action');
insert into public.attribution_reviews(contributor_id,attribution_name,decision,reviewer)
values('10000000-0000-4000-8000-0000000000aa','Anonymous soil contributor','approved','local-proof');
reset role;
select plan(21);
select is((select count(*)
    from pg_proc p
    join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public'
    and p.proname in ('current_auth_user_exists',
    'my_submission_accepts_uploads')
    and not p.prosecdef),
    2::bigint,
    'both rights public entries use caller privileges');
select is((select count(*)
    from pg_proc p
    join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public'
    and p.proname in ('current_auth_user_exists',
    'my_submission_accepts_uploads')
    and p.prosqlbody is not null),
    2::bigint,
    'both rights wrappers use definition-time bound SQL bodies');
select is((select count(*)
    from pg_proc p
    join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='private'
    and p.proname in ('current_auth_user_exists',
    'my_submission_accepts_uploads')
    and p.prosecdef
    and p.proconfig @> array['search_path=""']),
    2::bigint,
    'both private rights helpers retain guarded privileged bodies');
select is((select count(*)
    from pg_proc p
    join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='private'
    and p.proname in ('current_auth_user_exists',
    'my_submission_accepts_uploads')
    and has_function_privilege('authenticated',
    p.oid,
    'execute')
    and has_function_privilege('service_role',
    p.oid,
    'execute')
    and not has_function_privilege('anon',
    p.oid,
    'execute')),
    2::bigint,
    'both rights private dispatch grants preserve authenticated and service callers');
select is((select count(*)
    from pg_depend d
    join pg_proc p on p.oid=d.objid
    join pg_namespace n on n.oid=p.pronamespace
    join pg_proc q on q.oid=d.refobjid
    join pg_namespace m on m.oid=q.pronamespace
    where d.classid='pg_proc'::regclass
    and d.refclassid='pg_proc'::regclass
    and n.nspname='public'
    and m.nspname='private'
    and p.proname in ('current_auth_user_exists',
    'my_submission_accepts_uploads')
    and q.proname=p.proname),
    2::bigint,
    'both rights wrappers track their private callee dependencies');
select ok(not has_schema_privilege('authenticated',
    'private',
    'usage')
    and not has_schema_privilege('anon',
    'private',
    'usage'),
    'private schema usage remains denied');
select is((select count(*)
    from pg_proc p
    join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='private'
    and p.proname in ('finalize_submission',
    'current_auth_user_exists',
    'my_submission_accepts_uploads')
    and has_function_privilege('anon',
    p.oid,
    'execute')),
    0::bigint,
    'anonymous callers execute none of the three private dispatch callees');
select ok(not has_table_privilege('authenticated',
    'public.grant_withdrawals',
    'select')
    and not has_table_privilege('authenticated',
    'public.attribution_reviews',
    'select')
    and not has_table_privilege('authenticated',
    'auth.users',
    'select'),
    'no private table or auth-user reads are granted');
select is((select count(*)
    from pg_policy p
    where p.polname in ('grant_withdrawals_deny_client',
    'attribution_reviews_deny_client')
    and not p.polpermissive
    and pg_get_expr(p.polqual,
    p.polrelid)='false'
    and pg_get_expr(p.polwithcheck,
    p.polrelid)='false'),
    2::bigint,
    'both private tables have explicit restrictive false policies');
set local role authenticated;
set local "request.jwt.claims"='{}';
select is(public.current_auth_user_exists(),false,'missing auth UID cannot exist through the wrapper');
select is(public.my_submission_accepts_uploads('00000000-0000-4000-8000-000000000001'),
    false,
    'missing auth UID cannot upload through the wrapper');
select throws_ok($$select private.current_auth_user_exists()$$,
    '42501',
    null,
    'direct private helper name resolution remains denied');
select throws_ok($$select count(*) from public.grant_withdrawals$$,
    '42501',
    null,
    'direct private withdrawal read remains denied');
reset role;
-- Rolled-back fault injection: default deny alone is insufficient here.
-- An accidental permissive policy and SELECT grant must not expose the fixtures.
create policy local_test_allow_withdrawal_read
    on public.grant_withdrawals as permissive
    for select to authenticated using (true);
create policy local_test_allow_attribution_read
    on public.attribution_reviews as permissive
    for select to authenticated using (true);
grant select on public.grant_withdrawals,public.attribution_reviews to authenticated;
set local role authenticated;
select is((select count(*)
    from public.grant_withdrawals),
    0::bigint,
    'withdrawals remain hidden under an accidental SELECT grant and permissive policy');
select is((select count(*)
    from public.attribution_reviews),
    0::bigint,
    'attribution reviews remain hidden under an accidental SELECT grant and permissive policy');
reset role;
set local role service_role;
select is((select count(*)
    from public.grant_withdrawals),
    1::bigint,
    'service can insert and read the withdrawal fixture');
select is((select count(*)
    from public.attribution_reviews),
    1::bigint,
    'service can insert and read the attribution fixture');
select is(public.current_auth_user_exists(),false,'service auth-existence capability is preserved');
select is(public.my_submission_accepts_uploads('00000000-0000-4000-8000-000000000001'),
    false,
    'service upload-helper capability is preserved');
reset role;
set local role anon;
select throws_ok($$select public.my_submission_accepts_uploads('00000000-0000-4000-8000-000000000001')$$,
    '42501',
    null,
    'anonymous caller cannot probe upload eligibility');
select throws_ok($$select public.current_auth_user_exists()$$,
    '42501',
    null,
    'anonymous caller cannot probe auth-user existence');
reset role;
select * from finish();
rollback;
