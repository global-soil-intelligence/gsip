-- Data as production may hold it just before WP-6e. Loaded after every earlier migration and
-- immediately before 20261010150000_wp6e_provenance.sql (scripts/db-migration-test.sh); the
-- assertions are in wp6e_provenance.test.sql.

-- L1: a signed-in contributor with a finalized, QA-passed field observation and a lab result.
insert into auth.users (id) values ('e1000000-0000-4000-8000-000000000001');
insert into public.contributors (id, auth_uid, handle)
values ('d1000000-0000-4000-8000-000000000001', 'e1000000-0000-4000-8000-000000000001', 'legacy-one');
insert into public.contribution_grants (id, contributor_id, terms_version, accepted_at, attribution_name)
values (
    'f1000000-0000-4000-8000-000000000001', 'd1000000-0000-4000-8000-000000000001',
    '2026-07-22-v1', '2026-09-01T10:00:00Z', 'Legacy One'
);
insert into public.submissions (
    id, contributor_id, grant_id, geom_precise, h3_r8, h3_r6, captured_at, status, finalized_at
) values (
    'b1000000-0000-4000-8000-000000000001', 'd1000000-0000-4000-8000-000000000001',
    'f1000000-0000-4000-8000-000000000001',
    extensions.st_setsrid(extensions.st_makepoint(-73.2121, 44.4759), 4326),
    '882b8cb563fffff', '862b8cb57ffffff', '2026-09-01T09:50:00Z', 'qa_pass', '2026-09-01T10:00:00Z'
);
insert into public.photos (submission_id, shot_type, storage_path, qa_status)
values
    ('b1000000-0000-4000-8000-000000000001', 'A',
     'e1000000-0000-4000-8000-000000000001/b1000000-0000-4000-8000-000000000001/A/a1000000-0000-4000-8000-00000000000a.jpg',
     'pass'),
    ('b1000000-0000-4000-8000-000000000001', 'B',
     'e1000000-0000-4000-8000-000000000001/b1000000-0000-4000-8000-000000000001/B/a1000000-0000-4000-8000-00000000000b.jpg',
     'pass');
insert into public.gold_labels (submission_id, lab_name, property, value, unit, depth_top_cm, depth_bottom_cm)
values ('b1000000-0000-4000-8000-000000000001', 'Example Lab', 'soc', 21.5, 'g/kg', 0, 5);

-- L2: an account already deleted under WP-6d: unlinked from sign-in, nothing left behind.
insert into public.contributors (id, auth_uid, handle)
values ('d2000000-0000-4000-8000-000000000002', null, 'deleted-d20000000000400080000000');

-- L3: a grant whose pre-WP-6e client wrote its own terms version text.
insert into auth.users (id) values ('e1000000-0000-4000-8000-000000000003');
insert into public.contributors (id, auth_uid, handle)
values ('d1000000-0000-4000-8000-000000000003', 'e1000000-0000-4000-8000-000000000003', 'legacy-three');
insert into public.contribution_grants (id, contributor_id, terms_version, accepted_at, attribution_name)
values (
    'f1000000-0000-4000-8000-000000000003', 'd1000000-0000-4000-8000-000000000003',
    'whatever-i-like', '2026-08-15T10:00:00Z', 'Legacy Three'
);

-- S: a synthetic development observation, as supabase/seed.sql wrote it before WP-6e.
insert into public.contributors (id, auth_uid, handle)
values ('d1000000-0000-4000-8000-000000000005', 'a0000000-0000-4000-8000-000000000009', 'synthetic-farmer');
insert into public.contribution_grants (id, contributor_id, terms_version, accepted_at, attribution_name)
values (
    'f1000000-0000-4000-8000-000000000005', 'd1000000-0000-4000-8000-000000000005',
    '2026-07-22', '2026-07-22T00:00:00Z', 'synthetic-farmer'
);
insert into public.submissions (
    id, contributor_id, grant_id, geom_precise, h3_r8, h3_r6, captured_at, status, is_synthetic,
    finalized_at
) values (
    'b1000000-0000-4000-8000-000000000005', 'd1000000-0000-4000-8000-000000000005',
    'f1000000-0000-4000-8000-000000000005',
    extensions.st_setsrid(extensions.st_makepoint(-93.6250, 41.9483), 4326),
    '88262b2a37fffff', '86262b287ffffff', '2026-06-01T14:10:00Z', 'qa_pass', true,
    '2026-06-01T14:15:00Z'
);
insert into public.photos (submission_id, shot_type, storage_path, qa_status)
values
    ('b1000000-0000-4000-8000-000000000005', 'A',
     'a0000000-0000-4000-8000-000000000009/b1000000-0000-4000-8000-000000000005/A/a1000000-0000-4000-8000-00000000005a.jpg',
     'pass'),
    ('b1000000-0000-4000-8000-000000000005', 'B',
     'a0000000-0000-4000-8000-000000000009/b1000000-0000-4000-8000-000000000005/B/a1000000-0000-4000-8000-00000000005b.jpg',
     'pass');
