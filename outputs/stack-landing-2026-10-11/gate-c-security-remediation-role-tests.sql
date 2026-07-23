begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;
-- Synthetic role-proof data; no observations, coordinates, photos or real contributor data.
insert into public.contributors(id,auth_uid,handle) values('10000000-0000-4000-8000-0000000000aa',null,'local-security-proof');
insert into public.contribution_grants(id,contributor_id,terms_version,accepted_at,attribution_name)
values('10000000-0000-4000-8000-0000000000ab','10000000-0000-4000-8000-0000000000aa','2026-07-22-v1',now(),'Anonymous soil contributor');
set local role service_role;
insert into public.grant_withdrawals(grant_id,reason) values('10000000-0000-4000-8000-0000000000ab','steward_action');
insert into public.attribution_reviews(contributor_id,attribution_name,decision,reviewer)
values('10000000-0000-4000-8000-0000000000aa','Anonymous soil contributor','approved','local-proof');
reset role;
select plan(28);
select is((select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname in ('capture_is_open','finalize_submission','current_auth_user_exists','my_submission_accepts_uploads') and not p.prosecdef),4::bigint,'all four public functions use caller privileges');
select is((select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname in ('finalize_submission','current_auth_user_exists','my_submission_accepts_uploads') and p.prosqlbody is not null),3::bigint,'all three wrappers have definition-time bound SQL bodies');
select is((select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='private' and p.proname in ('finalize_submission','current_auth_user_exists','my_submission_accepts_uploads') and p.prosecdef and p.proconfig @> array['search_path=""']),3::bigint,'exact three private guarded bodies pin empty search path');
select is((select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='private' and p.proname in ('finalize_submission','current_auth_user_exists','my_submission_accepts_uploads') and has_function_privilege('authenticated',p.oid,'execute')),3::bigint,'authenticated has only the required private guarded dispatch grants');
select is((select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='private' and has_function_privilege('anon',p.oid,'execute')),0::bigint,'anon executes no private function');
select ok(not has_schema_privilege('authenticated','private','usage') and not has_schema_privilege('anon','private','usage'),'private schema remains unusable by clients');
select ok(not has_table_privilege('authenticated','public.grant_withdrawals','select') and not has_table_privilege('authenticated','public.attribution_reviews','select') and not has_table_privilege('authenticated','auth.users','select'),'no private table or auth user access added');
select is((select count(*) from pg_policy p where p.polname in ('grant_withdrawals_deny_client','attribution_reviews_deny_client') and not p.polpermissive and pg_get_expr(p.polqual,p.polrelid)='false' and pg_get_expr(p.polwithcheck,p.polrelid)='false'),2::bigint,'both private tables have restrictive false policies');
select ok(not has_column_privilege('anon','public.service_state','singleton','select') and not has_table_privilege('anon','public.service_state','select'),'capture caller uses original limited column ACL');
set local role anon;
select is(public.capture_is_open(),false,'anonymous capture query stays false with limited column access');
select throws_ok($$select public.finalize_submission('00000000-0000-4000-8000-000000000001')$$,'42501',null,'anon cannot finalize through the wrapper');
select throws_ok($$select public.my_submission_accepts_uploads('00000000-0000-4000-8000-000000000001')$$,'42501',null,'anon cannot probe upload eligibility');
reset role;
set local role authenticated;
set local "request.jwt.claims" = '{}';
select is(public.capture_is_open(),false,'signed-in role capture query remains false');
select is(public.current_auth_user_exists(),false,'missing auth UID remains false through bound wrapper');
select is(public.my_submission_accepts_uploads('00000000-0000-4000-8000-000000000001'),false,'missing auth UID cannot accept uploads through bound wrapper');
select throws_ok($$select public.finalize_submission('00000000-0000-4000-8000-000000000001')$$,'42501','authentication required','missing auth UID cannot finalize through bound wrapper');
select throws_ok($$select private.current_auth_user_exists()$$,'42501',null,'direct private name resolution still denied despite narrow EXECUTE grant');
select throws_ok($$select count(*) from public.grant_withdrawals$$,'42501',null,'direct withdrawals read remains denied');
select throws_ok($$update public.submissions set finalized_at=now() where id='00000000-0000-4000-8000-000000000001'$$,'42501',null,'no direct finalized_at write granted');
reset role;
-- Fault injection in a rolled-back local transaction only: a future accidental SELECT grant
-- cannot defeat the explicit restrictive policy. Actual migration adds no table privilege.
grant select on public.grant_withdrawals, public.attribution_reviews to authenticated;
set local role authenticated;
select is((select count(*) from public.grant_withdrawals),0::bigint,'withdrawal deny policy survives an accidental local SELECT grant');
select is((select count(*) from public.attribution_reviews),0::bigint,'attribution deny policy survives an accidental local SELECT grant');
reset role;
set local role service_role;
select is((select count(*) from public.grant_withdrawals),1::bigint,'service inserts and reads populated withdrawals under unchanged bypass privileges');
select is((select count(*) from public.attribution_reviews),1::bigint,'service inserts and reads populated attribution reviews under unchanged bypass privileges');
select is(public.capture_is_open(),false,'service capture read remains false');
select is(public.current_auth_user_exists(),false,'service auth existence check keeps caller semantics');
select is(public.my_submission_accepts_uploads('00000000-0000-4000-8000-000000000001'),false,'service upload eligibility keeps existing callable capability');
select ok(not has_function_privilege('service_role','public.finalize_submission(uuid)','execute'),'service does not gain owner finalization capability');
reset role;
select is(public.capture_is_open(),false,'capture remains closed at transaction end');
select * from finish();
rollback;
