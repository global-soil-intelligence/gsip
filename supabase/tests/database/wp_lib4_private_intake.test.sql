-- Owner-private, unverified intake: role boundaries, authority, immutable retries and rights.
begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;
select no_plan();

create function pg_temp.id(p_prefix text, p_index integer)
returns uuid language sql immutable as $$
    select (p_prefix || '0000-0000-4000-8000-' || lpad(p_index::text, 12, '0'))::uuid;
$$;
create function pg_temp.request(p_index integer, p_declaration jsonb default null)
returns jsonb language sql immutable as $$
    select jsonb_build_object('schema_version', 'gsip-library-intake-v1',
        'intake_id', pg_temp.id('e404', p_index), 'node_id', pg_temp.id('a404', 1),
        'sample_id', pg_temp.id('f404', p_index), 'submission_id', pg_temp.id('b404', p_index),
        'protocol_version', 'gsip-capture-v1', 'context',
        jsonb_build_object('depth_top_cm', 0, 'depth_bottom_cm', 20, 'condition', 'dry'),
        'instrument_declaration', p_declaration);
$$;
create function pg_temp.declaration(p_index integer, p_digest text default repeat('a',64))
returns jsonb language sql immutable as $$
    select jsonb_build_object('measurement_id', pg_temp.id('8404', p_index), 'measurement',
        jsonb_build_object('kind','instrument_reflectance', 'source_sha256',p_digest,
            'instrument_id',pg_temp.id('9404',1), 'calibration_id',pg_temp.id('7404',1),
            'wavelength_nm',jsonb_build_array(400,500,600),
            'reflectance',jsonb_build_array(0.2,0.3,0.4), 'uncertainty',jsonb_build_array(0.01,0.02,0.03)));
$$;
create function pg_temp.seed_submission(p_index integer, p_owner integer default 1, p_grant uuid default null)
returns void language plpgsql as $$
declare uid uuid := pg_temp.id('3404',p_owner);
    sub uuid := pg_temp.id('b404',p_index);
begin
    insert into public.submissions(id,contributor_id,grant_id,geom_precise,captured_at,land_cover,surface_condition,disturbed,device_model,finalized_at)
    values(sub,pg_temp.id('2404',p_owner),coalesce(p_grant,pg_temp.id('6404',p_owner)),
        'SRID=4326;POINT EMPTY',now(),'bare','dry',false,'synthetic fixture',now());
    insert into public.photos(id,submission_id,shot_type,storage_path) values
        (pg_temp.id('d404',p_index*2),sub,'A',uid::text||'/'||sub::text||'/A/'||pg_temp.id('c404',p_index*2)::text||'.jpg'),
        (pg_temp.id('d404',p_index*2+1),sub,'B',uid::text||'/'||sub::text||'/B/'||pg_temp.id('c404',p_index*2+1)::text||'.jpg');
end;
$$;
insert into public.terms_versions(version,published_at) values ('lib4b-test',now()-interval '100 days');
insert into auth.users(id) select pg_temp.id('3404',i) from generate_series(1,4) i;
insert into public.contributors(id,auth_uid,handle)
    select pg_temp.id('2404',i),pg_temp.id('3404',i),'library-synthetic-'||i from generate_series(1,4) i;
insert into public.contribution_grants(id,contributor_id,terms_version,accepted_at,attribution_name)
    select pg_temp.id('6404',i),pg_temp.id('2404',i),'lib4b-test',now()-interval '40 days',
        'Anonymous soil contributor' from generate_series(1,4) i;
select pg_temp.seed_submission(i) from generate_series(1,8) i;
select pg_temp.seed_submission(101,2);
select pg_temp.seed_submission(102,2);
select pg_temp.seed_submission(201,4);

