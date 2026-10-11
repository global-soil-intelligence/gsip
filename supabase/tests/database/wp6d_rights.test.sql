-- WP-6d: contributor rights. Requests, immediate withdrawal, refusal of anything a request covers,
-- the rights worker's steps, account pseudonymization, immutable grants and append-only
-- withdrawals, attribution review, and the Storage catch-alls.
begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;

select plan(70);

-- Privileges: the worker's functions and the rights tables are server-only.
select ok(
    not has_function_privilege('authenticated', 'public.claim_deletion_request(interval)', 'execute')
    and not has_function_privilege('authenticated', 'public.apply_deletion_request(uuid)', 'execute')
    and not has_function_privilege('authenticated', 'public.complete_deletion_request(uuid)', 'execute')
    and not has_function_privilege('authenticated', 'public.release_deletion_request(uuid, text, interval)', 'execute')
    and not has_function_privilege('authenticated', 'public.contributor_orphaned_objects(uuid, integer)', 'execute')
    and not has_function_privilege('authenticated', 'public.orphaned_photo_objects(integer)', 'execute')
    and not has_function_privilege('authenticated', 'public.auth_user_exists(uuid)', 'execute')
    and not has_function_privilege('anon', 'public.claim_deletion_request(interval)', 'execute')
    and not has_function_privilege('anon', 'public.contributor_orphaned_objects(uuid, integer)', 'execute')
    and not has_function_privilege('anon', 'public.my_submission_accepts_uploads(text)', 'execute'),
    'clients cannot run the rights worker steps or probe other accounts'
);
select ok(
    not has_table_privilege('authenticated', 'public.grant_withdrawals', 'select')
    and not has_table_privilege('authenticated', 'public.grant_withdrawals', 'insert')
    and not has_table_privilege('anon', 'public.grant_withdrawals', 'select'),
    'clients cannot read or write grant withdrawals'
);
select ok(
    not has_table_privilege('authenticated', 'public.attribution_reviews', 'select')
    and not has_table_privilege('authenticated', 'public.attribution_reviews', 'insert')
    and not has_table_privilege('anon', 'public.attribution_reviews', 'select'),
    'clients cannot read or write attribution reviews'
);
select ok(
    not has_table_privilege('authenticated', 'public.attribution_review_queue', 'select')
    and not has_table_privilege('anon', 'public.attribution_review_queue', 'select'),
    'the attribution review queue is server-only'
);
select ok(
    not has_table_privilege('authenticated', 'public.deletion_requests', 'update')
    and not has_table_privilege('authenticated', 'public.deletion_requests', 'delete')
    and not has_table_privilege('anon', 'public.deletion_requests', 'select')
    and not has_table_privilege('anon', 'public.deletion_requests', 'insert'),
    'clients can never change or remove a request, and anonymous visitors have none'
);
select ok(
    not has_column_privilege('authenticated', 'public.deletion_requests', 'last_error', 'select')
    and not has_column_privilege('authenticated', 'public.deletion_requests', 'status', 'insert'),
    'owners neither see operator errors nor choose a status'
);
select ok(
    not has_table_privilege('service_role', 'public.grant_withdrawals', 'truncate')
    and not has_table_privilege('service_role', 'public.contribution_grants', 'truncate'),
    'not even the service role may truncate the licence record'
);

insert into auth.users (id)
values
    ('31600000-0000-4000-8000-00000000000a'),
    ('31600000-0000-4000-8000-00000000000b'),
    ('31600000-0000-4000-8000-00000000000e');

insert into public.contributors (id, auth_uid, handle)
values
    ('21600000-0000-4000-8000-00000000000a', '31600000-0000-4000-8000-00000000000a', 'rights-owner-a'),
    ('21600000-0000-4000-8000-00000000000b', '31600000-0000-4000-8000-00000000000b', 'rights-owner-b');

