-- Synthetic EMPTY geometry only; no images, coordinates, model approval or live tokens.
begin;
create extension if not exists pgtap with schema extensions;
set local search_path=public,extensions;
select no_plan();
create function pg_temp.id(p_prefix text,p_index integer) returns uuid language sql immutable as $$
    select (p_prefix||'0000-0000-4000-8000-'||lpad(p_index::text,12,'0'))::uuid;
$$;
create function pg_temp.token(p_index integer) returns text language sql immutable as $$
    select encode(extensions.digest(convert_to('fictional-private-photo-review-'||p_index,'UTF8'),'sha256'),'hex');
$$;
create function pg_temp.seed(p_index integer,p_owner integer default 1) returns void language plpgsql as $$
declare uid uuid:=pg_temp.id('36fa',p_owner); sub uuid:=pg_temp.id('46fa',p_index); i integer; shot text;
begin
    insert into public.submissions(id,contributor_id,grant_id,geom_precise,captured_at,land_cover,surface_condition,disturbed,device_model,finalized_at)
    values(sub,pg_temp.id('26fa',p_owner),pg_temp.id('66fa',p_owner),'SRID=4326;POINT EMPTY',now(),'bare','dry',false,'synthetic fixture',now());
    for i in 1..3 loop
        shot:=substring('ABC',i,1);
        insert into public.photos(id,submission_id,shot_type,storage_path,qa_status)
        values(pg_temp.id('56fa',p_index*10+i),sub,shot,uid::text||'/'||sub::text||'/'||shot||'/'||pg_temp.id('86fa',p_index*10+i)::text||'.jpg','pass');
    end loop;
    -- Fictional format-only cell strings satisfy the legacy QA table constraint;
    -- they describe no location and are never released by this database test.
    update public.submissions set status='qa_pass',h3_r8='88'||lpad(p_index::text,13,'0'),h3_r6='86'||lpad(p_index::text,13,'0') where id=sub;
end;
$$;
create function pg_temp.content(p_photo uuid,p_expected bigint default 0,p_digest text default repeat('a',64))
returns jsonb language sql immutable as $$
    select jsonb_build_object('schema_version','gsip-photo-privacy-v1','photo_id',p_photo,'expected_content_revision',p_expected,
        'sanitized_sha256',p_digest,'byte_count',1024,'sanitizer_version','synthetic-sanitizer-v1');
$$;
create function pg_temp.screen(p_lease jsonb,p_result text default 'pass') returns jsonb language sql volatile as $$
    select jsonb_build_object('schema_version','gsip-photo-privacy-v1','request_id',gen_random_uuid(),'photo_id',p_lease->'photo_id',
        'content_revision',p_lease->'content_revision','policy_id',p_lease->'policy_id','policy_revision',p_lease->'policy_revision',
        'sanitized_sha256',p_lease->'sanitized_sha256','screening_version',p_lease->'screening_version',
        'calibration_version',p_lease->'calibration_version','detector_manifest_sha256',p_lease->'detector_manifest_sha256',
        'calibration_manifest_sha256',p_lease->'calibration_manifest_sha256','face',jsonb_build_object('result','pass','candidates',0),
        'scene_text',jsonb_build_object('result',p_result,'candidates',case when p_result='flag' then 1 else 0 end),
        'card_exception_used',false,'card_exclusion',null);
$$;
create function pg_temp.review(p_receipt jsonb,p_decision text default 'clear') returns jsonb language sql volatile as $$
    select (p_receipt-array['status']::text[])||jsonb_build_object('schema_version','gsip-photo-privacy-v1','review_id',gen_random_uuid(),
        'decision',p_decision,'reason',case p_decision when 'clear' then 'false_positive' else 'privacy_risk' end);
$$;
create function pg_temp.export_request(p_receipt jsonb) returns jsonb language sql immutable as $$
    select jsonb_build_object('schema_version','gsip-photo-privacy-v1','photos',jsonb_build_array(p_receipt-array['status']::text[]));
$$;
create temp table state(photo_id uuid primary key,lease jsonb,receipt jsonb,review jsonb);
insert into public.terms_versions(version,published_at) values('6fa-synthetic',now()-interval '100 days');
insert into auth.users(id) select pg_temp.id('36fa',i) from generate_series(1,5) i;
insert into public.contributors(id,auth_uid,handle) select pg_temp.id('26fa',i),pg_temp.id('36fa',i),'privacy-synthetic-'||i from generate_series(1,5) i;
insert into public.contribution_grants(id,contributor_id,terms_version,accepted_at,attribution_name)
    select pg_temp.id('66fa',i),pg_temp.id('26fa',i),'6fa-synthetic',now()-interval '20 days','Anonymous soil contributor' from generate_series(1,5) i;
select pg_temp.seed(1);

