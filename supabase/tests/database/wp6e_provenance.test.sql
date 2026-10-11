-- WP-6e: actors and human operators (I9), server-assigned provenance (I10), synthetic rows at
-- tier -1 (I11), terms versions and the acceptance window, and the server-only holdout (I15).
begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;
insert into public.terms_versions (version, published_at)
values ('test-v1', '2026-01-01T00:00:00Z') on conflict (version) do nothing;

select plan(48);

-- Clients write none of the server's provenance.
select ok(
    not has_column_privilege('authenticated', 'public.submissions', 'provenance_tier', 'insert')
    and not has_column_privilege('authenticated', 'public.submissions', 'provenance_tier', 'update')
    and not has_column_privilege('authenticated', 'public.submissions', 'actor_id', 'insert')
    and not has_column_privilege('authenticated', 'public.submissions', 'actor_id', 'update'),
    'clients cannot write a submission''s tier or actor'
);
select ok(
    not has_column_privilege('authenticated', 'public.photos', 'provenance_tier', 'insert')
    and not has_column_privilege('authenticated', 'public.photos', 'capture_evidence_private', 'insert')
    and not has_column_privilege('authenticated', 'public.photos', 'provenance_tier', 'update'),
    'clients cannot write a photo''s tier or evidence'
);
select ok(
    not has_column_privilege('authenticated', 'public.contribution_grants', 'received_at', 'insert')
    and not has_column_privilege('authenticated', 'public.gold_labels', 'holdout', 'select')
    and not has_column_privilege('anon', 'public.gold_labels', 'holdout', 'select'),
    'clients cannot set when a grant was received, nor see which labels are held out'
);
select ok(
    not has_table_privilege('authenticated', 'public.actors', 'insert')
    and not has_table_privilege('authenticated', 'public.actors', 'update')
    and not has_table_privilege('anon', 'public.actors', 'select'),
    'clients create and change no actors'
);
select ok(
    has_column_privilege('authenticated', 'public.submissions', 'ingest_path', 'insert')
    and has_column_privilege('authenticated', 'public.submissions', 'capture_method', 'insert')
    and has_column_privilege('authenticated', 'public.submissions', 'location_source', 'insert'),
    'clients may state their claims'
);

-- Actors (I9).
select is(
    (select count(*) from public.contributors c
     where (select count(*) from public.actors a
            where a.kind = 'human' and a.contributor_id = c.id) <> 1),
    0::bigint,
    'every contributor has exactly one human actor'
);
insert into auth.users (id) values ('31700000-0000-4000-8000-00000000000a');
insert into public.contributors (id, auth_uid, handle)
values ('21700000-0000-4000-8000-00000000000a', '31700000-0000-4000-8000-00000000000a', 'provenance-a');
select is(
    (select count(*) from public.actors where kind = 'human' and contributor_id = '21700000-0000-4000-8000-00000000000a'),
    1::bigint,
    'a new contributor gets a human actor'
);
select throws_ok(
    $$insert into public.actors (kind, model_family) values ('agent', 'example-model')$$,
    '23514',
    null,
    'an agent without an operator is rejected'
);
select throws_ok(
    $$insert into public.actors (kind, contributor_id) values ('agent', '21700000-0000-4000-8000-00000000000a')$$,
    '23514',
    null,
    'an agent is not a contributor in its own right'
);
insert into public.actors (id, kind, operator_id, model_family, model_version)
values (
    '71700000-0000-4000-8000-0000000000a1', 'agent',
    (select id from public.actors where kind = 'human' and contributor_id = '21700000-0000-4000-8000-00000000000a'),
    'example-model', '2026-10'
);
select throws_ok(
    $$insert into public.actors (kind, operator_id, model_family)
      values ('agent', '71700000-0000-4000-8000-0000000000a1', 'sub-agent')$$,
    '23514',
    'an operator must be a human actor',
    'an agent cannot vouch for another agent'
);
update public.contributors set auth_uid = null where id = '21700000-0000-4000-8000-00000000000a';
select results_eq(
    $$select kind, status from public.actors
      where contributor_id = '21700000-0000-4000-8000-00000000000a'
         or id = '71700000-0000-4000-8000-0000000000a1'
      order by kind$$,
    $$values ('agent'::text, 'revoked'::text), ('human'::text, 'revoked'::text)$$,
    'unlinking a deleted account revokes its human actor and every agent it operated'
);

