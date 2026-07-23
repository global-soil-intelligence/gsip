begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;

select plan(36);

select is((select count(*) from public.submissions), 25::bigint, 'seed has 25 submissions');
select is((select count(*) from public.contribution_grants), 5::bigint, 'seed has immutable grants');
select is((select count(*) from public.prior_jobs), 25::bigint, 'seed submissions have durable prior jobs');
select is((select count(*) from public.qa_jobs), 25::bigint, 'seed photos have durable QA jobs');
select is((select count(*) from public.qa_events), 125::bigint, 'seed submissions have deterministic QA events');
select is((select count(*) from storage.buckets where public), 0::bigint, 'all photo buckets are private');
select hasnt_column('public', 'public_submissions', 'geom_precise', 'public view omits precise geometry');
select hasnt_column('public', 'public_submissions', 'contributor_id', 'public view omits contributor id');
select hasnt_column('public', 'public_submissions', 'device_model', 'public view omits device model');
select ok(
    not has_column_privilege('anon', 'public.submissions', 'geom_precise', 'select'),
    'anon lacks precise geometry privilege'
);
select ok(
    not has_column_privilege('anon', 'public.photos', 'camera_metadata_private', 'select'),
    'anon lacks private camera metadata privilege'
);
select ok(
    not has_table_privilege('anon', 'public.public_submissions', 'insert'),
    'public view is read only for anon'
);
select ok(
    not has_table_privilege('anon', 'public.prior_jobs', 'select'),
    'prior job errors are server-only'
);
select ok(
    not has_table_privilege('anon', 'public.qa_jobs', 'select'),
    'photo QA job errors are server-only'
);
select ok(
    not has_function_privilege('anon', 'public.enqueue_prior_job()', 'execute'),
    'anon cannot invoke the security-definer queue trigger directly'
);
select ok(
    not has_function_privilege('authenticated', 'public.enqueue_prior_job()', 'execute'),
    'authenticated users cannot invoke the queue trigger directly'
);
select ok(
    not has_function_privilege('anon', 'public.enqueue_qa_job()', 'execute'),
    'anon cannot invoke the security-definer photo queue trigger directly'
);

insert into public.contributors (id, auth_uid, handle)
values
    ('20000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000001', 'rls-owner-a'),
    ('20000000-0000-4000-8000-000000000002', '30000000-0000-4000-8000-000000000002', 'rls-owner-b');

insert into public.contribution_grants (
    id, contributor_id, terms_version, accepted_at, attribution_name
)
values
    ('40000000-0000-4000-8000-000000000001', '20000000-0000-4000-8000-000000000001', 'test-v1', now(), 'owner-a'),
    ('40000000-0000-4000-8000-000000000002', '20000000-0000-4000-8000-000000000002', 'test-v1', now(), 'owner-b');

insert into public.submissions (
    id, contributor_id, grant_id, geom_precise, h3_r8, h3_r6, captured_at, status
)
values
    ('50000000-0000-4000-8000-000000000001', '20000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000001', extensions.st_setsrid(extensions.st_makepoint(-93.625, 41.9483), 4326), '88262b2a37fffff', '86262b287ffffff', now(), 'pending'),
    ('50000000-0000-4000-8000-000000000002', '20000000-0000-4000-8000-000000000002', '40000000-0000-4000-8000-000000000002', extensions.st_setsrid(extensions.st_makepoint(36.08, -0.3031), 4326), '887a6a09ebfffff', '867a6a09fffffff', now(), 'pending');

select is((select count(*) from public.prior_jobs), 27::bigint, 'submission inserts enqueue one prior job each');

insert into public.photos (submission_id, shot_type, storage_path, camera_metadata_private)
values
    ('50000000-0000-4000-8000-000000000001', 'B', 'owner-a/photo.jpg', '{"make":"Test"}'),
    ('50000000-0000-4000-8000-000000000002', 'B', 'owner-b/photo.jpg', '{"iso":100}');

insert into storage.objects (bucket_id, name, owner)
values
    ('incoming-photos', '30000000-0000-4000-8000-000000000001/submission/B/a.jpg', '30000000-0000-4000-8000-000000000001'),
    ('submission-photos', '30000000-0000-4000-8000-000000000001/submission/B/a.jpg', '30000000-0000-4000-8000-000000000001'),
    ('incoming-photos', '30000000-0000-4000-8000-000000000002/submission/B/b.jpg', '30000000-0000-4000-8000-000000000002');