select ok((select count(*)=8 and bool_and(c.relrowsecurity) from pg_class c join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='private' and c.relname like 'photo_privacy_%' and c.relkind='r'),'all eight private tables have RLS');
select is((select count(*) from pg_policy p join pg_class c on c.oid=p.polrelid join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='private' and c.relname like 'photo_privacy_%' and not p.polpermissive),8::bigint,'all eight restrictive client-deny policies exist');
select ok((select count(*)=9 and bool_and(not p.prosecdef and p.prosqlbody is not null and p.proconfig=array['search_path=""'])
    from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname like '%photo_privacy%'),
    'exact nine public functions are empty-search-path bound invoker dispatch');
select ok(not has_schema_privilege('anon','private','usage') and not has_schema_privilege('authenticated','private','usage')
    and not has_schema_privilege('service_role','private','usage'),'private schema remains inaccessible by name for all API roles');
select ok((select bool_and(not has_table_privilege(role,c.oid,'select,insert,update,delete,truncate'))
    from pg_class c join pg_namespace n on n.oid=c.relnamespace cross join unnest(array['anon','authenticated','service_role']) role
    where n.nspname='private' and c.relname like 'photo_privacy_%' and c.relkind='r'),'no API role has direct private table privileges');
select is((select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='private'
    and p.proname like '%photo_privacy%' and has_function_privilege('service_role',p.oid,'execute')),9::bigint,'only the exact nine private dispatch bodies grant service execution');
select ok((select bool_and(not has_function_privilege(role,p.oid,'execute')) from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    cross join unnest(array['anon','authenticated']) role where n.nspname='public' and p.proname like '%photo_privacy%'),
    'every screening RPC refuses both client roles');
set local role anon;
select throws_ok($$select public.photo_privacy_capabilities()$$,'42501',null,'anon cannot probe private configuration');
reset role;
set local role authenticated;
select throws_ok($$select public.record_photo_privacy_content(pg_temp.content(pg_temp.id('56fa',11)))$$,'42501',null,'authenticated cannot register a hash');
select throws_ok($$select public.review_photo_privacy(pg_temp.token(1),'{}')$$,'42501',null,'authenticated cannot clear or review');
reset role;
set local role service_role;
set local "request.jwt.claims"='{"role":"service_role"}';
select throws_ok($$select * from private.photo_privacy_operators$$,'42501',null,'worker service key cannot read token allowlist');
select throws_ok($$update private.photo_privacy_state set publication_open=true$$,'42501',null,'service key cannot open publication');
select throws_ok($$insert into private.photo_privacy_operators values(gen_random_uuid(),pg_temp.id('36fa',4),repeat('a',64),true)$$,
    '42501',null,'service key cannot self-provision a reviewer');
set local "request.jwt.claims"='{}';
select throws_ok($$select public.photo_privacy_capabilities()$$,'42501',null,'execute privilege without service claim gives no authority');
set local "request.jwt.claims"='{"role":"service_role"}';
select ok(not(public.photo_privacy_capabilities()->>'publication_open')::boolean,'initial global publication gate is closed');
select is(public.photo_privacy_capabilities()->'policy_id','null'::jsonb,'initial policy is explicitly unknown');
select is(public.claim_photo_privacy_job(),null::jsonb,'no policy means no work lease');
select is(public.photo_privacy_receipt(pg_temp.id('56fa',11))->>'status','pending','existing QA pass is never privacy clearance');
select is(public.photo_privacy_receipt(pg_temp.id('56fa',11))->'sanitized_sha256','null'::jsonb,'migration/new photo infers no byte digest');
select is(public.record_photo_privacy_content(pg_temp.content(pg_temp.id('56fa',11)))->>'status','registered','trusted service registers actual content tuple');
select is(public.record_photo_privacy_content(pg_temp.content(pg_temp.id('56fa',11)))->>'status','already_current','lost registration response retries with stale revision');
select is(public.record_photo_privacy_content(jsonb_set(pg_temp.content(pg_temp.id('56fa',11)),'{photo_id}',to_jsonb(upper(pg_temp.id('56fa',11)::text))))->>'status',
    'already_current','UUID case normalizes on exact retry');