-- Synthetic rows are exactly tier -1 (I11).
select is(
    (select count(*) from public.submissions where is_synthetic and provenance_tier <> -1)
    + (select count(*) from public.submissions where not is_synthetic and provenance_tier = -1),
    0::bigint,
    'synthetic rows, and only they, sit at tier -1'
);
select throws_ok(
    $$update public.submissions set provenance_tier = 0 where is_synthetic$$,
    '23514',
    null,
    'a synthetic row can never be raised to field data'
);
select is(
    (select count(*) from public.photos p join public.submissions s on s.id = p.submission_id
     where s.is_synthetic and p.provenance_tier <> -1),
    0::bigint,
    'photos of synthetic submissions sit at tier -1 too'
);

-- A contributor's submission: server-set actor and tier; claims recorded but never raising it.
insert into auth.users (id) values ('31700000-0000-4000-8000-00000000000b');
insert into public.contributors (id, auth_uid, handle)
values ('21700000-0000-4000-8000-00000000000b', '31700000-0000-4000-8000-00000000000b', 'provenance-b');
insert into public.contribution_grants (id, contributor_id, terms_version, accepted_at, attribution_name)
values ('41700000-0000-4000-8000-0000000000b1', '21700000-0000-4000-8000-00000000000b', 'test-v1', now(), 'Anonymous soil contributor');
update public.service_state set capture_open = true where singleton;

set local role authenticated;
set local "request.jwt.claims" = '{"sub":"31700000-0000-4000-8000-00000000000b","role":"authenticated"}';
select lives_ok(
    $$insert into public.submissions (
        id, contributor_id, grant_id, geom_precise, h3_r8, h3_r6, captured_at, status,
        ingest_path, capture_method, location_source
      ) values (
        '51700000-0000-4000-8000-0000000000b1', '21700000-0000-4000-8000-00000000000b',
        '41700000-0000-4000-8000-0000000000b1',
        extensions.st_setsrid(extensions.st_makepoint(-73.2121, 44.4759), 4326),
        '88fffffffffffff', '86fffffffffffff', now(), 'pending',
        'app', 'camera', 'device_gps'
      )$$,
    'a contributor submits with their claims'
);
select throws_ok(
    $$insert into public.submissions (
        id, contributor_id, grant_id, geom_precise, h3_r8, h3_r6, captured_at, status, provenance_tier
      ) values (
        '51700000-0000-4000-8000-0000000000b9', '21700000-0000-4000-8000-00000000000b',
        '41700000-0000-4000-8000-0000000000b1',
        extensions.st_setsrid(extensions.st_makepoint(-73.2121, 44.4759), 4326),
        '88fffffffffffff', '86fffffffffffff', now(), 'pending', 3
      )$$,
    '42501',
    null,
    'a client cannot assert a tier'
);
select throws_ok(
    $$insert into public.submissions (
        id, contributor_id, grant_id, geom_precise, h3_r8, h3_r6, captured_at, status, ingest_path
      ) values (
        '51700000-0000-4000-8000-0000000000b8', '21700000-0000-4000-8000-00000000000b',
        '41700000-0000-4000-8000-0000000000b1',
        extensions.st_setsrid(extensions.st_makepoint(-73.2121, 44.4759), 4326),
        '88fffffffffffff', '86fffffffffffff', now(), 'pending', 'satellite'
      )$$,
    '23514',
    null,
    'claims are limited to known values'
);
select results_eq(
    $$select kind, status from public.actors$$,
    $$values ('human'::text, 'active'::text)$$,
    'a client sees only its own actor'
);
reset role;
select results_eq(
    $$select s.ingest_path, s.capture_method, s.location_source, s.provenance_tier,
             s.actor_id = (select a.id from public.actors a
                           where a.kind = 'human' and a.contributor_id = s.contributor_id)
      from public.submissions s where s.id = '51700000-0000-4000-8000-0000000000b1'$$,
    $$values ('app'::text, 'camera'::text, 'device_gps'::text, 0::smallint, true)$$,
    'claims are recorded, the actor is set by the server, and the tier stays 0'
);

