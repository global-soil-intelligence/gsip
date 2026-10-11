-- WP-6b acceptance: path binding, finalize and settle, the capture gate, k-anonymous cells,
-- attribution safety and the colour-space metadata allowlist.
begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;

select plan(42);

-- Fixtures (as the migration owner): two contributors, each with a grant and a pending submission.
insert into public.contributors (id, auth_uid, handle)
values
    ('21000000-0000-4000-8000-000000000001', '31000000-0000-4000-8000-000000000001', 'wp6b-owner-a'),
    ('21000000-0000-4000-8000-000000000002', '31000000-0000-4000-8000-000000000002', 'wp6b-owner-b');
insert into public.contribution_grants (id, contributor_id, terms_version, accepted_at, attribution_name)
values
    ('41000000-0000-4000-8000-000000000001', '21000000-0000-4000-8000-000000000001', 'test-v1', now(), 'Anonymous soil contributor'),
    ('41000000-0000-4000-8000-000000000002', '21000000-0000-4000-8000-000000000002', 'test-v1', now(), 'Anonymous soil contributor');
insert into public.submissions (id, contributor_id, grant_id, geom_precise, captured_at, status)
values
    ('51000000-0000-4000-8000-000000000001', '21000000-0000-4000-8000-000000000001', '41000000-0000-4000-8000-000000000001', extensions.st_setsrid(extensions.st_makepoint(-73.21, 44.48), 4326), now(), 'pending'),
    ('51000000-0000-4000-8000-000000000002', '21000000-0000-4000-8000-000000000002', '41000000-0000-4000-8000-000000000002', extensions.st_setsrid(extensions.st_makepoint(-72.58, 44.26), 4326), now(), 'pending');
update public.service_state set capture_open = true where singleton;

-- ---------------------------------------------------------------------------------------------
-- Path binding (launch blocker 4)
-- ---------------------------------------------------------------------------------------------
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"31000000-0000-4000-8000-000000000001","role":"authenticated"}';

select lives_ok(
    $$insert into public.photos (submission_id, shot_type, storage_path) values (
        '51000000-0000-4000-8000-000000000001', 'A',
        '31000000-0000-4000-8000-000000000001/51000000-0000-4000-8000-000000000001/A/61000000-0000-4000-8000-00000000000a.jpg')$$,
    'owner inserts a photo row at its bound path'
);
select throws_ok(
    $$insert into public.photos (submission_id, shot_type, storage_path) values (
        '51000000-0000-4000-8000-000000000001', 'B',
        '31000000-0000-4000-8000-000000000002/51000000-0000-4000-8000-000000000001/B/61000000-0000-4000-8000-00000000000b.jpg')$$,
    '23514',
    'photo storage_path must be {auth_uid}/{submission_id}/{shot_type}/{uuid}.jpg',
    'a path naming another user is rejected'
);
select throws_ok(
    $$insert into public.photos (submission_id, shot_type, storage_path) values (
        '51000000-0000-4000-8000-000000000001', 'B',
        '31000000-0000-4000-8000-000000000001/51000000-0000-4000-8000-000000000002/B/61000000-0000-4000-8000-00000000000b.jpg')$$,
    '23514',
    'photo storage_path must be {auth_uid}/{submission_id}/{shot_type}/{uuid}.jpg',
    'a path naming another submission is rejected'
);
select throws_ok(
    $$insert into public.photos (submission_id, shot_type, storage_path) values (
        '51000000-0000-4000-8000-000000000001', 'B',
        '31000000-0000-4000-8000-000000000001/51000000-0000-4000-8000-000000000001/C/61000000-0000-4000-8000-00000000000b.jpg')$$,
    '23514',
    'photo storage_path must be {auth_uid}/{submission_id}/{shot_type}/{uuid}.jpg',
    'a path naming another shot is rejected'
);
select throws_ok(
    $$insert into public.photos (submission_id, shot_type, storage_path) values (
        '51000000-0000-4000-8000-000000000001', 'B',
        '31000000-0000-4000-8000-000000000001/51000000-0000-4000-8000-000000000001/B/photo.jpg')$$,
    '23514',
    'photo storage_path must be {auth_uid}/{submission_id}/{shot_type}/{uuid}.jpg',
    'a non-UUID object name is rejected'
);
select throws_ok(
    $$insert into public.photos (submission_id, shot_type, storage_path) values (
        '51000000-0000-4000-8000-000000000001', 'B',
        '31000000-0000-4000-8000-000000000001/51000000-0000-4000-8000-000000000001/B/../../../31000000-0000-4000-8000-000000000002/51000000-0000-4000-8000-000000000002/B/61000000-0000-4000-8000-00000000000b.jpg')$$,
    '23514',
    'photo storage_path must be {auth_uid}/{submission_id}/{shot_type}/{uuid}.jpg',
    'a path with dot-dot segments is rejected'
);
select lives_ok(
    $$insert into storage.objects (bucket_id, name, owner) values ('incoming-photos',
        '31000000-0000-4000-8000-000000000001/51000000-0000-4000-8000-000000000001/B/61000000-0000-4000-8000-00000000000b.jpg',
        '31000000-0000-4000-8000-000000000001')$$,
    'owner uploads to the bound quarantine path of their own submission'
);
select throws_ok(
    $$insert into storage.objects (bucket_id, name, owner) values ('incoming-photos',
        '31000000-0000-4000-8000-000000000001/51000000-0000-4000-8000-000000000001/B/escape.jpg',
        '31000000-0000-4000-8000-000000000001')$$,
    '42501',
    null,
    'quarantine uploads outside the full pattern are rejected'
);
select throws_ok(
    $$insert into storage.objects (bucket_id, name, owner) values ('incoming-photos',
        '31000000-0000-4000-8000-000000000001/51000000-0000-4000-8000-000000000002/B/61000000-0000-4000-8000-00000000000c.jpg',
        '31000000-0000-4000-8000-000000000001')$$,
    '42501',
    null,
    'quarantine uploads into another contributor''s submission folder are rejected'
);
reset role;