select throws_ok($$select public.record_photo_privacy_content(pg_temp.content(pg_temp.id('56fa',11),0,repeat('b',64)))$$,'PP002',null,'changed content requires compare-and-set revision');
select throws_ok(format('select public.record_photo_privacy_content(%L::jsonb)',bad),'22023',null,description) from (values
    (pg_temp.content(pg_temp.id('56fa',11))||'{"status":"clear"}'::jsonb,'client-style authority field is refused'),
    (pg_temp.content(pg_temp.id('56fa',11))||'{"reviewer_id":"fictional"}'::jsonb,'caller reviewer identity is refused'),
    (jsonb_set(pg_temp.content(pg_temp.id('56fa',11)),'{byte_count}','true'),'boolean byte count is refused'),
    (jsonb_set(pg_temp.content(pg_temp.id('56fa',11)),'{byte_count}','1.5'),'fractional byte count is refused'),
    (jsonb_set(pg_temp.content(pg_temp.id('56fa',11)),'{byte_count}','10485761'),'oversized object is refused'),
    (jsonb_set(pg_temp.content(pg_temp.id('56fa',11)),'{sanitized_sha256}',to_jsonb(repeat('A',64))),'uppercase digest is refused'),
    (jsonb_set(pg_temp.content(pg_temp.id('56fa',11)),'{sanitizer_version}',to_jsonb(repeat('x',17000))),'oversized normalized request is refused')
) cases(bad,description);
reset role;
insert into private.photo_privacy_policies values(pg_temp.id('16fa',1),'synthetic-screen-v1','unapproved-synthetic-calibration-v1',
    repeat('d',64),repeat('e',64),'synthetic-margin-v1','{"face":"full-frame","scene_text":"full-frame-card-exception","multiscale":true,"thresholds":{}}',null);
update private.photo_privacy_state set policy_id=pg_temp.id('16fa',1);
select throws_ok($$update private.photo_privacy_state set implementation_deployed=true,publication_open=true$$,'55000',null,'unapproved benchmark policy cannot open gate');
insert into private.photo_privacy_operators(operator_id,auth_uid,token_sha256,active)
    select pg_temp.id('96fa',i),pg_temp.id('36fa',i+3),encode(extensions.digest(convert_to(pg_temp.token(i),'UTF8'),'sha256'),'hex'),true from generate_series(1,2) i;
set local role service_role;
select is(public.record_photo_privacy_content(pg_temp.content(pg_temp.id('56fa',12)))->>'status','registered','shot B digest registers');
select is(public.record_photo_privacy_content(pg_temp.content(pg_temp.id('56fa',13)))->>'status','registered','optional shot C digest registers');
reset role;
-- Capture three leases/receipts without exposing private payloads through pgTAP stdout.
insert into state(photo_id,lease) select (l->>'photo_id')::uuid,l from (select public.claim_photo_privacy_job() l) q;
update state set receipt=pg_temp.screen(lease);
select is((select (lease->>'attempt')::integer from state),1,'first lease counts one bounded attempt');
select ok((select (lease->>'lease_expires_at')::timestamptz<=clock_timestamp()+interval '300 seconds' from state),'lease expires within 300 seconds');
select is(public.complete_photo_privacy_job((select (lease->>'lease_id')::uuid from state),(select receipt from state))->>'status','clear','both supported passes produce private clear');
select is(public.complete_photo_privacy_job((select (lease->>'lease_id')::uuid from state),(select receipt from state))->>'status','clear','lost completion response exact retry is idempotent');
update private.photo_privacy_jobs set lease_expires_at=clock_timestamp()-interval '1 second' where lease_id=(select (lease->>'lease_id')::uuid from state);
select is(public.complete_photo_privacy_job((select (lease->>'lease_id')::uuid from state),jsonb_set((select receipt from state),'{request_id}',to_jsonb(upper((select receipt->>'request_id' from state)))))->>'status','clear','completed expired lease permits only exact canonical UUID retry');

select throws_ok($$select public.complete_photo_privacy_job((select (lease->>'lease_id')::uuid from state),
    jsonb_set((select receipt from state),'{face,candidates}','1'))$$,'22023',null,'pass with candidates is structurally invalid');
select throws_ok($$select public.complete_photo_privacy_job((select (lease->>'lease_id')::uuid from state),
    jsonb_set((select receipt from state),'{request_id}',to_jsonb(gen_random_uuid()::text)))$$,'PP003',null,'changed completion request ID cannot rewrite same lease');
select ok(not(public.authorize_photo_privacy_export(pg_temp.export_request(public.photo_privacy_receipt(pg_temp.id('56fa',11))))->'authorizations'->0->>'authorized')::boolean,
    'private clear cannot bypass closed global gate');
insert into state(photo_id,lease) select (l->>'photo_id')::uuid,l from (select public.claim_photo_privacy_job() l) q;
update state set receipt=pg_temp.screen(lease,'flag') where photo_id=pg_temp.id('56fa',12);
select is(public.complete_photo_privacy_job((select (lease->>'lease_id')::uuid from state where photo_id=pg_temp.id('56fa',12)),
    (select receipt from state where photo_id=pg_temp.id('56fa',12)))->>'status','review','scene text candidate flags only its own photo');
select is((select status from public.submissions where id=pg_temp.id('46fa',1)),'qa_pass','privacy flag does not alter settlement');
select throws_ok($$select public.review_photo_privacy(pg_temp.token(99),pg_temp.review(public.photo_privacy_receipt(pg_temp.id('56fa',12))))$$,
    '42501',null,'service key without personal token cannot clear');
