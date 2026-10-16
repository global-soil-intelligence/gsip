-- Snapshot populated synthetic prior schema. No gate, account or publication activation.
insert into public.dataset_releases(version,rows,photos) values('2026-10-15',3,0);
insert into public.h3_cells(h3_index,resolution,n_submissions,n_contributors,latest_submission_date)
values('882bac94b5fffff',8,3,3,'2026-10-15');
create table private.collect2_test_baseline as select
 (select count(*) from public.h3_cells) cells,
 (select count(*) from public.dataset_releases) releases,
 (select count(*) from public.contributors) contributors,
 (select count(*) from public.contribution_grants) grants,
 (select count(*) from public.submissions) submissions,
 (select count(*) from public.photos) photos,
 (select count(*) from public.gold_labels) labels,
 (select capture_open from public.service_state) capture_open,
 (select intake_open from private.library_service_state) intake_open,
 (select encode(extensions.digest(convert_to(jsonb_agg(to_jsonb(s) order by s.id)::text,'UTF8'),'sha256'),'hex') from public.submissions s) submission_sha256,
 pg_get_functiondef('public.apply_deletion_request(uuid)'::regprocedure) apply_definition,
 pg_get_functiondef('public.complete_deletion_request(uuid)'::regprocedure) complete_definition;