select ok(not (public.library_intake_capabilities()->>'available')::boolean, 'new gate defaults closed');
select is(public.library_intake_capabilities()->>'version','gsip-library-intake-v1','capability version is exact');
select ok((select bool_and(not p.prosecdef and p.prosqlbody is not null)
    from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public' and p.proname in ('library_intake_capabilities','record_library_intake','my_library_intake_receipt')),
    'client entry points are definition-time bound invoker wrappers');
select ok((select count(*)=10 and bool_and(c.relrowsecurity)
    from pg_class c join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='private' and c.relname like 'library_%' and c.relkind='r'), 'all ten private library tables enable RLS');
select ok((select count(*)=10 from pg_policy p join pg_class c on c.oid=p.polrelid
    join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='private' and c.relname like 'library_%' and not p.polpermissive),
    'every private library table has a restrictive client-deny policy');
select ok(not has_schema_privilege('authenticated','private','usage')
    and not has_schema_privilege('anon','private','usage')
    and not has_schema_privilege('authenticated','private','create'), 'clients gain no private schema access');
select ok(not has_table_privilege('authenticated','private.library_samples','select')
    and not has_table_privilege('authenticated','private.library_intakes','insert')
    and not has_table_privilege('service_role','private.library_intakes','update'),
    'clients cannot read/write private tables and service role cannot rewrite claims');

set local role anon;
select lives_ok($$select public.library_intake_capabilities()$$,'anonymous capability read succeeds without an account');
select throws_ok($$select public.record_library_intake(pg_temp.request(1))$$,'42501',null,'anonymous intake is refused');
reset role;
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"34040000-0000-4000-8000-000000000001","role":"authenticated"}';
select throws_ok($$select public.set_library_intake_open(true)$$,'42501',null,'client cannot open the library gate');
select throws_ok($$select public.record_library_intake(pg_temp.request(1))$$,'LI001',null,'library closed is an explicit hold');
select throws_ok($$select * from private.library_intakes$$,'42501',null,'direct private table name resolution fails');
select throws_ok($$select private.record_library_intake(pg_temp.request(1))$$,'42501',null,'bound helper cannot be called directly by private name');
reset role;
set local role service_role;
select lives_ok($$select public.set_library_intake_open(true)$$,'service-only gate operation is available');
reset role;
-- The disposable development seed may have capture open; close it explicitly for this case.
update public.service_state set capture_open=false;
select ok(not (public.library_intake_capabilities()->>'available')::boolean,'library gate cannot bypass closed capture');
update public.service_state set capture_open=true;
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"34040000-0000-4000-8000-000000000001","role":"authenticated"}';
select is(public.record_library_intake(pg_temp.request(1,pg_temp.declaration(1)))->>'status',
    'stored_private_unverified','owner stores a declaration under an admitted 40-day-old grant');
select is(public.record_library_intake(pg_temp.request(1,pg_temp.declaration(1)))->>'status',
    'already_stored','lost-response retry is idempotent');
select is(public.record_library_intake(jsonb_set(pg_temp.request(1,pg_temp.declaration(1)),
    '{context,depth_top_cm}','0.00'))->>'status','already_stored','numeric spelling does not create a conflict');
select is(public.record_library_intake(jsonb_set(pg_temp.request(1,pg_temp.declaration(1)),
    '{intake_id}',to_jsonb(upper(pg_temp.id('e404',1)::text))))->>'status','already_stored','UUID case normalizes consistently');
select is((select count(*) from jsonb_object_keys(public.my_library_intake_receipt(pg_temp.id('e404',1)))),
    2::bigint,'receipt contains exactly the two safe fields');
select is(public.my_library_intake_receipt(pg_temp.id('e404',1))->>'status','already_stored','owner can read safe receipt');
select throws_ok($$select public.record_library_intake(jsonb_set(pg_temp.request(1,pg_temp.declaration(1)),
    '{context,depth_bottom_cm}','21'))$$,'LI002',null,'changed retry cannot replace immutable context');
select throws_ok($$select public.record_library_intake(jsonb_set(pg_temp.request(2),
    '{submission_id}',to_jsonb(pg_temp.id('b404',1)::text)))$$,'LI002',null,'one source/submission cannot be rebound');