set local role service_role;
select throws_ok(
    $$insert into public.photos (submission_id, shot_type, storage_path) values (
        '51000000-0000-4000-8000-000000000002', 'A',
        '31000000-0000-4000-8000-000000000001/51000000-0000-4000-8000-000000000002/A/61000000-0000-4000-8000-00000000000d.jpg')$$,
    '23514',
    'photo storage_path must be {auth_uid}/{submission_id}/{shot_type}/{uuid}.jpg',
    'the service role is bound too'
);
select throws_ok(
    $$update public.photos
      set storage_path = '31000000-0000-4000-8000-000000000002/51000000-0000-4000-8000-000000000002/A/61000000-0000-4000-8000-00000000000a.jpg'
      where submission_id = '51000000-0000-4000-8000-000000000001' and shot_type = 'A'$$,
    '23514',
    'photo storage_path must be {auth_uid}/{submission_id}/{shot_type}/{uuid}.jpg',
    'a stored path cannot be rewritten to point elsewhere'
);
reset role;

-- ---------------------------------------------------------------------------------------------
-- Finalize and settle (launch blocker 5)
-- ---------------------------------------------------------------------------------------------
select ok(
    not has_function_privilege('anon', 'public.finalize_submission(uuid)', 'execute'),
    'anon cannot finalize'
);
select ok(
    not has_function_privilege('authenticated', 'public.settle_submission(uuid)', 'execute')
    and not has_function_privilege('anon', 'public.settle_submission(uuid)', 'execute'),
    'clients cannot settle a status'
);

set local role authenticated;
set local "request.jwt.claims" = '{"sub":"31000000-0000-4000-8000-000000000001","role":"authenticated"}';
select throws_ok(
    $$select public.finalize_submission('51000000-0000-4000-8000-000000000001')$$,
    '23514',
    'shots A and B are required before a submission can be finalized',
    'finalize refuses a submission without shot B'
);
select lives_ok(
    $$insert into public.photos (submission_id, shot_type, storage_path) values (
        '51000000-0000-4000-8000-000000000001', 'B',
        '31000000-0000-4000-8000-000000000001/51000000-0000-4000-8000-000000000001/B/61000000-0000-4000-8000-00000000000b.jpg')$$,
    'owner adds shot B'
);
select isnt(
    public.finalize_submission('51000000-0000-4000-8000-000000000001'),
    null,
    'finalize succeeds once shots A and B exist'
);
select is(
    public.finalize_submission('51000000-0000-4000-8000-000000000001'),
    (select finalized_at from public.submissions where id = '51000000-0000-4000-8000-000000000001'),
    'finalize is idempotent'
);
reset role;