select throws_ok($$select public.review_photo_privacy(repeat('x',20000),pg_temp.review(public.photo_privacy_receipt(pg_temp.id('56fa',12))))$$,
    '42501',null,'oversized malformed operator token gets generic authorization refusal');
update state set review=pg_temp.review(public.photo_privacy_receipt(photo_id)) where photo_id=pg_temp.id('56fa',12);
select is(public.review_photo_privacy(pg_temp.token(1),(select review from state where photo_id=pg_temp.id('56fa',12)))->>'status','clear','live personal operator clears supported false positive');
select is(public.review_photo_privacy(pg_temp.token(1),(select review from state where photo_id=pg_temp.id('56fa',12)))->>'status','clear','same reviewer lost response retry is idempotent');
select throws_ok($$select public.review_photo_privacy(pg_temp.token(2),(select review from state where photo_id=pg_temp.id('56fa',12)))$$,
    'PP003',null,'a different operator cannot claim the same review UUID');
select is((select operator_id from private.photo_privacy_reviews where photo_id=pg_temp.id('56fa',12)),pg_temp.id('96fa',1),'audit identity is derived from live allowlist');
select throws_ok($$update private.photo_privacy_reviews set decision='withhold'$$,'PP003',null,'human audit cannot be overwritten');
select throws_ok($$delete from private.photo_privacy_screens$$,'55000',null,'screen deletion requires opaque refusal record');
select throws_ok($$truncate private.photo_privacy_reviews$$,null,null,'audit cannot be truncated');
insert into state(photo_id,lease) select (l->>'photo_id')::uuid,l from (select public.claim_photo_privacy_job() l) q;
update state set review=pg_temp.review(public.photo_privacy_receipt(photo_id),'withhold') where photo_id=pg_temp.id('56fa',13);
select is(public.review_photo_privacy(pg_temp.token(1),(select review from state where photo_id=pg_temp.id('56fa',13)))->>'status','withheld','operator permanently withholds known processing content');
select throws_ok($$select public.complete_photo_privacy_job((select (lease->>'lease_id')::uuid from state where photo_id=pg_temp.id('56fa',13)),
    pg_temp.screen((select lease from state where photo_id=pg_temp.id('56fa',13))))$$,'PP002',null,'late detector cannot reverse permanent withhold');
select throws_ok($$select public.fail_photo_privacy_job((select (lease->>'lease_id')::uuid from state where photo_id=pg_temp.id('56fa',13)),'storage')$$,
    'PP002',null,'late failure cannot reset permanent withhold');
select throws_ok($$select public.review_photo_privacy(pg_temp.token(1),pg_temp.review(public.photo_privacy_receipt(pg_temp.id('56fa',13))))$$,
    'PP002',null,'human clear cannot reverse permanent withhold');
select is(public.record_photo_privacy_content(pg_temp.content(pg_temp.id('56fa',13),1,repeat('b',64)))->>'status','registered','replacement bytes advance permanent-withheld identity revision');
select is(public.photo_privacy_receipt(pg_temp.id('56fa',13))->>'status','withheld','replacement bytes preserve permanent withhold');
update public.photos set storage_path=pg_temp.id('36fa',1)::text||'/'||pg_temp.id('46fa',1)::text||'/C/'||gen_random_uuid()::text||'.jpg' where id=pg_temp.id('56fa',13);
select is(public.photo_privacy_receipt(pg_temp.id('56fa',13))->>'status','withheld','source path replacement cannot reset permanent withholding');
select is(public.photo_privacy_receipt(pg_temp.id('56fa',13))->'sanitized_sha256','null'::jsonb,'source path replacement invalidates exact-byte digest');
select is(public.record_photo_privacy_content(pg_temp.content(pg_temp.id('56fa',13),3,repeat('c',64)))->>'status','registered','replacement path must register its new exact bytes');
select throws_ok($$update public.photos set shot_type='A',storage_path=pg_temp.id('36fa',1)::text||'/'||pg_temp.id('46fa',1)::text||'/A/'||gen_random_uuid()::text||'.jpg' where id=pg_temp.id('56fa',13)$$,'PP003',null,'source shot identity cannot be rebound');

update private.photo_privacy_policies set owner_approval_sha256=repeat('f',64) where policy_id=pg_temp.id('16fa',1);
update private.photo_privacy_state set implementation_deployed=true,publication_open=true;
select is(public.photo_privacy_receipt(pg_temp.id('56fa',12))->>'status','pending','gate/policy revision invalidates old human clearance');
select is(public.photo_privacy_receipt(pg_temp.id('56fa',13))->>'status','withheld','gate/policy revision preserves permanent withhold');
select ok(not(public.authorize_photo_privacy_export(pg_temp.export_request(public.photo_privacy_receipt(pg_temp.id('56fa',12))))->'authorizations'->0->>'authorized')::boolean,
    'fresh policy cannot authorize old screen/manual clearance');