select throws_ok($$select public.record_library_intake(jsonb_set(jsonb_set(pg_temp.request(2),
    '{sample_id}',to_jsonb(pg_temp.id('f404',1)::text)),'{context,condition}','"wet"'))$$,
    'LI002',null,'same physical sample cannot change declared context');
select is(public.record_library_intake(jsonb_set(pg_temp.request(2),'{sample_id}',
    to_jsonb(pg_temp.id('f404',1)::text)))->>'status','stored_private_unverified','same immutable sample can have another source under the same grant');
select throws_ok($$select public.record_library_intake(pg_temp.request(3,pg_temp.declaration(3)))$$,
    'LI002',null,'owner cannot count a claimed instrument source under another sample');

-- Server validation remains effective if the client parser is bypassed.
select throws_ok(format('select public.record_library_intake(%L::jsonb)',bad), '22023',null,description)
from (values
    (pg_temp.request(3)||'{"consent_verified":true}'::jsonb,'local consent cannot enter hosted authority'),
    (pg_temp.request(3)||'{"holdout":false}'::jsonb,'client cannot supply a holdout state'),
    (pg_temp.request(3)||'{"qa_status":"pass"}'::jsonb,'client cannot grant QA clearance'),
    (pg_temp.request(3)||'{"grant_id":"64040000-0000-4000-8000-000000000001"}'::jsonb,'grant comes from the owned submission'),
    (jsonb_set(pg_temp.request(3),'{schema_version}','null'),'null contract version is refused'),
    (jsonb_set(pg_temp.request(3),'{protocol_version}','null'),'null protocol version is refused'),
    (jsonb_set(pg_temp.request(3),'{sample_id}','"bad"'),'malformed sample UUID is refused'),
    (pg_temp.request(3)-'instrument_declaration','missing explicit declaration/null field is refused'),
    (jsonb_set(pg_temp.request(3),'{context,depth_top_cm}','-1'),'negative depth is refused'),
    (jsonb_set(pg_temp.request(3),'{context,depth_bottom_cm}','201'),'depth above 200 is refused'),
    (jsonb_set(pg_temp.request(3),'{context,depth_top_cm}','20'),'empty depth range is refused'),
    (jsonb_set(pg_temp.request(3),'{context,depth_top_cm}','"0"'),'string depth is refused'),
    (jsonb_set(pg_temp.request(3),'{context,location}','"private point"'),'unknown context field is refused'),
    (jsonb_set(pg_temp.request(3),'{context,condition}','"other"'),'unknown material condition is refused'),
    (jsonb_set(pg_temp.request(3),'{instrument_declaration}','[]'),'arbitrary attachment type is refused'),
    (jsonb_set(pg_temp.request(3,pg_temp.declaration(3)), '{instrument_declaration,measurement,kind}','null'),'null measurement kind is refused'),
    (jsonb_set(pg_temp.request(3,pg_temp.declaration(3)), '{instrument_declaration,measurement,reflectance}','[0.2,0.3,40]'),'percent reflectance is never silently converted'),
    (jsonb_set(pg_temp.request(3,pg_temp.declaration(3)), '{instrument_declaration,measurement,uncertainty}','[0.2,0.3]'),'unaligned uncertainty is refused'),
    (jsonb_set(pg_temp.request(3,pg_temp.declaration(3)), '{instrument_declaration,measurement,wavelength_nm}','[400,400,600]'),'non-increasing bands are refused'),
    (jsonb_set(pg_temp.request(3,pg_temp.declaration(3)), '{instrument_declaration,measurement,wavelength_nm}','[199,400,600]'),'wavelength below 200 is refused'),
    (jsonb_set(pg_temp.request(3,pg_temp.declaration(3)), '{instrument_declaration,measurement,reflectance}','[0.2,null,0.4]'),'null band values are refused'),
    (jsonb_set(pg_temp.request(3,pg_temp.declaration(3)), '{instrument_declaration,measurement,source_sha256}',to_jsonb(repeat('A',64))),'digest must be lowercase hex'),
    (pg_temp.request(3)||jsonb_build_object('extra',repeat('x',2000000)),'normalized request above byte bound is refused')
) cases(bad,description);
reset role;
select is((select intakes::integer from private.library_intake_daily_usage where contributor_id=pg_temp.id('2404',1)),2,'retries and invalid requests spend no daily quota');
select ok((select not source_verified and not calibration_verified and not pairing_verified
    from private.library_instrument_declarations where measurement_id=pg_temp.id('8404',1)), 'all scientific verification stays false');
