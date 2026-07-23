create schema rehearsal_control;
create table rehearsal_control.sentinel(id integer primary key, value text not null);
insert into rehearsal_control.sentinel values(1,'synthetic unrelated state must survive');
insert into auth.users(id) values('ee000000-0000-4000-8000-000000000001'),('ee000000-0000-4000-8000-000000000002');
insert into public.contributors(id,auth_uid,handle) values
('dd000000-0000-4000-8000-000000000001','ee000000-0000-4000-8000-000000000001','synthetic-owner-one'),
('dd000000-0000-4000-8000-000000000002','ee000000-0000-4000-8000-000000000002','synthetic-owner-two');
insert into public.contribution_grants(id,contributor_id,terms_version,accepted_at,attribution_name) values
('ff000000-0000-4000-8000-000000000001','dd000000-0000-4000-8000-000000000001','2026-07-22-v1','2026-09-01','Anonymous soil contributor'),
('ff000000-0000-4000-8000-000000000002','dd000000-0000-4000-8000-000000000002','2026-07-22-v1','2026-09-01','Anonymous soil contributor');
insert into public.submissions(id,contributor_id,grant_id,geom_precise,captured_at,is_synthetic) values
('bb000000-0000-4000-8000-000000000001','dd000000-0000-4000-8000-000000000001','ff000000-0000-4000-8000-000000000001',extensions.st_geomfromtext('POINT EMPTY',4326),'2026-09-01',true),
('bb000000-0000-4000-8000-000000000002','dd000000-0000-4000-8000-000000000002','ff000000-0000-4000-8000-000000000002',extensions.st_geomfromtext('POINT EMPTY',4326),'2026-09-01',true);
insert into public.photos(submission_id,shot_type,storage_path)
select s.id,shot,'ee000000-0000-4000-8000-00000000000'||owner||'/'||s.id||'/'||shot||'/aa000000-0000-4000-8000-00000000000'||owner||'.jpg'
from (values (1,'bb000000-0000-4000-8000-000000000001'::uuid),(2,'bb000000-0000-4000-8000-000000000002'::uuid)) sample(owner,id)
join public.submissions s using(id) cross join (values('A'),('B')) shots(shot);
update public.qa_jobs set status='completed',completed_at=now();
insert into public.priors(submission_id,source,property,value,unit,depth_top_cm,depth_bottom_cm)
select id,'soilgrids','soc',1,'g/kg',0,5 from public.submissions;
insert into public.gold_labels(submission_id,lab_name,property,value,unit,depth_top_cm,depth_bottom_cm)
select id,'Synthetic local reference','soc',1,'g/kg',0,5 from public.submissions;
insert into public.predictions(submission_id,model_version,property,value,ci_lo,ci_hi,basis,unit)
select id,'synthetic-local-v1','soc',1,0,2,'prior','g/kg' from public.submissions;
insert into public.qa_events(submission_id,check_name,passed)
select id,'synthetic_local_check',true from public.submissions;