set local role authenticated;
set local "request.jwt.claims" = '{"sub":"31000000-0000-4000-8000-000000000002","role":"authenticated"}';
select throws_ok(
    $$select public.finalize_submission('51000000-0000-4000-8000-000000000001')$$,
    'P0002',
    'submission not found',
    'another contributor cannot finalize the submission'
);
reset role;

set local role service_role;
update public.submissions
set h3_r8 = '882bac94b5fffff', h3_r6 = '862bac94fffffff'
where id = '51000000-0000-4000-8000-000000000001';
select is(
    public.settle_submission('51000000-0000-4000-8000-000000000001'),
    'pending',
    'a finalized submission stays pending while shots are in QA'
);
update public.photos set qa_status = 'pass' where submission_id = '51000000-0000-4000-8000-000000000001';
select is(
    public.settle_submission('51000000-0000-4000-8000-000000000001'),
    'qa_pass',
    'shots A and B passing settle to qa_pass'
);
select is(
    (select status from public.submissions where id = '51000000-0000-4000-8000-000000000001'),
    'qa_pass',
    'settle writes the derived status'
);
insert into public.photos (submission_id, shot_type, storage_path, qa_status) values (
    '51000000-0000-4000-8000-000000000001', 'C',
    '31000000-0000-4000-8000-000000000001/51000000-0000-4000-8000-000000000001/C/61000000-0000-4000-8000-00000000000e.jpg',
    'fail');
select is(
    public.settle_submission('51000000-0000-4000-8000-000000000001'),
    'qa_pass',
    'a failed optional shot C never fails the submission'
);
update public.photos set qa_status = 'flagged'
where submission_id = '51000000-0000-4000-8000-000000000001' and shot_type = 'B';
select is(
    public.settle_submission('51000000-0000-4000-8000-000000000001'),
    'flagged',
    'a flagged required shot routes the submission to review'
);
update public.photos set qa_status = 'error'
where submission_id = '51000000-0000-4000-8000-000000000001' and shot_type = 'B';
select is(
    public.settle_submission('51000000-0000-4000-8000-000000000001'),
    'flagged',
    'a required shot whose QA errored routes the submission to review'
);
update public.photos set qa_status = 'fail'
where submission_id = '51000000-0000-4000-8000-000000000001' and shot_type = 'A';
select is(
    public.settle_submission('51000000-0000-4000-8000-000000000001'),
    'qa_fail',
    'a failed required shot fails the submission'
);
select is(
    public.settle_submission('51000000-0000-4000-8000-000000000002'),
    'pending',
    'an unfinalized submission is never settled'
);
reset role;

-- ---------------------------------------------------------------------------------------------
-- Capture gate (launch blocker 8)
-- ---------------------------------------------------------------------------------------------
update public.service_state set capture_open = false where singleton;
set local role authenticated;
set local "request.jwt.claims" = '{"sub":"31000000-0000-4000-8000-000000000002","role":"authenticated"}';
select throws_ok(
    $$insert into public.contribution_grants (id, contributor_id, terms_version, accepted_at, attribution_name)
      values ('41000000-0000-4000-8000-000000000009', '21000000-0000-4000-8000-000000000002', 'test-v1', now(), 'Anonymous soil contributor')$$,
    '42501',
    null,
    'closed capture refuses new grants'
);
select throws_ok(
    $$insert into public.submissions (id, contributor_id, grant_id, geom_precise, captured_at, status)
      values ('51000000-0000-4000-8000-000000000009', '21000000-0000-4000-8000-000000000002',
        '41000000-0000-4000-8000-000000000002',
        extensions.st_setsrid(extensions.st_makepoint(-72.58, 44.26), 4326), now(), 'pending')$$,
    '42501',
    null,
    'closed capture refuses new submissions'
);
select throws_ok(
    $$insert into public.photos (submission_id, shot_type, storage_path) values (
        '51000000-0000-4000-8000-000000000002', 'A',
        '31000000-0000-4000-8000-000000000002/51000000-0000-4000-8000-000000000002/A/61000000-0000-4000-8000-00000000000f.jpg')$$,
    '42501',
    null,
    'closed capture refuses new photo rows'
);
select throws_ok(
    $$insert into storage.objects (bucket_id, name, owner) values ('incoming-photos',
        '31000000-0000-4000-8000-000000000002/51000000-0000-4000-8000-000000000002/A/61000000-0000-4000-8000-00000000000f.jpg',
        '31000000-0000-4000-8000-000000000002')$$,
    '42501',
    null,
    'closed capture refuses quarantine uploads'
);
select throws_ok(
    $$update public.service_state set capture_open = true$$,
    '42501',
    null,
    'clients cannot open capture'
);
reset role;
set local role anon;
set local "request.jwt.claims" = '{"role":"anon"}';
select is(
    (select capture_open from public.service_state),
    false,
    'everyone can read whether capture is open'
);
reset role;