select ok((select payload_sha256=encode(extensions.digest(convert_to(payload_text,'UTF8'),'sha256'),'hex')
    from private.library_intakes where intake_id=pg_temp.id('e404',1)), 'private digest binds the persisted normalized bytes');
select throws_ok($$update private.library_intakes set payload=payload||'{"new":true}' where intake_id=pg_temp.id('e404',1)$$,
    'LI002',null,'even privileged writes cannot rewrite immutable payload');
select throws_ok($$delete from private.library_samples where sample_id=pg_temp.id('f404',1)$$,
    '55000',null,'payload deletion without a tombstone is refused');
select throws_ok($$truncate private.library_sample_tombstones$$,'P0001',null,'tombstones cannot be truncated');

set local role authenticated;
set local "request.jwt.claims" = '{"sub":"34040000-0000-4000-8000-000000000002","role":"authenticated"}';
select throws_ok($$select public.my_library_intake_receipt(pg_temp.id('e404',1))$$,'42501',null,'another owner cannot read a receipt');
select throws_ok($$select public.record_library_intake(pg_temp.request(1))$$,'42501',null,'another owner cannot attach another contributor source');
select throws_ok($$select public.record_library_intake(pg_temp.request(102))$$,'LI002',null,'existing namespace cannot be reassigned');
select is(public.record_library_intake(jsonb_set(pg_temp.request(101,pg_temp.declaration(101)),
    '{node_id}',to_jsonb(pg_temp.id('a404',2)::text)))->>'status','stored_private_unverified',
    'same untrusted source hash in another owner does not imply physical pairing');
reset role;

-- A permissive client grant/policy still cannot bypass the restrictive deny policy.
grant usage on schema private to authenticated;
grant select on private.library_intakes to authenticated;
create policy lib4b_test_permissive on private.library_intakes for select to authenticated using(true);
set local role authenticated;
select is((select count(*) from private.library_intakes),0::bigint,'restrictive RLS denies even an accidental permissive read');
reset role;
revoke usage on schema private from authenticated;
revoke select on private.library_intakes from authenticated;
drop policy lib4b_test_permissive on private.library_intakes;

-- Existing and subsequently sealed labels both propagate, without returning evidence.
insert into public.gold_labels(id,submission_id,lab_name,property,value,unit,depth_top_cm,depth_bottom_cm,holdout)
values(pg_temp.id('5404',4),pg_temp.id('b404',4),'synthetic','soc',1,'g/kg',0,20,true);
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"34040000-0000-4000-8000-000000000001","role":"authenticated"}';
select is(public.record_library_intake(pg_temp.request(4))->>'status','stored_private_unverified','holdout source gets the same unverified receipt');
reset role;
select ok((select holdout from private.library_sample_restrictions where sample_id=pg_temp.id('f404',4)), 'already held-out source seals its entire sample');
insert into public.gold_labels(id,submission_id,lab_name,property,value,unit,depth_top_cm,depth_bottom_cm,holdout)
values(pg_temp.id('5404',2),pg_temp.id('b404',2),'synthetic','soc',1,'g/kg',0,20,true);
select ok((select holdout from private.library_sample_restrictions where sample_id=pg_temp.id('f404',1)), 'later sealing a linked source reaches all sample measurements');
update public.gold_labels set holdout=false where id=pg_temp.id('5404',2);
delete from public.gold_labels where id=pg_temp.id('5404',2);
select ok((select holdout from private.library_sample_restrictions where sample_id=pg_temp.id('f404',1)), 'removing/unsealing the source label cannot unseal a sample');
select throws_ok($$update private.library_sample_restrictions set holdout=false where sample_id=pg_temp.id('f404',1)$$,
    '23514',null,'direct privileged false flag cannot unseal a sample');