-- A server path may record an agent, but only one acting for the contributor (I9).
insert into public.actors (id, kind, operator_id, model_family, model_version)
values (
    '71700000-0000-4000-8000-0000000000b1', 'agent',
    (select id from public.actors where kind = 'human' and contributor_id = '21700000-0000-4000-8000-00000000000b'),
    'example-model', '2026-10'
);
select lives_ok(
    $$insert into public.submissions (
        id, contributor_id, grant_id, geom_precise, h3_r8, h3_r6, captured_at, status, actor_id
      ) values (
        '51700000-0000-4000-8000-0000000000b2', '21700000-0000-4000-8000-00000000000b',
        '41700000-0000-4000-8000-0000000000b1',
        extensions.st_setsrid(extensions.st_makepoint(-73.2121, 44.4759), 4326),
        '88fffffffffffff', '86fffffffffffff', now(), 'pending',
        '71700000-0000-4000-8000-0000000000b1'
      )$$,
    'the server may record an agent operated by the contributor''s human actor'
);
select throws_ok(
    $$insert into public.submissions (
        id, contributor_id, grant_id, geom_precise, h3_r8, h3_r6, captured_at, status, actor_id
      ) values (
        '51700000-0000-4000-8000-0000000000b3', '21700000-0000-4000-8000-00000000000b',
        '41700000-0000-4000-8000-0000000000b1',
        extensions.st_setsrid(extensions.st_makepoint(-73.2121, 44.4759), 4326),
        '88fffffffffffff', '86fffffffffffff', now(), 'pending',
        '71700000-0000-4000-8000-0000000000a1'
      )$$,
    '23514',
    'the actor must be active and act for the submission''s contributor',
    'an agent acting for someone else, or revoked, is never recorded'
);
select throws_ok(
    $$update public.submissions
      set actor_id = (select id from public.actors
                      where kind = 'human' and contributor_id = '21700000-0000-4000-8000-00000000000a')
      where id = '51700000-0000-4000-8000-0000000000b2'$$,
    '23514',
    'the actor must be active and act for the submission''s contributor',
    'a submission cannot be reassigned to another contributor''s actor'
);

-- Tier 1 needs evidence on both required shots (set by the QA worker).
insert into public.photos (submission_id, shot_type, storage_path, provenance_tier)
values
    ('51700000-0000-4000-8000-0000000000b1', 'A',
     '31700000-0000-4000-8000-00000000000b/51700000-0000-4000-8000-0000000000b1/A/61700000-0000-4000-8000-0000000000b1.jpg',
     1),
    ('51700000-0000-4000-8000-0000000000b1', 'B',
     '31700000-0000-4000-8000-00000000000b/51700000-0000-4000-8000-0000000000b1/B/61700000-0000-4000-8000-0000000000b2.jpg',
     0);
