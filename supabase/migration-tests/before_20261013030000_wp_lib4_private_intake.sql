-- Synthetic pre-migration snapshot only; no application rows or permissions are changed here.
-- Earlier fixtures already supply legacy grants, contributors, submissions and photos.
create table private.lib4b_test_baseline as
select
    (select count(*) from public.contributors) as contributors,
    (select count(*) from public.contribution_grants) as grants,
    (select count(*) from public.submissions) as submissions,
    (select count(*) from public.photos) as photos,
    (select count(*) from public.gold_labels) as labels,
    (select capture_open from public.service_state) as capture_open,
    pg_get_functiondef('public.finalize_submission(uuid)'::regprocedure) as finalize_definition,
    pg_get_functiondef('public.apply_deletion_request(uuid)'::regprocedure) as apply_definition,
    pg_get_functiondef('public.complete_deletion_request(uuid)'::regprocedure) as complete_definition,
    (select array_agg(p.polname::text || ':' || pg_get_expr(p.polqual,p.polrelid) || ':' ||
        coalesce(pg_get_expr(p.polwithcheck,p.polrelid),'') order by p.polname)
     from pg_policy p where p.polrelid='public.submissions'::regclass) as submission_policies,
    (select relacl::text from pg_class where oid='public.submissions'::regclass) as submission_acl,
    (select relacl::text from pg_class where oid='public.photos'::regclass) as photo_acl,
    (select nspacl::text from pg_namespace where nspname='private') as private_acl;