update public.submissions set is_synthetic=true where id=pg_temp.id('b404',2);
select ok((select synthetic from private.library_sample_restrictions where sample_id=pg_temp.id('f404',1)), 'synthetic quarantine propagates sample-wide');
select ok(not (select holdout or synthetic from private.library_sample_restrictions where node_id=pg_temp.id('a404',2)),
    'untrusted matching source hash never changes another owner restrictions');

-- Quota is contributor-wide, durable across withdrawals; equivalent retry remains free.
select pg_temp.seed_submission(i,3) from generate_series(301,401) i;
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"34040000-0000-4000-8000-000000000003","role":"authenticated"}';
select lives_ok($$select public.record_library_intake(jsonb_set(pg_temp.request(i),'{node_id}',to_jsonb(pg_temp.id('a404',3)::text)))
    from generate_series(301,400) i$$,'100 newly admitted owner intakes are allowed');
select throws_ok($$select public.record_library_intake(jsonb_set(pg_temp.request(401),'{node_id}',to_jsonb(pg_temp.id('a404',3)::text)))$$,
    'LI003',null,'101st daily intake is refused');
select is(public.record_library_intake(jsonb_set(pg_temp.request(301),'{node_id}',to_jsonb(pg_temp.id('a404',3)::text)))->>'status',
    'already_stored','retry at the quota limit remains free');
reset role;

-- Withdraw grants atomically: old worker signatures need no extension or redeployment.
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"34040000-0000-4000-8000-000000000001","role":"authenticated"}';
insert into public.deletion_requests(contributor_id,kind)
values(pg_temp.id('2404',1),'withdraw_contributions');
select throws_ok($$select public.record_library_intake(pg_temp.request(1,pg_temp.declaration(1)))$$,
    'WD001',null,'covered queued retry is terminally withdrawn');
reset role;
select is((select count(*) from private.library_samples where contributor_id=pg_temp.id('2404',1)),0::bigint,'request transaction erases covered sample payload immediately');
select is((select count(*) from private.library_instrument_declarations where contributor_id=pg_temp.id('2404',1)),0::bigint,'declarations cannot survive withdrawal');
select is((select count(*) from private.library_sample_tombstones where grant_id=pg_temp.id('6404',1)),2::bigint,'opaque refusal records survive payload erasure');
select is((select intakes::integer from private.library_intake_daily_usage where contributor_id=pg_temp.id('2404',1)),3,'withdrawal does not reset the daily quota');
select throws_ok($$delete from private.library_sample_tombstones where grant_id=pg_temp.id('6404',1)$$,'P0001',null,'refusal records cannot be removed');
set local role service_role;
select lives_ok($$select public.apply_deletion_request((select request_id from public.claim_deletion_request()))$$,'old worker apply signature still succeeds');
reset role;
-- Privileged synthetic fault injection: old worker must not certify residual covered data.
insert into private.library_samples(node_id,sample_id,contributor_id,grant_id,protocol_version,context)
values(pg_temp.id('a404',1),pg_temp.id('f404',1),pg_temp.id('2404',1),pg_temp.id('6404',1),
    'gsip-capture-v1','{"depth_top_cm":0,"depth_bottom_cm":20,"condition":"dry"}');
set local role service_role;
select throws_ok($$select public.complete_deletion_request((select id from public.deletion_requests where contributor_id=pg_temp.id('2404',1)))$$,
    '55000',null,'old worker refuses completion while covered private sample payload remains');
reset role;
delete from private.library_samples where node_id=pg_temp.id('a404',1) and sample_id=pg_temp.id('f404',1);
set local role service_role;
select lives_ok($$select public.complete_deletion_request((select id from public.deletion_requests where contributor_id=pg_temp.id('2404',1)))$$,'old worker completes only after covered payload is absent');
reset role;
select is((select status from public.deletion_requests where contributor_id=pg_temp.id('2404',1)),'completed','withdrawal completion is honest');

