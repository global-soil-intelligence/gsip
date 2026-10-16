-- WP-6e applied to data written before it (before_20261010150000_wp6e_provenance.sql): the
-- backfill, the retired legacy terms versions, and an account deletion of a pre-WP-6e grant.
begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;

select plan(13);

-- Actors -----------------------------------------------------------------------------------------
select results_eq(
    $$select c.handle, a.status from public.actors a
      join public.contributors c on c.id = a.contributor_id
      where a.kind = 'human' order by c.handle$$,
    $$values ('deleted-d20000000000400080000000'::text, 'revoked'::text),
             ('legacy-one'::text, 'active'::text),
             ('legacy-three'::text, 'active'::text),
             ('synthetic-farmer'::text, 'active'::text)$$,
    'every legacy contributor has one human actor, revoked where the account was already deleted'
);

-- Submissions and photos -------------------------------------------------------------------------
select results_eq(
    $$select s.id::text, s.provenance_tier,
             s.actor_id = (select a.id from public.actors a
                           where a.kind = 'human' and a.contributor_id = s.contributor_id),
             s.ingest_path, s.capture_method, s.location_source, s.client_version
      from public.submissions s order by s.id$$,
    $$values ('b1000000-0000-4000-8000-000000000001'::text, 0::smallint, true,
              'web'::text, 'unknown'::text, 'unknown'::text, null::text),
             ('b1000000-0000-4000-8000-000000000005'::text, -1::smallint, true,
              'web'::text, 'unknown'::text, 'unknown'::text, null::text)$$,
    'legacy submissions record their human actor, unknown claims, tier 0 or -1 when synthetic'
);
select results_eq(
    $$select p.submission_id::text, p.shot_type, p.provenance_tier, p.capture_evidence_private
      from public.photos p order by p.submission_id, p.shot_type$$,
    $$values ('b1000000-0000-4000-8000-000000000001'::text, 'A'::text, 0::smallint, null::jsonb),
             ('b1000000-0000-4000-8000-000000000001'::text, 'B'::text, 0::smallint, null::jsonb),
             ('b1000000-0000-4000-8000-000000000005'::text, 'A'::text, -1::smallint, null::jsonb),
             ('b1000000-0000-4000-8000-000000000005'::text, 'B'::text, -1::smallint, null::jsonb)$$,
    'legacy photos have no evidence: tier 0, or -1 for synthetic data'
);
select is(
    (select count(*) from public.gold_labels where not holdout),
    1::bigint,
    'legacy laboratory results are not held out'
);

-- Terms versions ---------------------------------------------------------------------------------
select results_eq(
    $$select version, published_at, retired_at is not null from public.terms_versions order by version$$,
    $$values ('2026-07-22'::text, '2026-07-22T00:00:00Z'::timestamptz, true),
             ('2026-07-22-v1'::text, '2026-07-22T00:00:00Z'::timestamptz, false),
             ('whatever-i-like'::text, '2026-07-22T00:00:00Z'::timestamptz, true)$$,
    'the in-app version stays current; versions known only from legacy grants are retired, revealing no acceptance time'
);
select is(
    (select count(*) from public.contribution_grants where received_at is null),
    3::bigint,
    'legacy grants keep an unknown receipt time'
);

-- Explicit disposable invitation for the historical acceptance case; no deployment backfill.
update auth.users set is_anonymous=false where id='e1000000-0000-4000-8000-000000000003';
insert into private.collection_pilot_members(auth_uid) values('e1000000-0000-4000-8000-000000000003');
select public.set_library_intake_open(true);
update public.service_state set capture_open = true where singleton;
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"e1000000-0000-4000-8000-000000000003","role":"authenticated"}';
select throws_ok(
    $$insert into public.contribution_grants (contributor_id, terms_version, accepted_at, attribution_name)
      values ('d1000000-0000-4000-8000-000000000003', 'whatever-i-like', now(), 'Legacy Three')$$,
    '42501',
    null,
    'no new grant can cite a version known only from legacy grants'
);
select lives_ok(
    $$insert into public.contribution_grants (id, contributor_id, terms_version, accepted_at, attribution_name)
      values ('f1000000-0000-4000-8000-000000000033', 'd1000000-0000-4000-8000-000000000003',
              '2026-07-22-v1', now(), 'Legacy Three')$$,
    'a legacy contributor accepts the current version'
);
reset role;
select ok(
    (select received_at = now() from public.contribution_grants
     where id = 'f1000000-0000-4000-8000-000000000033'),
    'and the server records when it received that grant'
);

-- An account deletion still completes for a grant made before WP-6e (no receipt time) ------------
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"e1000000-0000-4000-8000-000000000001","role":"authenticated"}';
select lives_ok(
    $$insert into public.deletion_requests (contributor_id, kind)
      values ('d1000000-0000-4000-8000-000000000001', 'delete_account')$$,
    'a legacy contributor asks to delete the account'
);
reset role;
set local role service_role;
select results_eq(
    $$select withdrawn_grants, deleted_submissions from public.apply_deletion_request(
        (select request_id from public.claim_deletion_request()))$$,
    $$values (0, 1)$$,
    'the worker removes the legacy observation (its grant was withdrawn on request)'
);
reset role;
delete from auth.users where id = 'e1000000-0000-4000-8000-000000000001';  -- the worker's Admin API call
set local role service_role;
select lives_ok(
    $$select public.complete_deletion_request(
        (select id from public.deletion_requests
         where contributor_id = 'd1000000-0000-4000-8000-000000000001'))$$,
    'the worker completes the deletion, redacting a grant that has no receipt time'
);
reset role;
select results_eq(
    $$select g.attribution_name, g.received_at is null, c.auth_uid is null, a.status
      from public.contribution_grants g
      join public.contributors c on c.id = g.contributor_id
      join public.actors a on a.kind = 'human' and a.contributor_id = c.id
      where g.id = 'f1000000-0000-4000-8000-000000000001'$$,
    $$values ('Anonymous soil contributor'::text, true, true, 'revoked'::text)$$,
    'the legacy grant is pseudonymized, the contributor unlinked and its actor revoked'
);

select * from finish();
rollback;
