begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;
-- Local transactional fixture only; never run this test file in production.
update public.service_state set capture_open=false where singleton;
select plan(16);
select is((select count(*)
    from pg_proc p
    join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public'
    and p.proname in ('capture_is_open',
    'finalize_submission')
    and not p.prosecdef),
    2::bigint,
    'capture and finalization public entries use caller privileges');
select is((select count(*)
    from pg_proc p
    join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public'
    and p.proname='finalize_submission'
    and p.prosqlbody is not null),
    1::bigint,
    'finalize wrapper has a definition-time bound SQL body');
select is((select count(*)
    from pg_proc p
    join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='private'
    and p.proname='finalize_submission'
    and p.prosecdef
    and p.proconfig @> array['search_path=""']),
    1::bigint,
    'private finalize keeps its guarded privileged body and empty search path');
select is((select count(*)
    from pg_proc p
    join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='private'
    and p.proname='finalize_submission'
    and has_function_privilege('authenticated',
    p.oid,
    'execute')
    and not has_function_privilege('anon',
    p.oid,
    'execute')
    and not has_function_privilege('service_role',
    p.oid,
    'execute')),
    1::bigint,
    'private finalization dispatch is granted only to authenticated');
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
    and p.proname='finalize_submission'
    and q.proname=p.proname),
    1::bigint,
    'finalize wrapper tracks the private function dependency');
select ok(not has_schema_privilege('authenticated',
    'private',
    'usage')
    and not has_schema_privilege('anon',
    'private',
    'usage'),
    'private schema usage remains denied');
select ok(not has_column_privilege('anon',
    'public.service_state',
    'singleton',
    'select')
    and not has_table_privilege('anon',
    'public.service_state',
    'select')
    and not has_column_privilege('authenticated',
    'public.service_state',
    'singleton',
    'select')
    and not has_table_privilege('authenticated',
    'public.service_state',
    'select'),
    'anonymous and authenticated capture callers keep limited column ACLs');
set local role anon;
select is(public.capture_is_open(),false,'anonymous capture remains closed');
select throws_ok($$select public.finalize_submission('00000000-0000-4000-8000-000000000001')$$,
    '42501',
    null,
    'anonymous caller cannot finalize');
reset role;
set local role authenticated;
set local "request.jwt.claims"='{}';
select is(public.capture_is_open(),false,'authenticated capture remains closed');
select throws_ok($$select public.finalize_submission('00000000-0000-4000-8000-000000000001')$$,
    '42501',
    'authentication required',
    'missing auth UID reaches and fails the guarded finalizer');
select throws_ok($$select private.finalize_submission('00000000-0000-4000-8000-000000000001')$$,
    '42501',
    null,
    'direct private finalization name resolution remains denied');
select throws_ok($$update public.submissions set finalized_at=now() where id='00000000-0000-4000-8000-000000000001'$$,
    '42501',
    null,
    'direct finalized_at write remains denied');
reset role;
set local role service_role;
select is(public.capture_is_open(),false,'service capture read remains closed');
select ok(not has_function_privilege('service_role',
    'public.finalize_submission(uuid)',
    'execute'),
    'service does not gain owner finalization');
reset role;
-- Existing singleton PK/check permits at most one true row. An absent row must fail closed.
delete from public.service_state;
set local role anon;
select is(public.capture_is_open(),
    false,
    'an absent switch row fails closed without singleton SELECT privilege');
reset role;
select * from finish();
rollback;