-- A new grant cannot resurrect an opaque sample tombstone.
-- Model a later acceptance while keeping this regression suite in one rollback transaction.
update public.deletion_requests set requested_at=now()-interval '1 second' where contributor_id=pg_temp.id('2404',1);
insert into public.contribution_grants(id,contributor_id,terms_version,accepted_at,attribution_name)
values(pg_temp.id('6404',11),pg_temp.id('2404',1),'lib4b-test',now(),'Anonymous soil contributor');
select pg_temp.seed_submission(8,1,pg_temp.id('6404',11));
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"34040000-0000-4000-8000-000000000001","role":"authenticated"}';
select throws_ok($$select public.record_library_intake(jsonb_set(pg_temp.request(8),'{sample_id}',to_jsonb(pg_temp.id('f404',1)::text)))$$,
    'WD001',null,'new grant cannot revive a tombstoned sample key');
reset role;

set local role authenticated;
set local "request.jwt.claims" = '{"sub":"34040000-0000-4000-8000-000000000001","role":"authenticated"}';
select throws_ok($$select public.record_library_intake(jsonb_set(pg_temp.request(8),'{intake_id}',to_jsonb(pg_temp.id('e404',1)::text)))$$,
    'LI002',null,'new grant/new source/sample cannot reuse an erased intake UUID with different bytes');
select throws_ok($$select public.record_library_intake(pg_temp.request(8,pg_temp.declaration(1,repeat('c',64))))$$,
    'LI002',null,'new grant/new source/sample cannot reuse an erased measurement UUID with different bytes');
reset role;
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"34040000-0000-4000-8000-000000000002","role":"authenticated"}';
select throws_ok($$select public.record_library_intake(jsonb_set(jsonb_set(pg_temp.request(102),'{node_id}',to_jsonb(pg_temp.id('a404',2)::text)),
    '{intake_id}',to_jsonb(pg_temp.id('e404',1)::text)))$$,'LI002',null,'another owner cannot reuse a retired intake UUID');
select throws_ok($$select public.record_library_intake(jsonb_set(pg_temp.request(102,pg_temp.declaration(1,repeat('c',64))),
    '{node_id}',to_jsonb(pg_temp.id('a404',2)::text)))$$,'LI002',null,'another owner cannot reuse a retired measurement UUID');
reset role;
select is((select count(*) from private.library_retired_declaration_ids where identity_kind='measurement'),1::bigint,
    'withdrawal retains only the minimal opaque retired measurement identity');
select throws_ok($$update private.library_retired_declaration_ids set identity_id=pg_temp.id('e404',999)$$,'P0001',null,'retired declaration IDs cannot be changed');
select throws_ok($$delete from private.library_retired_declaration_ids$$,'P0001',null,'retired declaration IDs cannot be erased');
select throws_ok($$truncate private.library_retired_declaration_ids$$,'P0001',null,'retired declaration IDs cannot be truncated');

-- Erasure does not turn already spent daily intake quota into fresh capacity.
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"34040000-0000-4000-8000-000000000003","role":"authenticated"}';
insert into public.deletion_requests(contributor_id,kind) values(pg_temp.id('2404',3),'withdraw_contributions');
reset role;
select is((select count(*) from private.library_intakes i join private.library_samples s using(node_id,sample_id)
    where s.contributor_id=pg_temp.id('2404',3)),0::bigint,'quota-owner withdrawal erases all 100 admitted payloads');
select is((select intakes::integer from private.library_intake_daily_usage where contributor_id=pg_temp.id('2404',3)),100,
    '100 historical admissions stay spent after withdrawal');