insert into public.contribution_grants (id, contributor_id, terms_version, accepted_at, attribution_name)
values
    ('41600000-0000-4000-8000-0000000000a1', '21600000-0000-4000-8000-00000000000a', 'test-v1', '2026-09-01T00:00:00Z', 'Jane Q Example'),
    ('41600000-0000-4000-8000-0000000000a2', '21600000-0000-4000-8000-00000000000a', 'test-v1', '2026-09-02T00:00:00Z', 'Anonymous soil contributor'),
    ('41600000-0000-4000-8000-0000000000b1', '21600000-0000-4000-8000-00000000000b', 'test-v1', '2026-09-03T00:00:00Z', 'Field Notes Club');

insert into public.submissions (id, contributor_id, grant_id, geom_precise, h3_r8, h3_r6, captured_at, status)
values
    ('51600000-0000-4000-8000-0000000000a1', '21600000-0000-4000-8000-00000000000a', '41600000-0000-4000-8000-0000000000a1',
     extensions.st_setsrid(extensions.st_makepoint(-93.625, 41.9483), 4326), '88262b2a37fffff', '86262b287ffffff', now(), 'pending'),
    ('51600000-0000-4000-8000-0000000000a2', '21600000-0000-4000-8000-00000000000a', '41600000-0000-4000-8000-0000000000a2',
     extensions.st_setsrid(extensions.st_makepoint(-93.626, 41.9484), 4326), '88262b2a37fffff', '86262b287ffffff', now(), 'pending'),
    ('51600000-0000-4000-8000-0000000000b1', '21600000-0000-4000-8000-00000000000b', '41600000-0000-4000-8000-0000000000b1',
     extensions.st_setsrid(extensions.st_makepoint(36.08, -0.3031), 4326), '887a6a09ebfffff', '867a6a09fffffff', now(), 'pending');

insert into public.photos (submission_id, shot_type, storage_path)
values
    ('51600000-0000-4000-8000-0000000000a1', 'B',
     '31600000-0000-4000-8000-00000000000a/51600000-0000-4000-8000-0000000000a1/B/61600000-0000-4000-8000-0000000000a1.jpg'),
    ('51600000-0000-4000-8000-0000000000b1', 'B',
     '31600000-0000-4000-8000-00000000000b/51600000-0000-4000-8000-0000000000b1/B/61600000-0000-4000-8000-0000000000b1.jpg');

insert into storage.objects (bucket_id, name)
values
    ('incoming-photos', '31600000-0000-4000-8000-00000000000a/51600000-0000-4000-8000-0000000000a1/B/71600000-0000-4000-8000-0000000000a1.jpg'),
    ('submission-photos', '31600000-0000-4000-8000-00000000000a/51600000-0000-4000-8000-0000000000a1/B/61600000-0000-4000-8000-0000000000a1.jpg'),
    ('submission-photos', '31600000-0000-4000-8000-00000000000b/51600000-0000-4000-8000-0000000000b1/B/61600000-0000-4000-8000-0000000000b1.jpg');

create temporary table grants_before on commit drop as
select id, contributor_id, terms_version, accepted_at, data_license, photo_license
from public.contribution_grants
where contributor_id = '21600000-0000-4000-8000-00000000000a';
grant select on grants_before to service_role;

-- Only an auth user that exists can create a contributor.
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"31600000-0000-4000-8000-0000000000ff","role":"authenticated"}';
select throws_ok(
    $$insert into public.contributors (auth_uid, handle)
      values ('31600000-0000-4000-8000-0000000000ff', 'ghost-account')$$,
    '42501',
    null,
    'a token for an auth user that does not exist cannot create a contributor'
);
set local "request.jwt.claims" = '{"sub":"31600000-0000-4000-8000-00000000000e","role":"authenticated"}';
select lives_ok(
    $$insert into public.contributors (auth_uid, handle)
      values ('31600000-0000-4000-8000-00000000000e', 'rights-owner-e')$$,
    'a real auth user creates their contributor'
);

-- A withdrawal from someone with nothing stored is complete when filed.
select lives_ok(
    $$insert into public.deletion_requests (contributor_id, kind)
      values ((select public.current_contributor_id()), 'withdraw_contributions')$$,
    'a contributor with nothing stored can still ask'
);
select results_eq(
    $$select status, completed_at is not null from public.deletion_requests$$,
    $$values ('completed'::text, true)$$,
    'an empty withdrawal is complete at once and never waits in the worker queue'
);

