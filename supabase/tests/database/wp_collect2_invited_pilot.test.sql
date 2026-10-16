-- Synthetic role proof: invitations are not a client claim and collection never publishes.
begin;
create extension if not exists pgtap with schema extensions;
set local search_path=public,extensions;
select no_plan();
-- The development seed may be open; prove the actual closed state explicitly.
update public.service_state set capture_open=false;
select public.set_library_intake_open(false);
select has_column('public','submissions','collection_scope','server-owned collection scope exists');
select is((select count(*) from pg_policy where polname in(
 'contributors_pilot_insert','contributors_pilot_update',
 'contribution_grants_pilot_insert','contribution_grants_pilot_update',
 'submissions_pilot_insert','submissions_pilot_update','photos_pilot_insert','photos_pilot_update',
 'incoming_photos_pilot_insert','incoming_photos_pilot_update') and not polpermissive),10::bigint,
 'all ten client INSERT/UPDATE restrictions are restrictive policies');

select is(public.collection_pilot_capabilities(),
    '{"version":"gsip-invited-pilot-v1","mode":"invited_private","member":false,"capture_open":false,"library_intake_available":false,"publication_held":true}'::jsonb,
    'no caller has a capability to write by default');
select ok(not has_table_privilege('authenticated','private.collection_pilot_members','select')
    and not has_table_privilege('authenticated','private.collection_pilot_members','insert')
    and not has_table_privilege('service_role','private.collection_pilot_members','update'),
    'invitation provisioning and lists are owner-admin only');
insert into auth.users(id,is_anonymous) values
 ('38200000-0000-4000-8000-000000000001',false),
 ('38200000-0000-4000-8000-000000000002',false),
 ('38200000-0000-4000-8000-000000000003',true);
insert into private.collection_pilot_members(auth_uid) values
 ('38200000-0000-4000-8000-000000000001'),('38200000-0000-4000-8000-000000000003');
insert into public.terms_versions(version,published_at) values('collect2-synthetic',now()-interval '1 day');
update public.service_state set capture_open=true;
select public.set_library_intake_open(true);
set local role anon;
select is(public.collection_pilot_capabilities()->>'member','false','anonymous caller sees no membership');
select throws_ok($$select public.collection_publication_capabilities()$$,'42501',null,'anonymous publication authority is refused');
reset role;
set local role authenticated;
set local "request.jwt.claims"='{"sub":"38200000-0000-4000-8000-000000000002","role":"authenticated"}';
select is(public.collection_pilot_capabilities()->>'member','false','permanent account is not automatically invited');
select throws_ok($$insert into public.contributors(auth_uid,handle) values('38200000-0000-4000-8000-000000000002','nonmember-fixture')$$,'42501',null,'uninvited account cannot enroll a contributor');
set local "request.jwt.claims"='{"sub":"38200000-0000-4000-8000-000000000003","role":"authenticated"}';
select is(public.collection_pilot_capabilities()->>'member','false','an invited anonymous auth user is still refused');
set local "request.jwt.claims"='{"sub":"38200000-0000-4000-8000-000000000001","role":"authenticated"}';
select is(public.collection_pilot_capabilities(),
 '{"version":"gsip-invited-pilot-v1","mode":"invited_private","member":true,"capture_open":true,"library_intake_available":true,"publication_held":true}'::jsonb,
 'invited permanent identity with both gates is admitted without publication');
select lives_ok($$insert into public.contributors(auth_uid,handle) values('38200000-0000-4000-8000-000000000001','invited-synthetic')$$,'invited caller creates their own contributor');
select lives_ok($$insert into public.contribution_grants(id,contributor_id,terms_version,accepted_at,attribution_name) values('48200000-0000-4000-8000-000000000001',(select id from public.contributors where auth_uid='38200000-0000-4000-8000-000000000001'),'collect2-synthetic',now(),'Anonymous soil contributor')$$,'invited caller creates an immutable grant');
select lives_ok($$insert into public.submissions(id,contributor_id,grant_id,geom_precise,captured_at) values('58200000-0000-4000-8000-000000000001',(select id from public.contributors where auth_uid='38200000-0000-4000-8000-000000000001'),'48200000-0000-4000-8000-000000000001','SRID=4326;POINT EMPTY',now())$$,'invited caller creates a private observation');
select is((select collection_scope from public.submissions where id='58200000-0000-4000-8000-000000000001'),'private_pilot','ordinary observation is classified without optional library context');
select throws_ok($$insert into public.submissions(contributor_id,grant_id,geom_precise,captured_at,collection_scope) values((select id from public.contributors where auth_uid='38200000-0000-4000-8000-000000000001'),'48200000-0000-4000-8000-000000000001','SRID=4326;POINT EMPTY',now(),'legacy')$$,'42501',null,'client cannot supply the authority field');
select lives_ok($$insert into public.photos(submission_id,shot_type,storage_path) values('58200000-0000-4000-8000-000000000001','A','38200000-0000-4000-8000-000000000001/58200000-0000-4000-8000-000000000001/A/68200000-0000-4000-8000-000000000001.jpg'),('58200000-0000-4000-8000-000000000001','B','38200000-0000-4000-8000-000000000001/58200000-0000-4000-8000-000000000001/B/68200000-0000-4000-8000-000000000002.jpg')$$,'invited caller links the required private A and B photos');
select lives_ok($$select public.finalize_submission('58200000-0000-4000-8000-000000000001')$$,'invited owner can finalize the required set');
reset role;
set local role service_role;
select lives_ok($$insert into public.submissions(id,contributor_id,grant_id,geom_precise,captured_at,collection_scope) values('58200000-0000-4000-8000-000000000002',(select id from public.contributors where auth_uid='38200000-0000-4000-8000-000000000001'),'48200000-0000-4000-8000-000000000001','SRID=4326;POINT EMPTY',now(),'legacy')$$,'trusted service insert remains private even when claiming legacy');
select is((select collection_scope from public.submissions where id='58200000-0000-4000-8000-000000000002'),'private_pilot','service insert cannot choose public eligibility');
reset role;
update private.collection_pilot_members set revoked_at=now() where auth_uid='38200000-0000-4000-8000-000000000001';
set local role authenticated;
select is(public.collection_pilot_capabilities()->>'member','false','revocation changes current capabilities');
select throws_ok($$insert into public.contribution_grants(contributor_id,terms_version,accepted_at,attribution_name) values((select id from public.contributors where auth_uid='38200000-0000-4000-8000-000000000001'),'collect2-synthetic',now(),'Anonymous soil contributor')$$,'42501',null,'revoked member cannot create another grant');
select throws_ok($$insert into public.submissions(contributor_id,grant_id,geom_precise,captured_at) values((select id from public.contributors where auth_uid='38200000-0000-4000-8000-000000000001'),'48200000-0000-4000-8000-000000000001','SRID=4326;POINT EMPTY',now())$$,'42501',null,'revoked member cannot bypass the form with a direct observation insert');