create temp table retired_ids as select review->>'review_id' review_id from state where photo_id=pg_temp.id('56fa',12);
-- Re-screen A/B under the exact approved synthetic policy; no detector calibration is claimed.
delete from state where photo_id<>pg_temp.id('56fa',13);
insert into state(photo_id,lease) select (l->>'photo_id')::uuid,l from (select public.claim_photo_privacy_job() l) q;
update state set receipt=pg_temp.screen(lease) where photo_id=pg_temp.id('56fa',11);
select is(public.complete_photo_privacy_job((select (lease->>'lease_id')::uuid from state where photo_id=pg_temp.id('56fa',11)),
    (select receipt from state where photo_id=pg_temp.id('56fa',11)))->>'status','clear','new-generation A completes');
insert into state(photo_id,lease) select (l->>'photo_id')::uuid,l from (select public.claim_photo_privacy_job() l) q;
update state set receipt=pg_temp.screen(lease) where photo_id=pg_temp.id('56fa',12);
select is(public.complete_photo_privacy_job((select (lease->>'lease_id')::uuid from state where photo_id=pg_temp.id('56fa',12)),
    (select receipt from state where photo_id=pg_temp.id('56fa',12)))->>'status','clear','new-generation B completes');
select ok((public.authorize_photo_privacy_export(pg_temp.export_request(public.photo_privacy_receipt(pg_temp.id('56fa',11))))->'authorizations'->0->>'authorized')::boolean,
    'exact current clear bytes and all existing rights/QA/attribution gates authorize');
select ok(not(public.authorize_photo_privacy_export(pg_temp.export_request(jsonb_set(public.photo_privacy_receipt(pg_temp.id('56fa',11)),
    '{sanitized_sha256}',to_jsonb(repeat('b',64)))))->'authorizations'->0->>'authorized')::boolean,'actual loaded byte mismatch is refused');
select throws_ok($$select public.authorize_photo_privacy_export(jsonb_build_object('schema_version','gsip-photo-privacy-v1',
    'photos',jsonb_build_array(public.photo_privacy_receipt(pg_temp.id('56fa',11)),public.photo_privacy_receipt(pg_temp.id('56fa',11)))))$$,
    '22023',null,'duplicate/extra-field export entries are rejected');
select is(public.claim_photo_privacy_job(),null::jsonb,'clear and permanently withheld photos are not claimable');
select throws_ok($$update private.photo_privacy_tombstones set reason='withdrawn'$$,null,null,'permanent refusal records are immutable');
select throws_ok($$truncate private.photo_privacy_tombstones$$,null,null,'permanent refusal records are untruncatable');
update private.photo_privacy_operators set active=false where operator_id=pg_temp.id('96fa',1);
select throws_ok($$select public.photo_privacy_review_context(pg_temp.id('56fa',11),pg_temp.token(1))$$,'42501',null,'revoked operator cannot load review context');
delete from auth.users where id=pg_temp.id('36fa',5);
select throws_ok($$select public.photo_privacy_review_context(pg_temp.id('56fa',11),pg_temp.token(2))$$,'42501',null,'deleted auth user cannot review');
select is((select count(*) from private.photo_privacy_operators where operator_id=pg_temp.id('96fa',2)),0::bigint,'auth deletion cascades credential mapping');
select is((select count(*) from private.photo_privacy_reviews where photo_id=pg_temp.id('56fa',12)),1::bigint,'live auth erasure does not destroy prior derived audit');
insert into public.grant_withdrawals(grant_id,reason) values(pg_temp.id('66fa',1),'contributor_request');
select is((select count(*) from private.photo_privacy_content where contributor_id=pg_temp.id('26fa',1)),0::bigint,'withdrawal atomically erases current private content');
select is((select count(*) from private.photo_privacy_jobs where contributor_id=pg_temp.id('26fa',1)),0::bigint,'withdrawal atomically erases jobs/leases');
select is((select count(*) from private.photo_privacy_screens where contributor_id=pg_temp.id('26fa',1)),0::bigint,'withdrawal atomically erases detector payload');
select is((select count(*) from private.photo_privacy_reviews where contributor_id=pg_temp.id('26fa',1)),0::bigint,'withdrawal atomically erases human audit payload');
select is((select count(*) from private.photo_privacy_tombstones where identity_kind='photo' and grant_id=pg_temp.id('66fa',1)),3::bigint,'opaque source refusals remain after erasure');
select throws_ok($$select public.record_photo_privacy_content(pg_temp.content(pg_temp.id('56fa',11),1))$$,'WD001',null,'registration cannot revive withdrawn payload');
select is(public.photo_privacy_receipt(pg_temp.id('56fa',11)),null::jsonb,'withdrawn receipt reveals no private state');
select ok(not(public.authorize_photo_privacy_export(pg_temp.export_request((select receipt-array['schema_version','request_id','detector_manifest_sha256',
    'calibration_manifest_sha256','face','scene_text','card_exception_used','card_exclusion']::text[] from state where photo_id=pg_temp.id('56fa',11))))->'authorizations'->0->>'authorized')::boolean,
    'previous exact tuple cannot authorize after withdrawal');