select results_eq(
    $$select shot_type, provenance_tier from public.photos
      where submission_id = '51700000-0000-4000-8000-0000000000b1' order by shot_type$$,
    $$values ('A'::text, 0::smallint), ('B'::text, 0::smallint)$$,
    'every field photo starts at tier 0, whoever inserts it'
);
set local role service_role;
update public.photos set provenance_tier = 1
where submission_id = '51700000-0000-4000-8000-0000000000b1' and shot_type = 'B';
select is(
    (select provenance_tier from public.submissions where id = '51700000-0000-4000-8000-0000000000b1'),
    0::smallint,
    'one corroborated shot is not enough'
);
update public.photos set provenance_tier = 1
where submission_id = '51700000-0000-4000-8000-0000000000b1' and shot_type = 'A';
select is(
    (select provenance_tier from public.submissions where id = '51700000-0000-4000-8000-0000000000b1'),
    1::smallint,
    'shots A and B both corroborated make the submission tier 1'
);
delete from public.photos where submission_id = '51700000-0000-4000-8000-0000000000b1' and shot_type = 'A';
select is(
    (select provenance_tier from public.submissions where id = '51700000-0000-4000-8000-0000000000b1'),
    0::smallint,
    'without both required shots the tier falls back to 0'
);
select throws_ok(
    $$update public.photos set capture_evidence_private = '{"exif_gps_present": true, "latitude": 44.47}'
      where submission_id = '51700000-0000-4000-8000-0000000000b1'$$,
    '23514',
    null,
    'capture evidence can never hold coordinates or other unlisted fields'
);
select lives_ok(
    $$update public.photos set capture_evidence_private =
        '{"evidence_version": "exif-v1", "exif_time_present": true, "exif_time_absolute": true,
          "exif_time_delta_s": 42, "exif_gps_present": true, "exif_gps_distance_m": 12.5}'
      where submission_id = '51700000-0000-4000-8000-0000000000b1'$$,
    'allowlisted evidence is accepted'
);
reset role;

-- Terms versions and the acceptance window (I9).
insert into public.terms_versions (version, published_at, retired_at)
values
    ('test-future', now() + interval '1 day', null),
    ('test-retired', '2026-01-01T00:00:00Z', now() - interval '1 day');
select throws_ok(
    $$insert into public.contribution_grants (contributor_id, terms_version, accepted_at, attribution_name)
      values ('21700000-0000-4000-8000-00000000000b', 'never-published', now(), 'Anonymous soil contributor')$$,
    '23503',
    null,
    'even the server cannot record a grant under a terms version that does not exist'
);
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"31700000-0000-4000-8000-00000000000b","role":"authenticated"}';
select throws_ok(
    $$insert into public.contribution_grants (contributor_id, terms_version, accepted_at, attribution_name)
      values ('21700000-0000-4000-8000-00000000000b', 'never-published', now(), 'Anonymous soil contributor')$$,
    '42501',
    null,
    'a client cannot cite an unknown terms version'
);
select throws_ok(
    $$insert into public.contribution_grants (contributor_id, terms_version, accepted_at, attribution_name)
      values ('21700000-0000-4000-8000-00000000000b', 'test-future', now(), 'Anonymous soil contributor')$$,
    '42501',
    null,
    'a version not yet published cannot be accepted'
);
select throws_ok(
    $$insert into public.contribution_grants (contributor_id, terms_version, accepted_at, attribution_name)
      values ('21700000-0000-4000-8000-00000000000b', 'test-retired', now(), 'Anonymous soil contributor')$$,
    '42501',
    null,
    'a retired version cannot be accepted'
);
select throws_ok(
    $$insert into public.contribution_grants (contributor_id, terms_version, accepted_at, attribution_name)
      values ('21700000-0000-4000-8000-00000000000b', 'test-v1', now() - interval '31 days', 'Anonymous soil contributor')$$,
    '42501',
    null,
    'an acceptance older than 30 days is refused'
);
select throws_ok(
    $$insert into public.contribution_grants (contributor_id, terms_version, accepted_at, attribution_name)
      values ('21700000-0000-4000-8000-00000000000b', 'test-v1', now() + interval '1 hour', 'Anonymous soil contributor')$$,
    '42501',
    null,
    'an acceptance in the future is refused'
);
select throws_ok(
    $$insert into public.contribution_grants (contributor_id, terms_version, accepted_at, attribution_name, received_at)
      values ('21700000-0000-4000-8000-00000000000b', 'test-v1', now(), 'Anonymous soil contributor', now() - interval '1 year')$$,
    '42501',
    null,
    'a client cannot say when the server received a grant'
);
select lives_ok(
    $$insert into public.contribution_grants (id, contributor_id, terms_version, accepted_at, attribution_name)
      values ('41700000-0000-4000-8000-0000000000b2', '21700000-0000-4000-8000-00000000000b',
              'test-v1', now() - interval '29 days', 'Anonymous soil contributor')$$,
    'a published version accepted within the window is recorded'
);
select results_eq(
    $$select terms_version from public.contribution_grants where id = '41700000-0000-4000-8000-0000000000b2'$$,
    $$values ('test-v1'::text)$$,
    'the owner sees their grant'
);
select is(
    (select count(*) from public.terms_versions where version = 'test-v1'),
    1::bigint,
    'anyone can read which terms versions are published'
);
reset role;
select ok(
    (select received_at between now() - interval '1 minute' and now() + interval '1 minute'
     from public.contribution_grants where id = '41700000-0000-4000-8000-0000000000b2'),
    'the server records when it received the grant'
);
select throws_ok(
    $$update public.contribution_grants set received_at = now() where id = '41700000-0000-4000-8000-0000000000b2'$$,
    'P0001',
    'contribution_grants are immutable',
    'the receipt time is immutable like the rest of the grant'
);