-- Owners: create and read only their own requests, at most one open.
set local "request.jwt.claims" = '{"sub":"31600000-0000-4000-8000-00000000000a","role":"authenticated"}';
select lives_ok(
    $$insert into public.deletion_requests (contributor_id, kind)
      values ('21600000-0000-4000-8000-00000000000a', 'withdraw_contributions')$$,
    'an owner requests withdrawal of their contributions'
);
select results_eq(
    $$select kind, status, completed_at is null from public.deletion_requests$$,
    $$values ('withdraw_contributions'::text, 'pending'::text, true)$$,
    'the owner sees their pending request'
);
select throws_ok(
    $$insert into public.deletion_requests (contributor_id, kind)
      values ('21600000-0000-4000-8000-00000000000a', 'delete_account')$$,
    '23505',
    null,
    'a second open request is refused'
);
select throws_ok(
    $$insert into public.deletion_requests (contributor_id, kind)
      values ('21600000-0000-4000-8000-00000000000b', 'delete_account')$$,
    '42501',
    null,
    'nobody can file a request for someone else'
);
select throws_ok(
    $$insert into public.deletion_requests (contributor_id, kind, status)
      values ('21600000-0000-4000-8000-00000000000a', 'withdraw_contributions', 'completed')$$,
    '42501',
    null,
    'an owner cannot choose the status of a request'
);
set local "request.jwt.claims" = '{"sub":"31600000-0000-4000-8000-00000000000b","role":"authenticated"}';
select is((select count(*) from public.deletion_requests), 0::bigint, 'another contributor sees none of them');
reset role;

-- A request takes effect at once, and nothing it covers can come back.
select results_eq(
    $$select grant_id::text, reason from public.grant_withdrawals
      where grant_id::text like '41600000%' order by grant_id$$,
    $$values ('41600000-0000-4000-8000-0000000000a1', 'contributor_request'::text),
             ('41600000-0000-4000-8000-0000000000a2', 'contributor_request'::text)$$,
    'every grant the requester held is withdrawn the moment they ask'
);
select is(
    (select count(*) from public.grant_withdrawals w
     join public.deletion_requests r on r.id = w.request_id
     where r.contributor_id = '21600000-0000-4000-8000-00000000000a'),
    2::bigint,
    'each withdrawal records the request behind it'
);
select throws_ok(
    $$insert into public.submissions (id, contributor_id, grant_id, geom_precise, h3_r8, h3_r6, captured_at, status)
      values ('51600000-0000-4000-8000-0000000000a9', '21600000-0000-4000-8000-00000000000a',
              '41600000-0000-4000-8000-0000000000a1',
              extensions.st_setsrid(extensions.st_makepoint(-93.6, 41.9), 4326),
              '88262b2a37fffff', '86262b287ffffff', now(), 'pending')$$,
    'WD001',
    'contribution grant 41600000-0000-4000-8000-0000000000a1 has been withdrawn',
    'a withdrawn grant gains no submission'
);
select throws_ok(
    $$insert into public.contribution_grants (id, contributor_id, terms_version, accepted_at, attribution_name)
      values ('41600000-0000-4000-8000-0000000000a8', '21600000-0000-4000-8000-00000000000a',
              'test-v1', now() - interval '2 days', 'Anonymous soil contributor')$$,
    'WD001',
    'this contribution was withdrawn by its contributor',
    'an observation accepted before the request but synced after it is refused'
);
select throws_ok(
    $$insert into public.photos (submission_id, shot_type, storage_path)
      values ('51600000-0000-4000-8000-0000000000a2', 'A',
              '31600000-0000-4000-8000-00000000000a/51600000-0000-4000-8000-0000000000a2/A/61600000-0000-4000-8000-0000000000a2.jpg')$$,
    'WD001',
    'the contribution grant for this photo has been withdrawn',
    'a withdrawn grant gains no photo'
);
insert into public.contribution_grants (id, contributor_id, terms_version, accepted_at, attribution_name)
values ('41600000-0000-4000-8000-0000000000a3', '21600000-0000-4000-8000-00000000000a', 'test-v1',
        clock_timestamp(), 'Jane Q Example');