-- New isolated owner; remove unused shots to make queue selection deterministic.
select pg_temp.seed(2,2);
delete from public.photos where id in (pg_temp.id('56fa',22),pg_temp.id('56fa',23));
select is((select count(*) from private.photo_privacy_content where photo_id in (pg_temp.id('56fa',22),pg_temp.id('56fa',23))),0::bigint,'direct source delete erases private payload before cascade');
select throws_ok($$insert into public.photos(id,submission_id,shot_type,storage_path) values(pg_temp.id('56fa',22),pg_temp.id('46fa',2),'B',pg_temp.id('36fa',2)::text||'/'||pg_temp.id('46fa',2)::text||'/B/'||gen_random_uuid()::text||'.jpg')$$,
    'WD001',null,'a deleted source UUID cannot be imported under a fresh path');
select is(public.record_photo_privacy_content(pg_temp.content(pg_temp.id('56fa',21)))->>'status','registered','new owner content is independent');
insert into state(photo_id,lease) select (l->>'photo_id')::uuid,l from (select public.claim_photo_privacy_job() l) q;
update state set receipt=pg_temp.screen(lease)||jsonb_build_object('card_exception_used',true,'card_exclusion',jsonb_build_object(
    'image_width',100,'image_height',100,'mask_sha256',repeat('c',64),'excluded_pixels',500,'margin_version','synthetic-margin-v1')) where photo_id=pg_temp.id('56fa',21);
select throws_ok(format('select public.complete_photo_privacy_job(%L::uuid,%L::jsonb)',(select lease->>'lease_id' from state where photo_id=pg_temp.id('56fa',21)),bad),'22023',null,description)
from (select jsonb_set(receipt,path,value) bad,description from state cross join (values
    ('{card_exception_used}'::text[],'false'::jsonb,'unused card exception cannot retain evidence'),
    ('{card_exception_used}'::text[],'1'::jsonb,'card exception requires strict boolean'),
    ('{card_exclusion,image_width}'::text[],'true'::jsonb,'mask dimension requires strict integer'),
    ('{card_exclusion,image_width}'::text[],'40000001'::jsonb,'mask dimensions remain bounded'),
    ('{card_exclusion,excluded_pixels}'::text[],'10000'::jsonb,'card exception cannot exclude the full image'),
    ('{card_exclusion,excluded_pixels}'::text[],'0'::jsonb,'card exception must exclude a nonempty region'),
    ('{card_exclusion,ocr}'::text[],'"private text"'::jsonb,'mask evidence cannot contain OCR'),
    ('{face,result}'::text[],'"unknown"'::jsonb,'detector outcomes are finite'),
    ('{scene_text,candidates}'::text[],'10001'::jsonb,'candidate counts remain bounded')
) fields(path,value,description) where photo_id=pg_temp.id('56fa',21)) cases;
select throws_ok($$select public.complete_photo_privacy_job((select (lease->>'lease_id')::uuid from state where photo_id=pg_temp.id('56fa',21)),jsonb_set((select receipt from state where photo_id=pg_temp.id('56fa',21)),'{card_exclusion,margin_version}','"stale-margin"'))$$,'PP002',null,'card exclusion evidence must bind the selected margin version');
select throws_ok($$select public.complete_photo_privacy_job((select (lease->>'lease_id')::uuid from state where photo_id=pg_temp.id('56fa',21)),jsonb_set((select receipt from state where photo_id=pg_temp.id('56fa',21)),'{request_id}',(select receipt->'request_id' from state where photo_id=pg_temp.id('56fa',11))))$$,'PP003',null,'erased screen UUID remains retired for new photo and bytes');
select is(public.complete_photo_privacy_job((select (lease->>'lease_id')::uuid from state where photo_id=pg_temp.id('56fa',21)),(select receipt from state where photo_id=pg_temp.id('56fa',21)))->>'status','clear','bounded private mask evidence completes exact current screen');
update private.photo_privacy_operators set active=true where operator_id=pg_temp.id('96fa',1);
select throws_ok($$select public.review_photo_privacy(pg_temp.token(1),jsonb_set(pg_temp.review(public.photo_privacy_receipt(pg_temp.id('56fa',21))),'{review_id}',(select to_jsonb(review_id) from retired_ids)))$$,'PP003',null,'erased review UUID remains retired for another photo');
select is(public.record_photo_privacy_content(pg_temp.content(pg_temp.id('56fa',21),1,repeat('b',64)))->>'status','registered','new bytes start a fresh bounded generation');
delete from state where photo_id=pg_temp.id('56fa',21);
-- Advance only owner-controlled fixture timestamps; exercise production backoff arithmetic.
create function pg_temp.retry_attempt(p_attempt integer) returns setof text language plpgsql as $$
declare lease jsonb; result jsonb; delay integer;
begin
    lease:=public.claim_photo_privacy_job();
    return next is((lease->>'attempt')::integer,p_attempt,'attempt '||p_attempt||' is counted once');
    result:=public.fail_photo_privacy_job((lease->>'lease_id')::uuid,'storage');
    return next is(result->>'status',case when p_attempt=5 then 'error' else 'pending' end,'attempt '||p_attempt||' has bounded failure state');
    if p_attempt<5 then
        delay:=case p_attempt when 1 then 60 when 2 then 120 when 3 then 240 else 480 end;
        return next ok((select ready_at>=clock_timestamp()+make_interval(secs=>delay-2) from private.photo_privacy_jobs where lease_id=(lease->>'lease_id')::uuid),'attempt '||p_attempt||' honors backoff');
        return next is(public.claim_photo_privacy_job(),null::jsonb,'backoff cannot be skipped');
        update private.photo_privacy_jobs set ready_at=clock_timestamp()-interval '1 second' where lease_id=(lease->>'lease_id')::uuid;
    else
        return next is(public.claim_photo_privacy_job(),null::jsonb,'sixth automatic attempt is refused');
    end if;
