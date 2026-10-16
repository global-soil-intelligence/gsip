-- Additive migration on the prior schema/data, including a pre-existing withdrawal.
begin;
create extension if not exists pgtap with schema extensions;
set local search_path=public,extensions;
select plan(19);
select is((select count(*) from public.contributors),(select contributors from private.photo_privacy_test_baseline),'existing contributor count is unchanged');
select is((select count(*) from public.contribution_grants),(select grants from private.photo_privacy_test_baseline),'existing immutable grant count is unchanged');
select is((select count(*) from public.submissions),(select submissions from private.photo_privacy_test_baseline),'existing submission count is unchanged');
select is((select count(*) from public.photos),(select photos from private.photo_privacy_test_baseline),'existing A/B/C rows are unchanged');
select is((select count(*) from public.gold_labels),(select labels from private.photo_privacy_test_baseline),'existing holdout/lab label count is unchanged');
select is((select capture_open from public.service_state),(select capture_open from private.photo_privacy_test_baseline),'capture activation is unchanged');
select is((select encode(extensions.digest(convert_to(jsonb_agg(to_jsonb(p) order by p.id)::text,'UTF8'),'sha256'),'hex') from public.photos p),
    (select photo_payload_sha256 from private.photo_privacy_test_baseline),'QA/path/provenance/public photo fields are byte-equivalent');
select is(pg_get_functiondef('public.finalize_submission(uuid)'::regprocedure),(select finalize_definition from private.photo_privacy_test_baseline),'existing finalizer body/signature stays unchanged');
select is(pg_get_functiondef('public.apply_deletion_request(uuid)'::regprocedure),(select apply_definition from private.photo_privacy_test_baseline),'existing apply worker body/signature stays unchanged');
select is(pg_get_functiondef('public.complete_deletion_request(uuid)'::regprocedure),(select complete_definition from private.photo_privacy_test_baseline),'existing complete worker body/signature stays unchanged');
select is((select relacl::text from pg_class where oid='public.photos'::regclass),(select photo_acl from private.photo_privacy_test_baseline),'existing photo ACL is unchanged');
select is((select nspacl::text from pg_namespace where nspname='private'),(select private_acl from private.photo_privacy_test_baseline),'private namespace API grants stay unchanged');
select is((select array_agg(p.polname::text||':'||pg_get_expr(p.polqual,p.polrelid)||':'||coalesce(pg_get_expr(p.polwithcheck,p.polrelid),'') order by p.polname)
    from pg_policy p where p.polrelid='public.photos'::regclass and p.polname not in ('photos_pilot_insert','photos_pilot_update')),(select photo_policies from private.photo_privacy_test_baseline),'existing photo RLS stays unchanged');
select is((select count(*) from private.photo_privacy_content),(select photos-covered_photos from private.photo_privacy_test_baseline),'backfill excludes historically withdrawn payload');
select ok((select bool_and(status='pending' and content_revision=0 and sanitized_sha256 is null and policy_id is null) from private.photo_privacy_content),'legacy QA cannot infer digest or privacy clearance');
select is((select count(*) from private.photo_privacy_tombstones where identity_kind='photo'),(select covered_photos from private.photo_privacy_test_baseline),'historic withdrawal retains only opaque photo refusal');
select is((select count(*) from private.photo_privacy_screens)+(select count(*) from private.photo_privacy_reviews),0::bigint,'no historical detector/human claims are invented');
select ok((select policy_id is null and policy_revision=0 and not implementation_deployed and not publication_open from private.photo_privacy_state),'policy/calibration/deployment/publication all remain unselected/closed');
select is((select count(*) from private.photo_privacy_operators),0::bigint,'migration provisions no human operators');
select * from finish();
rollback;
