-- Existing synthetic data at the prior schema; no downloads, images or new observations.
-- The earlier fixture's synthetic grant was withdrawn before privacy state existed.
insert into public.grant_withdrawals(grant_id,reason)
select id,'contributor_request' from public.contribution_grants
where id='f1000000-0000-4000-8000-000000000005' on conflict do nothing;
create table private.photo_privacy_test_baseline as select
    (select count(*) from public.contributors) contributors,
    (select count(*) from public.contribution_grants) grants,
    (select count(*) from public.submissions) submissions,
    (select count(*) from public.photos) photos,
    (select count(*) from public.gold_labels) labels,
    (select count(*) from public.photos p join public.submissions s on s.id=p.submission_id
        where exists(select 1 from public.grant_withdrawals w where w.grant_id=s.grant_id)) covered_photos,
    (select capture_open from public.service_state) capture_open,
    (select encode(extensions.digest(convert_to(jsonb_agg(to_jsonb(p) order by p.id)::text,'UTF8'),'sha256'),'hex') from public.photos p) photo_payload_sha256,
    pg_get_functiondef('public.finalize_submission(uuid)'::regprocedure) finalize_definition,
    pg_get_functiondef('public.apply_deletion_request(uuid)'::regprocedure) apply_definition,
    pg_get_functiondef('public.complete_deletion_request(uuid)'::regprocedure) complete_definition,
    (select array_agg(p.polname::text||':'||pg_get_expr(p.polqual,p.polrelid)||':'||coalesce(pg_get_expr(p.polwithcheck,p.polrelid),'') order by p.polname)
     from pg_policy p where p.polrelid='public.photos'::regclass) photo_policies,
    (select relacl::text from pg_class where oid='public.photos'::regclass) photo_acl,
    (select nspacl::text from pg_namespace where nspname='private') private_acl;