set local role authenticated;
set local "request.jwt.claims" = '{"sub":"30000000-0000-4000-8000-000000000001","role":"authenticated"}';
select is((select count(*) from public.submissions), 1::bigint, 'owner sees only own precise submission');
select is((select count(*) from public.photos), 1::bigint, 'owner sees only own photo metadata');
select is((select count(*) from storage.objects), 2::bigint, 'owner sees only own objects in both buckets');
select is(
    (select count(*) from public.submissions where contributor_id = '20000000-0000-4000-8000-000000000002'),
    0::bigint,
    'contributor A cannot read contributor B precise rows'
);

select lives_ok(
    $$insert into public.submissions (
        id, contributor_id, grant_id, geom_precise, h3_r8, h3_r6, captured_at,
        land_cover, surface_condition, disturbed, device_model, gps_accuracy_m, status
      ) values (
        '50000000-0000-4000-8000-000000000003',
        '20000000-0000-4000-8000-000000000001',
        '40000000-0000-4000-8000-000000000001',
        extensions.st_setsrid(extensions.st_makepoint(-79.982, 40.446), 4326),
        '88fffffffffffff', '86fffffffffffff', now(),
        'urban', 'moist', false, 'pgTap authenticated client', 8, 'pending'
      )$$,
    'authenticated client can insert the exact hosted submission payload'
);
select is(
    (select h3_r8 from public.submissions where id = '50000000-0000-4000-8000-000000000003'),
    null,
    'a deliberately wrong client H3 cell cannot persist'
);
select is(
    (select h3_r6 from public.submissions where id = '50000000-0000-4000-8000-000000000003'),
    null,
    'a structurally invalid client H3 cell cannot persist'
);
select throws_ok(
    $$insert into public.submissions (
        id, contributor_id, grant_id, geom_precise, h3_r8, h3_r6, captured_at, status
      ) values (
        '50000000-0000-4000-8000-000000000004',
        '20000000-0000-4000-8000-000000000001',
        '40000000-0000-4000-8000-000000000001',
        extensions.st_setsrid(extensions.st_makepoint(-79.982, 40.446), 4326),
        '882a84666bfffff', '862a84667ffffff', now(), 'qa_pass'
      )$$,
    '42501',
    null,
    'authenticated client cannot self-approve a submission'
);
select lives_ok(
    $$insert into public.photos (submission_id, shot_type, storage_path)
      values (
        '50000000-0000-4000-8000-000000000003', 'A',
        '30000000-0000-4000-8000-000000000001/submission/A/client.jpg'
      )$$,
    'authenticated client can insert only the public photo linkage fields'
);
select throws_ok(
    $$insert into public.photos (
        submission_id, shot_type, storage_path, camera_metadata_private
      ) values (
        '50000000-0000-4000-8000-000000000003', 'C',
        '30000000-0000-4000-8000-000000000001/submission/C/client.jpg',
        '{"make":"forged"}'
      )$$,
    '42501',
    null,
    'authenticated client cannot self-grade private photo QA fields'
);
reset role;

set local role anon;
set local "request.jwt.claims" = '{"role":"anon"}';
select is((select count(*) from public.public_submissions), 25::bigint, 'anon sees only QA-passed H3 rows');
select throws_ok(
    'select geom_precise from public.submissions',
    '42501',
    'permission denied for table submissions',
    'anon cannot query precise geometry'
);
select throws_ok(
    'select camera_metadata_private from public.photos',
    '42501',
    'permission denied for table photos',
    'anon cannot query private camera metadata'
);
select is((select count(*) from storage.objects), 0::bigint, 'anon cannot read either photo bucket');
reset role;

select throws_ok(
    $$update public.contribution_grants set attribution_name = 'changed'
      where id = '40000000-0000-4000-8000-000000000001'$$,
    'P0001',
    'contribution_grants are immutable',
    'accepted grants cannot be changed'
);
select throws_ok(
    $$insert into public.photos (submission_id, shot_type, storage_path, camera_metadata_private)
      values ('50000000-0000-4000-8000-000000000001', 'C', 'bad.jpg', '{"GPSLatitude":41.9}')$$,
    '23514',
    null,
    'location metadata is rejected'
);
select throws_ok(
    $$insert into public.priors (
        submission_id, source, property, value, unit, depth_top_cm, depth_bottom_cm
      ) values (
        '50000000-0000-4000-8000-000000000001', 'soilgrids', 'soc', 10, 'pH', 0, 5
      )$$,
    '23514',
    null,
    'noncanonical units are rejected'
);
select throws_ok(
    $$insert into public.priors (
        submission_id, source, property, value, unit, depth_top_cm, depth_bottom_cm
      ) values (
        '50000000-0000-4000-8000-000000000001', 'soilgrids', 'soc', 10, 'g/kg', 30, 5
      )$$,
    '23514',
    null,
    'invalid depth ranges are rejected'
);

select * from finish();
rollback;
