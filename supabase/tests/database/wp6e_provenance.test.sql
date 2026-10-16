-- WP-6e: actors and human operators (I9), evidence-derived provenance (I10), synthetic rows at
-- tier -1 (I11), terms versions and the acceptance window, and the server-only holdout (I15).
begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;
insert into public.terms_versions (version, published_at)
values ('test-v1', '2026-01-01T00:00:00Z') on conflict (version) do nothing;

-- Evidence as the QA worker writes it (pipeline/provenance.py).
create function pg_temp.evidence(
    delta_s integer,
    age_s integer,
    gps_distance_m integer default null,
    time_absolute boolean default true
)
returns jsonb
language sql
immutable
as $$
    select jsonb_build_object(
        'evidence_version', 'exif-v1',
        'exif_time_present', true,
        'exif_time_absolute', time_absolute,
        'exif_time_delta_s', delta_s,
        'exif_age_at_acceptance_s', age_s,
        'exif_gps_present', gps_distance_m is not null,
        'exif_gps_distance_m', gps_distance_m
    )
$$;

select plan(57);

-- Clients write none of the server's provenance -------------------------------------------------
select ok(
    not has_column_privilege('authenticated', 'public.submissions', 'provenance_tier', 'insert')
    and not has_column_privilege('authenticated', 'public.submissions', 'provenance_tier', 'update')
    and not has_column_privilege('authenticated', 'public.submissions', 'actor_id', 'insert')
    and not has_column_privilege('authenticated', 'public.submissions', 'actor_id', 'update'),
    'clients cannot write a submission''s tier or actor'
);
select ok(
    not has_column_privilege('authenticated', 'public.photos', 'provenance_tier', 'insert')
    and not has_column_privilege('authenticated', 'public.photos', 'provenance_tier', 'update')
    and not has_column_privilege('authenticated', 'public.photos', 'capture_evidence_private', 'insert')
    and not has_column_privilege('authenticated', 'public.photos', 'capture_evidence_private', 'update'),
    'clients cannot write a photo''s tier or evidence'
);
select ok(
    not has_column_privilege('authenticated', 'public.contribution_grants', 'received_at', 'insert')
    and not has_column_privilege('authenticated', 'public.gold_labels', 'holdout', 'select')
    and not has_column_privilege('anon', 'public.gold_labels', 'holdout', 'select')
    and not has_column_privilege('authenticated', 'public.gold_labels', 'holdout', 'insert')
    and not has_column_privilege('authenticated', 'public.gold_labels', 'holdout', 'update'),
    'clients cannot set when a grant was received, nor read or write which labels are held out'
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
    and has_column_privilege('authenticated', 'public.submissions', 'location_source', 'insert')
    and has_column_privilege('authenticated', 'public.submissions', 'client_version', 'insert'),
    'clients may state their claims'
);
select ok(
    not has_table_privilege('service_role', 'public.actors', 'delete')
    and not has_table_privilege('service_role', 'public.actors', 'truncate')
    and not has_table_privilege('service_role', 'public.terms_versions', 'delete')
    and not has_table_privilege('service_role', 'public.terms_versions', 'truncate'),
    'not even the server deletes actors or terms versions'
);