end;
$$;
select pg_temp.retry_attempt(i) from generate_series(1,5) i;
select is((select max(attempts)::integer from private.photo_privacy_jobs where photo_id=pg_temp.id('56fa',21) and content_revision=2),5,'five attempts remain terminal for this generation');
select is(public.record_photo_privacy_content(pg_temp.content(pg_temp.id('56fa',21),2,repeat('c',64)))->>'status','registered','actual new content resets terminal generation');
insert into state(photo_id,lease) select (l->>'photo_id')::uuid,l from (select public.claim_photo_privacy_job() l) q;
select is((select (lease->>'attempt')::integer from state where photo_id=pg_temp.id('56fa',21)),1,'new content begins at attempt one');
update private.photo_privacy_jobs set lease_expires_at=clock_timestamp()-interval '1 second' where lease_id=(select (lease->>'lease_id')::uuid from state where photo_id=pg_temp.id('56fa',21));
select throws_ok($$select public.fail_photo_privacy_job((select (lease->>'lease_id')::uuid from state where photo_id=pg_temp.id('56fa',21)),'timeout')$$,'PP002',null,'expired lease failure cannot write stale state');
select is(public.claim_photo_privacy_job(),null::jsonb,'expired lease is reaped into backoff');
select is((select last_error from private.photo_privacy_jobs where lease_id=(select (lease->>'lease_id')::uuid from state where photo_id=pg_temp.id('56fa',21))),'timeout','expired attempt is recorded as generic timeout');
update private.photo_privacy_jobs set ready_at=clock_timestamp()-interval '1 second' where lease_id=(select (lease->>'lease_id')::uuid from state where photo_id=pg_temp.id('56fa',21));
update state set lease=public.claim_photo_privacy_job() where photo_id=pg_temp.id('56fa',21);
select is((select (lease->>'attempt')::integer from state where photo_id=pg_temp.id('56fa',21)),2,'expiry counts toward the five-attempt budget');
update state set receipt=pg_temp.screen(lease,'unsupported') where photo_id=pg_temp.id('56fa',21);
select is(public.complete_photo_privacy_job((select (lease->>'lease_id')::uuid from state where photo_id=pg_temp.id('56fa',21)),(select receipt from state where photo_id=pg_temp.id('56fa',21)))->>'status','error','unsupported detection cannot become clear');
select throws_ok($$select public.review_photo_privacy(pg_temp.token(1),pg_temp.review(public.photo_privacy_receipt(pg_temp.id('56fa',21))))$$,'PP002',null,'human false positive cannot clear unsupported screen');
-- Privileged corruption witness: source/QA/gate qualify, but a current-state flag alone
-- cannot stand in for a supported screen/manual audit.
insert into public.photos(id,submission_id,shot_type,storage_path,qa_status)
values(pg_temp.id('56fa',298),pg_temp.id('46fa',2),'B',pg_temp.id('36fa',2)::text||'/'||pg_temp.id('46fa',2)::text||'/B/'||gen_random_uuid()::text||'.jpg','pass');
update private.photo_privacy_content set status='clear' where photo_id=pg_temp.id('56fa',21);
select ok(not(public.authorize_photo_privacy_export(pg_temp.export_request(public.photo_privacy_receipt(pg_temp.id('56fa',21))))->'authorizations'->0->>'authorized')::boolean,
    'a corrupted clear flag without a current supported screen/audit cannot authorize');
update private.photo_privacy_content set status='error' where photo_id=pg_temp.id('56fa',21);

