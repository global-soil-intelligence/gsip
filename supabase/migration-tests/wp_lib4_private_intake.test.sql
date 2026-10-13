-- Additive migration applied to the existing synthetic legacy dataset.
begin;
create extension if not exists pgtap with schema extensions;
set local search_path=public,extensions;
select plan(13);
select is((select count(*) from public.contributors),(select contributors from private.lib4b_test_baseline),'contributor rows survive');
select is((select count(*) from public.contribution_grants),(select grants from private.lib4b_test_baseline),'immutable grants survive');
select is((select count(*) from public.submissions),(select submissions from private.lib4b_test_baseline),'legacy submission rows survive');
select is((select count(*) from public.photos),(select photos from private.lib4b_test_baseline),'legacy photo rows survive');
select is((select count(*) from public.gold_labels),(select labels from private.lib4b_test_baseline),'legacy labels survive');
select is((select capture_open from public.service_state),(select capture_open from private.lib4b_test_baseline),'capture gate value is unchanged');
select ok(not (public.library_intake_capabilities()->>'available')::boolean,'library intake defaults closed');
select is((select count(*) from private.library_intakes),0::bigint,'migration creates no library acceptance backfill');
select is(pg_get_functiondef('public.finalize_submission(uuid)'::regprocedure),(select finalize_definition from private.lib4b_test_baseline),'existing finalizer signature/body remains unchanged');
select is(pg_get_functiondef('public.apply_deletion_request(uuid)'::regprocedure),(select apply_definition from private.lib4b_test_baseline),'old worker apply signature/body remains unchanged');
select is(pg_get_functiondef('public.complete_deletion_request(uuid)'::regprocedure),(select complete_definition from private.lib4b_test_baseline),'old worker completion signature/body remains unchanged');
select is((select relacl::text from pg_class where oid='public.submissions'::regclass),(select submission_acl from private.lib4b_test_baseline),'legacy submission table ACL unchanged');
select ok(
    (select relacl::text from pg_class where oid='public.photos'::regclass) is not distinct from (select photo_acl from private.lib4b_test_baseline)
    and (select nspacl::text from pg_namespace where nspname='private') is not distinct from (select private_acl from private.lib4b_test_baseline)
    and (select array_agg(p.polname::text || ':' || pg_get_expr(p.polqual,p.polrelid) || ':' ||
        coalesce(pg_get_expr(p.polwithcheck,p.polrelid),'') order by p.polname)
        from pg_policy p where p.polrelid='public.submissions'::regclass) is not distinct from
        (select submission_policies from private.lib4b_test_baseline),
    'photo/private-schema ACLs and existing submission RLS are unchanged');
select * from finish();
rollback;