select lives_ok(
    $$insert into public.submissions (id, contributor_id, grant_id, geom_precise, h3_r8, h3_r6, captured_at, status)
      values ('51600000-0000-4000-8000-0000000000a3', '21600000-0000-4000-8000-00000000000a',
              '41600000-0000-4000-8000-0000000000a3',
              extensions.st_setsrid(extensions.st_makepoint(-93.6, 41.9), 4326),
              '88262b2a37fffff', '86262b287ffffff', now(), 'pending')$$,
    'a contribution accepted after a withdrawal is a new one, and is kept'
);

-- Uploads follow the same rule.
update public.service_state set capture_open = true where singleton;
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"31600000-0000-4000-8000-00000000000a","role":"authenticated"}';
select throws_ok(
    $$insert into storage.objects (bucket_id, name)
      values ('incoming-photos',
              '31600000-0000-4000-8000-00000000000a/51600000-0000-4000-8000-0000000000a2/A/71600000-0000-4000-8000-0000000000a2.jpg')$$,
    '42501',
    null,
    'an upload for a withdrawn observation is refused'
);
select lives_ok(
    $$insert into storage.objects (bucket_id, name)
      values ('incoming-photos',
              '31600000-0000-4000-8000-00000000000a/51600000-0000-4000-8000-0000000000a3/B/71600000-0000-4000-8000-0000000000a3.jpg')$$,
    'an upload for a contribution under a grant in force is accepted'
);
select is(
    public.my_submission_accepts_uploads('51600000-0000-4000-8000-0000000000b1'),
    false,
    'the upload check answers nothing about other people''s submissions'
);
reset role;

-- Grants stay immutable; withdrawals are append-only; neither can be truncated.
set local role service_role;
select throws_ok(
    $$update public.contribution_grants set attribution_name = 'Anonymous soil contributor'
      where id = '41600000-0000-4000-8000-0000000000a1'$$,
    'P0001',
    'contribution_grants are immutable',
    'even the service role cannot rewrite a grant outside account deletion'
);
select throws_ok(
    $$delete from public.contribution_grants where id = '41600000-0000-4000-8000-0000000000a2'$$,
    'P0001',
    'contribution_grants are immutable',
    'grants are never deleted'
);
do $$ begin perform set_config('gsip.redacting_attribution', 'on', true); end $$;
select throws_ok(
    $$update public.contribution_grants set terms_version = 'forged'
      where id = '41600000-0000-4000-8000-0000000000a1'$$,
    'P0001',
    'contribution_grants are immutable',
    'the redaction path cannot change licence terms'
);
select throws_ok(
    $$update public.contribution_grants set attribution_name = 'Anonymous soil contributor'
      where id = '41600000-0000-4000-8000-0000000000b1'$$,
    'P0001',
    'contribution_grants are immutable',
    'the redaction path cannot touch a grant that is not withdrawn'
);
do $$ begin perform set_config('gsip.redacting_attribution', 'off', true); end $$;
select throws_ok(
    $$delete from public.grant_withdrawals where grant_id = '41600000-0000-4000-8000-0000000000a1'$$,
    'P0001',
    'grant_withdrawals are append-only',
    'a withdrawal can never be undone by deleting it'
);
select throws_ok(
    $$update public.grant_withdrawals set reason = 'steward_action'
      where grant_id = '41600000-0000-4000-8000-0000000000a1'$$,
    'P0001',
    'grant_withdrawals are append-only',
    'a withdrawal can never be rewritten'
);
select throws_ok(
    $$truncate public.grant_withdrawals$$,
    '42501',
    null,
    'the service role cannot truncate withdrawals'
);
reset role;
select throws_ok(
    $$truncate public.contribution_grants cascade$$,
    'P0001',
    'contribution_grants cannot be truncated',
    'even the table owner cannot truncate grants'
);