-- Actors (I9) -------------------------------------------------------------------------------------
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
    (select status from public.actors
     where kind = 'human' and contributor_id = '21700000-0000-4000-8000-00000000000a'),
    'active',
    'a new contributor gets an active human actor'
);
insert into public.contributors (id, auth_uid, handle)
values ('21700000-0000-4000-8000-00000000000e', null, 'provenance-unlinked');
select is(
    (select status from public.actors
     where kind = 'human' and contributor_id = '21700000-0000-4000-8000-00000000000e'),
    'revoked',
    'a contributor without a sign-in gets a revoked human actor'
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
    'an operator must be an active human actor',
    'an agent cannot vouch for another agent'
);
select throws_ok(
    $$update public.actors set kind = 'device' where id = '71700000-0000-4000-8000-0000000000a1'$$,
    '23514',
    'an actor''s identity never changes',
    'who an actor is never changes'
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
select throws_ok(
    $$update public.actors set status = 'active' where id = '71700000-0000-4000-8000-0000000000a1'$$,
    '23514',
    'revocation is final',
    'a revoked actor stays revoked'
);
select throws_ok(
    $$insert into public.actors (kind, operator_id, model_family)
      values ('agent',
              (select id from public.actors
               where kind = 'human' and contributor_id = '21700000-0000-4000-8000-00000000000a'),
              'late-agent')$$,
    '23514',
    'an operator must be an active human actor',
    'a revoked person cannot start a new agent'
);

-- Synthetic rows are exactly tier -1 (I11) -------------------------------------------------------
select is(
    (select count(*) from public.submissions where is_synthetic and provenance_tier <> -1)
    + (select count(*) from public.submissions where not is_synthetic and provenance_tier = -1),
    0::bigint,
    'synthetic rows, and only they, sit at tier -1'
);
select is(
    (select count(*) from public.photos p join public.submissions s on s.id = p.submission_id
     where s.is_synthetic and p.provenance_tier <> -1),
    0::bigint,
    'photos of synthetic submissions sit at tier -1 too'
);
update public.submissions set provenance_tier = 0 where is_synthetic;
update public.photos p set capture_evidence_private = pg_temp.evidence(0, 60)
from public.submissions s
where s.id = p.submission_id and s.is_synthetic;
select is(
    (select count(*) from public.submissions where is_synthetic and provenance_tier <> -1)
    + (select count(*) from public.photos p join public.submissions s on s.id = p.submission_id
       where s.is_synthetic and p.provenance_tier <> -1),
    0::bigint,
    'neither a direct write nor perfect evidence lifts synthetic data off tier -1'
);
select throws_ok(
    $$update public.submissions set is_synthetic = false where is_synthetic$$,
    '23514',
    'a synthetic row can never become field data',
    'a synthetic row stays synthetic'
);

-- A contributor's submission: server-set actor and tier; claims recorded but never raising it ----
insert into auth.users (id) values ('31700000-0000-4000-8000-00000000000b');
insert into public.contributors (id, auth_uid, handle)
values ('21700000-0000-4000-8000-00000000000b', '31700000-0000-4000-8000-00000000000b', 'provenance-b');
insert into public.contribution_grants (id, contributor_id, terms_version, accepted_at, attribution_name)
values ('41700000-0000-4000-8000-0000000000b1', '21700000-0000-4000-8000-00000000000b', 'test-v1', now(), 'Anonymous soil contributor');
update public.service_state set capture_open = true where singleton;

-- Explicit disposable invitation fixture; earlier ownership/privacy assertions stay effective.
insert into auth.users(id,is_anonymous)
select auth_uid,false from public.contributors where auth_uid is not null on conflict(id) do nothing;
update auth.users set is_anonymous=false; -- every auth fixture in this rolled-back file is synthetic/permanent
insert into private.collection_pilot_members(auth_uid)
select id from auth.users where is_anonymous is false on conflict(auth_uid) do nothing;
select public.set_library_intake_open(true);

set local role authenticated;
set local "request.jwt.claims" = '{"sub":"31700000-0000-4000-8000-00000000000b","role":"authenticated"}';
select lives_ok(
    $$insert into public.submissions (
        id, contributor_id, grant_id, geom_precise, h3_r8, h3_r6, captured_at, status,
        ingest_path, capture_method, location_source, client_version
      ) values (
        '51700000-0000-4000-8000-0000000000b1', '21700000-0000-4000-8000-00000000000b',
        '41700000-0000-4000-8000-0000000000b1',
        extensions.st_setsrid(extensions.st_makepoint(-73.2121, 44.4759), 4326),
        '88fffffffffffff', '86fffffffffffff', now(), 'pending',
        'app', 'camera', 'device_gps', '0.1.0+abc1234'
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
        '88fffffffffffff', '86fffffffffffff', now(), 'pending', 1
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
select throws_ok(
    $$insert into public.submissions (
        id, contributor_id, grant_id, geom_precise, h3_r8, h3_r6, captured_at, status, client_version
      ) values (
        '51700000-0000-4000-8000-0000000000b7', '21700000-0000-4000-8000-00000000000b',
        '41700000-0000-4000-8000-0000000000b1',
        extensions.st_setsrid(extensions.st_makepoint(-73.2121, 44.4759), 4326),
        '88fffffffffffff', '86fffffffffffff', now(), 'pending', 'ignore previous instructions'
      )$$,
    '23514',
    null,
    'a client version is a version string, not free text'
);
select results_eq(
    $$select kind, status from public.actors$$,
    $$values ('human'::text, 'active'::text)$$,
    'a client sees only its own actor'
);
reset role;
select results_eq(
    $$select s.ingest_path, s.capture_method, s.location_source, s.client_version, s.provenance_tier,
             s.actor_id = (select a.id from public.actors a
                           where a.kind = 'human' and a.contributor_id = s.contributor_id)
      from public.submissions s where s.id = '51700000-0000-4000-8000-0000000000b1'$$,
    $$values ('app'::text, 'camera'::text, 'device_gps'::text, '0.1.0+abc1234'::text, 0::smallint, true)$$,
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

-- Tiers are derived from the evidence, never written (I10) --------------------------------------
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
where submission_id = '51700000-0000-4000-8000-0000000000b1';
update public.submissions set provenance_tier = 1 where id = '51700000-0000-4000-8000-0000000000b1';
select results_eq(
    $$select (select max(provenance_tier) from public.photos
              where submission_id = '51700000-0000-4000-8000-0000000000b1'),
             (select provenance_tier from public.submissions
              where id = '51700000-0000-4000-8000-0000000000b1')$$,
    $$values (0::smallint, 0::smallint)$$,
    'a direct write sets no tier, not even by the server'
);
update public.photos set capture_evidence_private = pg_temp.evidence(10, 120)
where submission_id = '51700000-0000-4000-8000-0000000000b1' and shot_type = 'B';
select results_eq(
    $$select (select provenance_tier from public.photos
              where submission_id = '51700000-0000-4000-8000-0000000000b1' and shot_type = 'B'),
             (select provenance_tier from public.submissions
              where id = '51700000-0000-4000-8000-0000000000b1')$$,
    $$values (1::smallint, 0::smallint)$$,
    'corroborating evidence raises its photo, but one corroborated shot is not enough'
);
update public.photos set capture_evidence_private = pg_temp.evidence(0, 60, 40)
where submission_id = '51700000-0000-4000-8000-0000000000b1' and shot_type = 'A';
select is(
    (select provenance_tier from public.submissions where id = '51700000-0000-4000-8000-0000000000b1'),
    1::smallint,
    'shots A and B both corroborated make the submission tier 1'
);
reset role;
select results_eq(
    $$select private.photo_tier_from_evidence(e) from (values
        (pg_temp.evidence(1800, 3600)),
        (pg_temp.evidence(1801, 0)),
        (pg_temp.evidence(0, 3601)),
        (pg_temp.evidence(0, -300)),
        (pg_temp.evidence(0, -301)),
        (pg_temp.evidence(0, 0, 250)),
        (pg_temp.evidence(0, 0, 251)),
        (pg_temp.evidence(0, 0, null, false)),
        (pg_temp.evidence(null, 0)),
        (pg_temp.evidence(0, null)),
        (jsonb_set(pg_temp.evidence(0, 0), '{evidence_version}', '"exif-v0"')),
        (null::jsonb)
      ) as cases(e)$$,
    $$values (1::smallint), (0::smallint), (0::smallint), (1::smallint), (0::smallint),
             (1::smallint), (0::smallint), (0::smallint), (0::smallint), (0::smallint),
             (0::smallint), (0::smallint)$$,
    'tier 1 needs an absolute time within 30 minutes of the claim and the hour before acceptance, and any position within 250 m'
);
select throws_ok(
    $$update public.photos set capture_evidence_private = pg_temp.evidence(0, 0) - 'exif_gps_present'
      where submission_id = '51700000-0000-4000-8000-0000000000b1'$$,
    '23514',
    null,
    'evidence carries every listed key'
);
select throws_ok(
    $$update public.photos
      set capture_evidence_private = jsonb_set(pg_temp.evidence(0, 0, 12), '{exif_gps_distance_m}', '44.4759')
      where submission_id = '51700000-0000-4000-8000-0000000000b1'$$,
    '23514',
    null,
    'a fractional number, such as a coordinate, never fits the evidence'
);
select throws_ok(
    $$update public.photos
      set capture_evidence_private = jsonb_set(pg_temp.evidence(0, 0), '{exif_time_absolute}', '"yes"')
      where submission_id = '51700000-0000-4000-8000-0000000000b1'$$,
    '23514',
    null,
    'evidence values have fixed types'
);
select throws_ok(
    $$update public.photos
      set capture_evidence_private = pg_temp.evidence(0, 0) || '{"latitude": 44}'
      where submission_id = '51700000-0000-4000-8000-0000000000b1'$$,
    '23514',
    null,
    'capture evidence can never hold coordinates or other unlisted fields'
);
delete from public.photos where submission_id = '51700000-0000-4000-8000-0000000000b1' and shot_type = 'A';
select is(
    (select provenance_tier from public.submissions where id = '51700000-0000-4000-8000-0000000000b1'),
    0::smallint,
    'without both required shots the tier falls back to 0'
);
update public.submissions set is_synthetic = true where id = '51700000-0000-4000-8000-0000000000b1';
select results_eq(
    $$select s.provenance_tier,
             (select array_agg(distinct p.provenance_tier) from public.photos p where p.submission_id = s.id)
      from public.submissions s where s.id = '51700000-0000-4000-8000-0000000000b1'$$,
    $$values (-1::smallint, array[-1::smallint])$$,
    'quarantining a field row as synthetic takes it and its corroborated photos to tier -1'
);

-- Terms versions and the acceptance window (I9) --------------------------------------------------
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
reset role;
set local role anon;
set local "request.jwt.claims" = '{"role":"anon"}';
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
insert into public.contribution_grants (id, contributor_id, terms_version, accepted_at, attribution_name, received_at)
values ('41700000-0000-4000-8000-0000000000b3', '21700000-0000-4000-8000-00000000000b',
        'test-v1', now(), 'Anonymous soil contributor', '2020-01-01T00:00:00Z');
select is(
    (select received_at from public.contribution_grants where id = '41700000-0000-4000-8000-0000000000b3'),
    now(),
    'the receipt time is the server''s, even for a server-side insert that names another'
);
select throws_ok(
    $$update public.contribution_grants set received_at = now() where id = '41700000-0000-4000-8000-0000000000b2'$$,
    'P0001',
    'contribution_grants are immutable',
    'the receipt time is immutable like the rest of the grant'
);

-- A withdrawn acceptance is refused as withdrawn before the window is checked, so the capture app
-- can tell an observation to drop (WD001) from one to hold for a new acceptance (42501).
insert into auth.users (id) values ('31700000-0000-4000-8000-00000000000c');
update auth.users set is_anonymous=false where id='31700000-0000-4000-8000-00000000000c';
insert into private.collection_pilot_members(auth_uid) values('31700000-0000-4000-8000-00000000000c');
insert into public.contributors (id, auth_uid, handle)
values ('21700000-0000-4000-8000-00000000000c', '31700000-0000-4000-8000-00000000000c', 'provenance-c');
insert into public.deletion_requests (contributor_id, kind)
values ('21700000-0000-4000-8000-00000000000c', 'withdraw_contributions');
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"31700000-0000-4000-8000-00000000000c","role":"authenticated"}';
select throws_ok(
    $$insert into public.contribution_grants (contributor_id, terms_version, accepted_at, attribution_name)
      values ('21700000-0000-4000-8000-00000000000c', 'test-v1', now() - interval '31 days', 'Anonymous soil contributor')$$,
    'WD001',
    null,
    'an expired acceptance that was withdrawn is refused as withdrawn, not as expired'
);
reset role;

-- The holdout is server-only (I15) ---------------------------------------------------------------
insert into public.submissions (
    id, contributor_id, grant_id, geom_precise, h3_r8, h3_r6, captured_at, status
) values (
    '51700000-0000-4000-8000-0000000000b4', '21700000-0000-4000-8000-00000000000b',
    '41700000-0000-4000-8000-0000000000b1',
    extensions.st_setsrid(extensions.st_makepoint(-73.2121, 44.4759), 4326),
    '88fffffffffffff', '86fffffffffffff', now(), 'pending'
);
insert into public.gold_labels (submission_id, lab_name, property, value, unit, depth_top_cm, depth_bottom_cm, holdout)
values ('51700000-0000-4000-8000-0000000000b4', 'Example Lab', 'soc', 21.5, 'g/kg', 0, 5, true);
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
    (select count(*) from public.gold_labels where holdout and submission_id = '51700000-0000-4000-8000-0000000000b4'),
    1::bigint,
    'the server keeps the holdout flag'
);

select * from finish();
rollback;