select throws_ok($$select public.fail_photo_privacy_job((select (lease->>'lease_id')::uuid from state where photo_id=pg_temp.id('56fa',21)),'private diagnostic text')$$,'22023',null,'arbitrary worker error text cannot be persisted');
-- Exercise the unchanged old worker with fault-injected residual payloads after cleanup.
select pg_temp.seed(3,3);
insert into public.deletion_requests(id,contributor_id,kind) values(pg_temp.id('76fa',3),pg_temp.id('26fa',3),'delete_account');
update public.deletion_requests set status='processing',claimed_at=now() where id=pg_temp.id('76fa',3);
select public.apply_deletion_request(pg_temp.id('76fa',3));
delete from auth.users where id=pg_temp.id('36fa',3);
select is((select count(*) from private.photo_privacy_content where contributor_id=pg_temp.id('26fa',3)),0::bigint,'old apply worker cleans new private content through additive hooks');
-- Privileged fault injection simulates a broken cleanup/old worker; no API role can do this.
set local session_replication_role=replica;
insert into private.photo_privacy_content(photo_id,submission_id,contributor_id,grant_id) values(pg_temp.id('56fa',31),pg_temp.id('46fa',3),pg_temp.id('26fa',3),pg_temp.id('66fa',3));
set local session_replication_role=origin;
select throws_ok($$select public.complete_deletion_request(pg_temp.id('76fa',3))$$,'55000',null,'old complete worker refuses residual content even after source/auth erasure');
delete from private.photo_privacy_content where photo_id=pg_temp.id('56fa',31);
insert into private.photo_privacy_jobs(photo_id,contributor_id,grant_id,content_revision,policy_id,policy_revision) values(pg_temp.id('56fa',31),pg_temp.id('26fa',3),pg_temp.id('66fa',3),0,pg_temp.id('16fa',1),1);
select throws_ok($$select public.complete_deletion_request(pg_temp.id('76fa',3))$$,'55000',null,'old complete worker refuses an orphan lease/job');
delete from private.photo_privacy_jobs where photo_id=pg_temp.id('56fa',31);
insert into private.photo_privacy_screens(request_id,lease_id,photo_id,contributor_id,grant_id,content_revision,policy_id,policy_revision,sanitized_sha256,screening_version,calibration_version,status,receipt,receipt_sha256)
values(gen_random_uuid(),gen_random_uuid(),pg_temp.id('56fa',31),pg_temp.id('26fa',3),pg_temp.id('66fa',3),0,pg_temp.id('16fa',1),1,repeat('a',64),'synthetic-screen-v1','unapproved-synthetic-calibration-v1','error','{}',encode(extensions.digest(convert_to('{}','UTF8'),'sha256'),'hex'));
select throws_ok($$select public.complete_deletion_request(pg_temp.id('76fa',3))$$,'55000',null,'old complete worker refuses orphan screen receipt');
delete from private.photo_privacy_screens where photo_id=pg_temp.id('56fa',31);
insert into private.photo_privacy_reviews(review_id,photo_id,contributor_id,grant_id,content_revision,policy_id,policy_revision,sanitized_sha256,operator_id,decision,reason,request,request_sha256)
values(gen_random_uuid(),pg_temp.id('56fa',31),pg_temp.id('26fa',3),pg_temp.id('66fa',3),0,pg_temp.id('16fa',1),1,repeat('a',64),pg_temp.id('96fa',1),'withhold','privacy_risk','{}',encode(extensions.digest(convert_to('{}','UTF8'),'sha256'),'hex'));
select throws_ok($$select public.complete_deletion_request(pg_temp.id('76fa',3))$$,'55000',null,'old complete worker refuses orphan human audit');
delete from private.photo_privacy_reviews where photo_id=pg_temp.id('56fa',31);
select lives_ok($$select public.complete_deletion_request(pg_temp.id('76fa',3))$$,'old complete worker succeeds only after every private payload is absent');
select is((select status from public.deletion_requests where id=pg_temp.id('76fa',3)),'completed','honest completion is recorded');
select throws_ok($$delete from private.photo_privacy_state$$,'55000',null,'global gate state cannot disappear through ordinary owner DML');
select throws_ok($$update private.photo_privacy_policies set detector_manifest_sha256=repeat('a',64)$$,'PP003',null,'approved policy manifests cannot change in place');
-- Defense in depth: even accidental future permissive client grants do not authorize rows.
grant usage on schema private to authenticated;
grant select,insert,update,delete on all tables in schema private to authenticated;
create policy future_permissive_photo_select on private.photo_privacy_content for all to authenticated using(true) with check(true);
set local role authenticated;
select is((select count(*) from private.photo_privacy_content),0::bigint,'restrictive policy defeats future permissive client read');
select throws_ok($$insert into private.photo_privacy_operators values(gen_random_uuid(),pg_temp.id('36fa',4),repeat('a',64),true)$$,'42501',null,'restrictive policy defeats future client operator provisioning');
reset role;
select finish();
rollback;