-- The rights worker: claim, apply, sweep, complete.
set local role service_role;
select results_eq(
    $$select contributor_id::text, kind, auth_uid::text, attempts from public.claim_deletion_request()$$,
    $$values ('21600000-0000-4000-8000-00000000000a', 'withdraw_contributions'::text,
              '31600000-0000-4000-8000-00000000000a', 1::smallint)$$,
    'the worker claims the request with the auth user id it needs for Storage'
);
select is(
    (select count(*) from public.claim_deletion_request()),
    0::bigint,
    'a claimed request is not handed out twice'
);
select throws_ok(
    $$select public.complete_deletion_request(
        (select id from public.deletion_requests
         where contributor_id = '21600000-0000-4000-8000-00000000000a' and status = 'processing'))$$,
    '55000',
    'withdrawn contributions remain; apply the request first',
    'a request cannot complete while withdrawn contributions remain'
);
select results_eq(
    $$select withdrawn_grants, deleted_submissions from public.apply_deletion_request(
        (select id from public.deletion_requests
         where contributor_id = '21600000-0000-4000-8000-00000000000a' and status = 'processing'))$$,
    $$values (0, 2)$$,
    'applying a withdrawal deletes both submissions under the withdrawn grants'
);
select results_eq(
    $$select id::text from public.submissions where id::text like '51600000%' order by id$$,
    $$values ('51600000-0000-4000-8000-0000000000a3'), ('51600000-0000-4000-8000-0000000000b1')$$,
    'the newer contribution and other people''s contributions stay'
);
select is(
    (select count(*) from public.photos where submission_id = '51600000-0000-4000-8000-0000000000a1')
    + (select count(*) from public.prior_jobs where submission_id = '51600000-0000-4000-8000-0000000000a1'),
    0::bigint,
    'photo rows and jobs go with their submission'
);
select results_eq(
    $$select bucket_id, name from public.contributor_orphaned_objects('31600000-0000-4000-8000-00000000000a')$$,
    $$values
        ('incoming-photos'::text, '31600000-0000-4000-8000-00000000000a/51600000-0000-4000-8000-0000000000a1/B/71600000-0000-4000-8000-0000000000a1.jpg'::text),
        ('submission-photos'::text, '31600000-0000-4000-8000-00000000000a/51600000-0000-4000-8000-0000000000a1/B/61600000-0000-4000-8000-0000000000a1.jpg'::text)$$,
    'both buckets'' objects of the deleted submission are listed, not the newer contribution''s upload'
);
select results_eq(
    $$select withdrawn_grants, deleted_submissions from public.apply_deletion_request(
        (select id from public.deletion_requests
         where contributor_id = '21600000-0000-4000-8000-00000000000a' and status = 'processing'))$$,
    $$values (0, 0)$$,
    'applying again changes nothing'
);
select lives_ok(
    $$select public.complete_deletion_request(
        (select id from public.deletion_requests
         where contributor_id = '21600000-0000-4000-8000-00000000000a' and status = 'processing'))$$,
    'the worker completes the withdrawal'
);
select results_eq(
    $$select c.handle, c.auth_uid::text
      from public.contributors c where c.id = '21600000-0000-4000-8000-00000000000a'$$,
    $$values ('rights-owner-a'::text, '31600000-0000-4000-8000-00000000000a'::text)$$,
    'a withdrawal leaves the account itself in place'
);
select lives_ok(
    $$select public.complete_deletion_request(
        (select id from public.deletion_requests
         where contributor_id = '21600000-0000-4000-8000-00000000000a' and kind = 'withdraw_contributions'))$$,
    'completing again is harmless'
);