-- The holdout is server-only (I15).
insert into public.gold_labels (submission_id, lab_name, property, value, unit, depth_top_cm, depth_bottom_cm, holdout)
values ('51700000-0000-4000-8000-0000000000b1', 'Example Lab', 'soc', 21.5, 'g/kg', 0, 5, true);
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"31700000-0000-4000-8000-00000000000b","role":"authenticated"}';
select results_eq(
    $$select property, value from public.gold_labels$$,
    $$values ('soc'::text, 21.5::double precision)$$,
    'the owner still sees their own laboratory result'
);
select throws_ok(
    $$select holdout from public.gold_labels$$,
    '42501',
    null,
    'but never whether it is held out'
);
reset role;
select is(
    (select count(*) from public.gold_labels where holdout and submission_id = '51700000-0000-4000-8000-0000000000b1'),
    1::bigint,
    'the server keeps the holdout flag'
);

-- Synthetic is permanent, and the reserved tiers wait for their evidence paths (I10, I11).
select throws_ok(
    $$update public.photos set provenance_tier = 1
      where submission_id in (select id from public.submissions where is_synthetic)$$,
    '23514',
    'a synthetic photo stays at tier -1',
    'a synthetic photo can never be corroborated'
);
select throws_ok(
    $$update public.photos set provenance_tier = -1
      where submission_id = '51700000-0000-4000-8000-0000000000b1'$$,
    '23514',
    'tier -1 is reserved for synthetic data',
    'tier -1 is never used to file field data'
);
select throws_ok(
    $$update public.submissions set provenance_tier = 2 where id = '51700000-0000-4000-8000-0000000000b1'$$,
    '23514',
    null,
    'tiers 2 and 3 stay reserved until their evidence paths exist'
);
select throws_ok(
    $$update public.submissions set is_synthetic = false where is_synthetic$$,
    '23514',
    'a synthetic row can never become field data',
    'a synthetic row stays synthetic'
);
update public.submissions set is_synthetic = true where id = '51700000-0000-4000-8000-0000000000b1';
select results_eq(
    $$select s.provenance_tier,
             (select array_agg(distinct p.provenance_tier) from public.photos p where p.submission_id = s.id)
      from public.submissions s where s.id = '51700000-0000-4000-8000-0000000000b1'$$,
    $$values (-1::smallint, array[-1::smallint])$$,
    'quarantining a field row as synthetic takes it and its photos to tier -1'
);

select * from finish();
rollback;