select throws_ok($$insert into public.photos(submission_id,shot_type,storage_path) values('58200000-0000-4000-8000-000000000001','C','38200000-0000-4000-8000-000000000001/58200000-0000-4000-8000-000000000001/C/68200000-0000-4000-8000-000000000003.jpg')$$,'42501',null,'revoked member cannot add a photo');
select throws_ok($$insert into storage.objects(bucket_id,name,owner) values('incoming-photos','38200000-0000-4000-8000-000000000001/58200000-0000-4000-8000-000000000001/C/68200000-0000-4000-8000-000000000003.jpg','38200000-0000-4000-8000-000000000001')$$,'42501',null,'revoked member cannot upload directly');
select throws_ok($$select public.finalize_submission('58200000-0000-4000-8000-000000000001')$$,'42501',null,'privileged finalization retry cannot bypass revocation');
select throws_ok($$select public.record_library_intake('{"schema_version":"gsip-library-intake-v1","intake_id":"78200000-0000-4000-8000-000000000001","node_id":"88200000-0000-4000-8000-000000000001","sample_id":"98200000-0000-4000-8000-000000000001","submission_id":"58200000-0000-4000-8000-000000000001","protocol_version":"gsip-capture-v1","context":{"depth_top_cm":0,"depth_bottom_cm":20,"condition":"dry"},"instrument_declaration":null}'::jsonb)$$,'42501',null,'privileged library intake cannot bypass revocation');
reset role;
update private.collection_pilot_members set revoked_at=null where auth_uid='38200000-0000-4000-8000-000000000001';
select public.set_library_intake_open(false);
set local role authenticated;
select throws_ok($$select public.finalize_submission('58200000-0000-4000-8000-000000000001')$$,'LI001',null,'capture flag alone cannot enable privileged finalization');
select throws_ok($$insert into public.contribution_grants(contributor_id,terms_version,accepted_at,attribution_name) values((select id from public.contributors where auth_uid='38200000-0000-4000-8000-000000000001'),'collect2-synthetic',now(),'Anonymous soil contributor')$$,'LI001',null,'capture flag alone cannot admit a grant');
reset role;
select public.set_library_intake_open(true);
update public.service_state set capture_open=false;
set local role authenticated;
select throws_ok($$select public.finalize_submission('58200000-0000-4000-8000-000000000001')$$,'LI001',null,'library flag alone cannot finalize');
reset role;
update private.collection_pilot_members set revoked_at=now() where auth_uid='38200000-0000-4000-8000-000000000001';
select public.set_library_intake_open(false);
set local role authenticated;
select lives_ok($$insert into public.deletion_requests(contributor_id,kind) values((select id from public.contributors where auth_uid='38200000-0000-4000-8000-000000000001'),'withdraw_contributions')$$,'withdrawal survives revoked invitation and closed intake');
select is((select count(*) from public.submissions where id='58200000-0000-4000-8000-000000000001'),1::bigint,'owner reads remain available for rights handling');
reset role;
set local role service_role;
select is(public.collection_publication_capabilities(),'{"version":"gsip-collection-publication-v1","publication_allowed":false}'::jsonb,'service publication contract is fixed false');
select throws_ok($$update public.submissions set collection_scope='legacy' where id='58200000-0000-4000-8000-000000000001'$$,'23514',null,'service role cannot promote pilot classification');
select throws_ok($$select public.refresh_public_h3_cells('[]'::jsonb)$$,'CP001',null,'even an empty refresh RPC is held');
select throws_ok($$insert into public.h3_cells(h3_index,resolution,n_submissions,n_contributors,latest_submission_date) values('882bac94b5fffff',8,3,3,current_date)$$,'CP001',null,'service role cannot directly publish cells');
select throws_ok($$insert into public.dataset_releases(version,rows,photos) values('2026-10-16',3,0)$$,'CP001',null,'service role cannot record a public release');
select lives_ok($$delete from public.h3_cells where true$$,'deletion of public exposure remains possible');
select is((select deleted_submissions from public.apply_deletion_request((select request_id from public.claim_deletion_request()))),2,'rights worker removes pilot payloads with invitation revoked and both intake gates closed');
select lives_ok($$select public.complete_deletion_request((select id from public.deletion_requests where contributor_id=(select id from public.contributors where auth_uid='38200000-0000-4000-8000-000000000001') and status='processing'))$$,'rights worker completes while collection and publication remain held');

reset role;
select ok(not exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('public','private') and p.proname ~ 'collection.*(set|enable|open)' ),'no collection publication activation operation exists');
select * from finish();
rollback;