-- Attribution review: typed names wait for review; default names and withdrawn grants never do.
select results_eq(
    $$select contributor_id::text, attribution_name, grants from public.attribution_review_queue
      where contributor_id::text like '21600000%' order by contributor_id$$,
    $$values ('21600000-0000-4000-8000-00000000000a', 'Jane Q Example'::text, 1),
             ('21600000-0000-4000-8000-00000000000b', 'Field Notes Club'::text, 1)$$,
    'typed names on unwithdrawn grants wait for review'
);
insert into public.attribution_reviews (contributor_id, attribution_name, decision, reviewer)
values
    ('21600000-0000-4000-8000-00000000000a', 'Jane Q Example', 'approved', 'steward'),
    ('21600000-0000-4000-8000-00000000000b', 'Field Notes Club', 'rejected', 'steward');
select is(
    (select count(*) from public.attribution_review_queue where contributor_id::text like '21600000%'),
    0::bigint,
    'reviewed names leave the queue'
);

-- Account deletion.
reset role;
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"31600000-0000-4000-8000-00000000000a","role":"authenticated"}';
select lives_ok(
    $$insert into public.deletion_requests (contributor_id, kind)
      values ('21600000-0000-4000-8000-00000000000a', 'delete_account')$$,
    'once the withdrawal completed, the owner can ask to delete the account'
);
reset role;
select throws_ok(
    $$insert into public.contribution_grants (id, contributor_id, terms_version, accepted_at, attribution_name)
      values ('41600000-0000-4000-8000-0000000000a7', '21600000-0000-4000-8000-00000000000a',
              'test-v1', clock_timestamp(), 'Anonymous soil contributor')$$,
    'WD001',
    'this contribution was withdrawn by its contributor',
    'no new grant is accepted once an account deletion is requested'
);
set local role service_role;
select is(
    (select kind from public.claim_deletion_request()),
    'delete_account',
    'the worker claims the account deletion'
);
select results_eq(
    $$select withdrawn_grants, deleted_submissions from public.apply_deletion_request(
        (select id from public.deletion_requests
         where contributor_id = '21600000-0000-4000-8000-00000000000a' and kind = 'delete_account'))$$,
    $$values (0, 1)$$,
    'an account deletion removes every remaining contribution (its grants were withdrawn on request)'
);
select throws_ok(
    $$select public.complete_deletion_request(
        (select id from public.deletion_requests
         where contributor_id = '21600000-0000-4000-8000-00000000000a' and kind = 'delete_account'))$$,
    '55000',
    'delete the auth user before completing an account deletion',
    'the auth id is never cleared while the auth user still exists'
);
reset role;
delete from auth.users where id = '31600000-0000-4000-8000-00000000000a';  -- the worker's Admin API call
set local role service_role;
select lives_ok(
    $$select public.complete_deletion_request(
        (select id from public.deletion_requests
         where contributor_id = '21600000-0000-4000-8000-00000000000a' and kind = 'delete_account'))$$,
    'the worker completes the account deletion'
);
select results_eq(
    $$select handle like 'deleted-%', auth_uid is null, precise_location_optin
      from public.contributors where id = '21600000-0000-4000-8000-00000000000a'$$,
    $$values (true, true, false)$$,
    'the contributor row is pseudonymized and unlinked from its auth user'
);
select is(
    (select array_agg(distinct attribution_name) from public.contribution_grants
     where contributor_id = '21600000-0000-4000-8000-00000000000a'),
    array['Anonymous soil contributor'],
    'the deleted account''s attribution names are replaced with the default pseudonym'
);
select set_eq(
    $$select id, contributor_id, terms_version, accepted_at, data_license, photo_license
      from public.contribution_grants
      where contributor_id = '21600000-0000-4000-8000-00000000000a'
        and id <> '41600000-0000-4000-8000-0000000000a3'$$,
    $$select * from grants_before$$,
    'the record of what was granted (ids, terms, dates, licences) is unchanged'
);
select is(
    (select count(*) from public.attribution_reviews where contributor_id = '21600000-0000-4000-8000-00000000000a'),
    0::bigint,
    'reviews of the deleted account''s names are removed'
);
select is(
    (select count(*) from public.grant_withdrawals
     where grant_id in (select id from public.contribution_grants
                        where contributor_id = '21600000-0000-4000-8000-00000000000a')),
    3::bigint,
    'every grant of the deleted account stays withdrawn'
);
reset role;
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"31600000-0000-4000-8000-00000000000a","role":"authenticated"}';
select throws_ok(
    $$insert into public.contributors (auth_uid, handle)
      values ('31600000-0000-4000-8000-00000000000a', 'soil-back-again')$$,
    '42501',
    null,
    'a deleted account''s still-valid token cannot recreate a contributor'
);
select is(
    (select public.current_contributor_id()),
    null,
    'nor act as the pseudonymized contributor'
);
reset role;