-- ---------------------------------------------------------------------------------------------
-- k-anonymous public cells (launch blocker 6)
-- ---------------------------------------------------------------------------------------------
set local role service_role;
select throws_ok(
    $$select public.refresh_public_h3_cells('[{"h3_index":"882bac94b5fffff","resolution":8,"n_submissions":4,"n_contributors":2,"latest_submission_date":"2026-10-01"}]'::jsonb)$$,
    '22023',
    'payload contains 1 cell(s) that are malformed or not k-anonymous',
    'cells with fewer than three contributors are refused'
);
select throws_ok(
    $$select public.refresh_public_h3_cells('[{"h3_index":"882bac94b5fffff","resolution":6,"n_submissions":4,"n_contributors":3,"latest_submission_date":"2026-10-01"}]'::jsonb)$$,
    '22023',
    'payload contains 1 cell(s) that are malformed or not k-anonymous',
    'a cell whose index does not match its resolution is refused'
);
select is(
    public.refresh_public_h3_cells('[
        {"h3_index":"882bac94b5fffff","resolution":8,"n_submissions":5,"n_contributors":3,"latest_submission_date":"2026-10-01"},
        {"h3_index":"862bac947ffffff","resolution":6,"n_submissions":3,"n_contributors":3,"latest_submission_date":"2026-09-30"},
        {"h3_index":"842bac9ffffffff","resolution":4,"n_submissions":7,"n_contributors":4,"latest_submission_date":"2026-09-29"}
    ]'::jsonb),
    3,
    'k-anonymous cells at resolutions 8, 6 and 4 publish'
);
reset role;
set local role anon;
set local "request.jwt.claims" = '{"role":"anon"}';
select is(
    (select array_agg(resolution order by resolution) from public.h3_cells),
    array[4, 6, 8]::smallint[],
    'anon reads multi-resolution aggregates only'
);
reset role;

-- ---------------------------------------------------------------------------------------------
-- Attribution safety and metadata allowlist
-- ---------------------------------------------------------------------------------------------
select throws_ok(
    $$insert into public.contribution_grants (contributor_id, terms_version, accepted_at, attribution_name)
      values ('21000000-0000-4000-8000-000000000001', 'test-v1', now(), '<img src=x onerror=alert(1)>')$$,
    '23514',
    null,
    'markup in an attribution name is rejected'
);
select throws_ok(
    $$insert into public.contribution_grants (contributor_id, terms_version, accepted_at, attribution_name)
      values ('21000000-0000-4000-8000-000000000001', 'test-v1', now(), 'visit https://spam.example now')$$,
    '23514',
    null,
    'URLs in an attribution name are rejected'
);
select throws_ok(
    $$insert into public.contribution_grants (contributor_id, terms_version, accepted_at, attribution_name)
      values ('21000000-0000-4000-8000-000000000001', 'test-v1', now(), 'jane@example.com')$$,
    '23514',
    null,
    'e-mail addresses in an attribution name are rejected'
);
select lives_ok(
    $$insert into public.contribution_grants (contributor_id, terms_version, accepted_at, attribution_name)
      values ('21000000-0000-4000-8000-000000000001', 'test-v1', now(), 'Ana María O''Neil-Ngũgĩ')$$,
    'international names with apostrophes and hyphens are accepted'
);
select lives_ok(
    $$update public.photos set camera_metadata_private = '{"make":"Pixel","color_space":"display_p3"}'
      where submission_id = '51000000-0000-4000-8000-000000000001' and shot_type = 'A'$$,
    'the colour-space class is an allowlisted private field'
);
select throws_ok(
    $$update public.photos set camera_metadata_private = '{"color_space":"Adobe RGB (1998) by Jane"}'
      where submission_id = '51000000-0000-4000-8000-000000000001' and shot_type = 'A'$$,
    '23514',
    null,
    'free-text colour-space values are rejected'
);

select * from finish();
rollback;