set local role service_role;
select public.apply_deletion_request((select request_id from public.claim_deletion_request()));
select public.complete_deletion_request((select id from public.deletion_requests where contributor_id=pg_temp.id('2404',3)));
reset role;
update public.deletion_requests set requested_at=now()-interval '1 second' where contributor_id=pg_temp.id('2404',3);
insert into public.contribution_grants(id,contributor_id,terms_version,accepted_at,attribution_name)
values(pg_temp.id('6404',33),pg_temp.id('2404',3),'lib4b-test',now(),'Anonymous soil contributor');
select pg_temp.seed_submission(402,3,pg_temp.id('6404',33));
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"34040000-0000-4000-8000-000000000003","role":"authenticated"}';
select throws_ok($$select public.record_library_intake(jsonb_set(pg_temp.request(402),'{node_id}',to_jsonb(pg_temp.id('a404',3)::text)))$$,
    'LI003',null,'101st fresh intake is refused after all earlier payloads were withdrawn');
reset role;

-- Account deletion erases namespaces and counters in the request transaction too.
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"34040000-0000-4000-8000-000000000004","role":"authenticated"}';
select is(public.record_library_intake(jsonb_set(pg_temp.request(201),'{node_id}',to_jsonb(pg_temp.id('a404',4)::text)))->>'status',
    'stored_private_unverified','account-deletion fixture owns an intake');
insert into public.deletion_requests(contributor_id,kind)
values(pg_temp.id('2404',4),'delete_account');
reset role;
select is((select count(*) from private.library_nodes where contributor_id=pg_temp.id('2404',4)),0::bigint,'account request removes its private namespaces');
select is((select count(*) from private.library_intake_daily_usage where contributor_id=pg_temp.id('2404',4)),0::bigint,'account request removes private usage counters');
select ok(exists(select 1 from private.library_retired_nodes where node_id=pg_temp.id('a404',4)),
    'account deletion retires only the opaque node UUID permanently');
select throws_ok($$delete from private.library_retired_nodes$$,'P0001',null,'retired namespaces cannot be reassigned by erasing their ledger');
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"34040000-0000-4000-8000-000000000002","role":"authenticated"}';
select throws_ok($$select public.record_library_intake(jsonb_set(pg_temp.request(102),'{node_id}',to_jsonb(pg_temp.id('a404',4)::text)))$$,
    'LI002',null,'another owner cannot reuse an account-deleted node UUID with a fresh sample');
reset role;
set local role service_role;
select lives_ok($$select public.apply_deletion_request((select request_id from public.claim_deletion_request()))$$,'old worker applies account deletion');
reset role;
delete from auth.users where id=pg_temp.id('3404',4);
insert into private.library_nodes(node_id,contributor_id) values(pg_temp.id('a404',44),pg_temp.id('2404',4));
set local role service_role;
select throws_ok($$select public.complete_deletion_request((select id from public.deletion_requests where contributor_id=pg_temp.id('2404',4)))$$,
    '55000',null,'old account worker cannot complete while contributor-linked private namespace remains');
reset role;
insert into private.library_retired_nodes(node_id) values(pg_temp.id('a404',44));
delete from private.library_nodes where node_id=pg_temp.id('a404',44);
insert into private.library_intake_daily_usage(contributor_id,utc_day,intakes)
values(pg_temp.id('2404',4),(now() at time zone 'UTC')::date,1);
set local role service_role;
select throws_ok($$select public.complete_deletion_request((select id from public.deletion_requests where contributor_id=pg_temp.id('2404',4)))$$,
    '55000',null,'old account worker cannot complete while contributor-linked private usage remains');
reset role;
delete from private.library_intake_daily_usage where contributor_id=pg_temp.id('2404',4);
set local role service_role;
select lives_ok($$select public.complete_deletion_request((select id from public.deletion_requests where contributor_id=pg_temp.id('2404',4)))$$,'old worker completes after synthetic auth-user deletion');
reset role;

-- Direct source deletion cannot leave private payload or erase without refusal evidence.
delete from public.photos where id=pg_temp.id('d404',203);
select is((select count(*) from private.library_samples where contributor_id=pg_temp.id('2404',2)),0::bigint,'source-photo deletion erases its private sample');
select ok(exists(select 1 from private.library_sample_tombstones where node_id=pg_temp.id('a404',2) and reason='source_deleted'),
    'source deletion preserves an opaque tombstone first');

select * from finish();
rollback;