-- The queue: requests with data first; failures wait; stuck claims are reclaimed.
insert into auth.users (id)
select ('31600000-0000-4000-8000-0000000000' || n)::uuid from generate_series(10, 12) as n;
insert into public.contributors (id, auth_uid, handle)
select ('21600000-0000-4000-8000-0000000000' || n)::uuid,
       ('31600000-0000-4000-8000-0000000000' || n)::uuid,
       'empty-account-' || n
from generate_series(10, 12) as n;
insert into public.deletion_requests (contributor_id, kind, requested_at)
select ('21600000-0000-4000-8000-0000000000' || n)::uuid, 'delete_account', now() - interval '1 day'
from generate_series(10, 12) as n;
insert into public.deletion_requests (contributor_id, kind)
values ('21600000-0000-4000-8000-00000000000b', 'withdraw_contributions');
set local role service_role;
select results_eq(
    $$select contributor_id::text, attempts from public.claim_deletion_request()$$,
    $$values ('21600000-0000-4000-8000-00000000000b', 1::smallint)$$,
    'a request with data is claimed before older empty requests'
);
select lives_ok(
    $$select public.release_deletion_request(
        (select id from public.deletion_requests where contributor_id = '21600000-0000-4000-8000-00000000000b'),
        'storage:HTTPStatusError:500')$$,
    'a failed step releases the request'
);
select results_eq(
    $$select status, last_error from public.deletion_requests
      where contributor_id = '21600000-0000-4000-8000-00000000000b'$$,
    $$values ('pending'::text, 'storage:HTTPStatusError:500'::text)$$,
    'a released request is pending again and keeps the error for the operator'
);
select is(
    (select contributor_id::text like '21600000-0000-4000-8000-00000000001%' from public.claim_deletion_request()),
    true,
    'while it waits out its retry delay, the worker moves on to other requests'
);
update public.deletion_requests set not_before = now() - interval '1 second'
where contributor_id = '21600000-0000-4000-8000-00000000000b';
select is(
    (select attempts from public.claim_deletion_request()),
    2::smallint,
    'it is retried after the wait'
);
update public.deletion_requests set claimed_at = now() - interval '2 hours'
where contributor_id = '21600000-0000-4000-8000-00000000000b';
select is(
    (select attempts from public.claim_deletion_request()),
    3::smallint,
    'a claim stuck in processing is reclaimed after an hour'
);
select throws_ok(
    $$select * from public.apply_deletion_request('00000000-0000-4000-8000-000000000000')$$,
    'P0002',
    null,
    'an unknown request is an error, not a silent no-op'
);

-- Storage catch-all: no canonical object outlives its photo row.
select results_eq(
    $$select name from public.orphaned_photo_objects() where name like '316%'$$,
    $$values ('31600000-0000-4000-8000-00000000000a/51600000-0000-4000-8000-0000000000a1/B/61600000-0000-4000-8000-0000000000a1.jpg'::text)$$,
    'a canonical object whose photo row was deleted is listed for deletion; owned objects are not'
);

-- Retention: request rows can be removed while the withdrawals they caused stay.
reset role;
select lives_ok(
    $$delete from public.deletion_requests
      where contributor_id = '21600000-0000-4000-8000-00000000000a' and kind = 'withdraw_contributions'$$,
    'an old request row can be deleted under the retention policy'
);
select is(
    (select count(*) from public.grant_withdrawals
     where grant_id in ('41600000-0000-4000-8000-0000000000a1', '41600000-0000-4000-8000-0000000000a2')),
    2::bigint,
    'its withdrawals remain as the licence record'
);

select * from finish();
rollback;
