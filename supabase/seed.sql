-- Deterministic, idempotent development seed: 25 synthetic submissions across
-- North America, South America, Africa, Europe, and Australia.

insert into public.contributors (id, handle)
values
    ('c6f3acc2-1ace-589c-9a02-4c015178914d', 'iowa-farmer'),
    ('1a4068aa-af34-5ce0-b4e9-e8e8fd2db974', 'kenya-agronomist'),
    ('071846b8-b76f-5fa6-be6c-e557fe9766df', 'brandenburg-gardener'),
    ('0ade88d1-f13d-56e2-80ed-65a0743d677e', 'cerrado-ranger'),
    ('c57529e0-2790-5e7b-9c83-f09d0e9c4f2a', 'murray-viticulturist')
on conflict (id) do nothing;

insert into public.contribution_grants (
    id, contributor_id, terms_version, accepted_at, attribution_name
)
values
    ('10000000-0000-4000-8000-000000000001', 'c6f3acc2-1ace-589c-9a02-4c015178914d', '2026-07-22', '2026-07-22T00:00:00Z', 'iowa-farmer'),
    ('10000000-0000-4000-8000-000000000002', '1a4068aa-af34-5ce0-b4e9-e8e8fd2db974', '2026-07-22', '2026-07-22T00:00:00Z', 'kenya-agronomist'),
    ('10000000-0000-4000-8000-000000000003', '071846b8-b76f-5fa6-be6c-e557fe9766df', '2026-07-22', '2026-07-22T00:00:00Z', 'brandenburg-gardener'),
    ('10000000-0000-4000-8000-000000000004', '0ade88d1-f13d-56e2-80ed-65a0743d677e', '2026-07-22', '2026-07-22T00:00:00Z', 'cerrado-ranger'),
    ('10000000-0000-4000-8000-000000000005', 'c57529e0-2790-5e7b-9c83-f09d0e9c4f2a', '2026-07-22', '2026-07-22T00:00:00Z', 'murray-viticulturist')
on conflict (id) do nothing;

with seed(id, contributor_id, grant_id, lat, lon, h3_r8, h3_r6, captured_at, land_cover, surface_condition) as (
    values
    ('73f0400e-5c64-5a6e-90d1-6a7686935317'::uuid, 'c6f3acc2-1ace-589c-9a02-4c015178914d'::uuid, '10000000-0000-4000-8000-000000000001'::uuid, 41.9483, -93.6250, '88262b2a37fffff', '86262b287ffffff', '2026-06-01T14:10:00Z'::timestamptz, 'cropland', 'moist'),
    ('d3445494-bdf6-5834-903e-ed01c056f883', 'c6f3acc2-1ace-589c-9a02-4c015178914d', '10000000-0000-4000-8000-000000000001', 42.0261, -93.6437, '88262b398bfffff', '86262b39fffffff', '2026-06-02T15:30:00Z', 'cropland', 'dry'),
    ('e6defa07-930a-57d2-95e3-09be6332bd2a', 'c6f3acc2-1ace-589c-9a02-4c015178914d', '10000000-0000-4000-8000-000000000001', 41.8780, -93.0977, '882676c833fffff', '862676c87ffffff', '2026-06-03T09:12:00Z', 'grassland', 'moist'),
    ('649541e9-80b2-57d7-889a-95e8835f1215', 'c6f3acc2-1ace-589c-9a02-4c015178914d', '10000000-0000-4000-8000-000000000001', 41.5868, -93.6250, '88260d8763fffff', '86260d877ffffff', '2026-06-04T17:45:00Z', 'urban', 'dry'),
    ('51e50bf8-3684-5869-9da1-fa0b9d88e481', 'c6f3acc2-1ace-589c-9a02-4c015178914d', '10000000-0000-4000-8000-000000000001', 42.4977, -92.3436, '8826290e2bfffff', '8626290e7ffffff', '2026-06-05T08:20:00Z', 'cropland', 'wet'),
    ('04073bdf-ac5c-5eba-9265-35c543d37de0', '1a4068aa-af34-5ce0-b4e9-e8e8fd2db974', '10000000-0000-4000-8000-000000000002', -0.3031, 36.0800, '887a6a09ebfffff', '867a6a09fffffff', '2026-06-06T10:00:00Z', 'cropland', 'moist'),
    ('510ddbd0-d1fb-5664-9816-2a7e7ee804bc', '1a4068aa-af34-5ce0-b4e9-e8e8fd2db974', '10000000-0000-4000-8000-000000000002', -0.4569, 36.5931, '887a452669fffff', '867a45267ffffff', '2026-06-07T11:15:00Z', 'grassland', 'dry'),
    ('b7efb432-316f-5199-9195-5170c5f43835', '1a4068aa-af34-5ce0-b4e9-e8e8fd2db974', '10000000-0000-4000-8000-000000000002', -0.7893, 36.4344, '887a6ad013fffff', '867a6ad0fffffff', '2026-06-08T12:40:00Z', 'shrubland', 'dry'),
    ('2aee6989-4e96-5aaa-b825-513de052555a', '1a4068aa-af34-5ce0-b4e9-e8e8fd2db974', '10000000-0000-4000-8000-000000000002', -1.0921, 37.0144, '887a6e4b27fffff', '867a6e4b7ffffff', '2026-06-09T13:05:00Z', 'cropland', 'moist'),
    ('f54141a6-a957-5a63-bfb0-8e0c0dec8251', '1a4068aa-af34-5ce0-b4e9-e8e8fd2db974', '10000000-0000-4000-8000-000000000002', -0.1022, 35.9608, '887a6a631dfffff', '867a6a637ffffff', '2026-06-10T14:55:00Z', 'forest', 'moist'),
    ('dfc91d6f-8ebf-55c5-b2ad-bd67cb170329', '071846b8-b76f-5fa6-be6c-e557fe9766df', '10000000-0000-4000-8000-000000000003', 52.4009, 13.0591, '881f188721fffff', '861f18877ffffff', '2026-06-11T09:30:00Z', 'cropland', 'moist'),
    ('ab316a42-fd20-5935-8651-ed3cc47374bc', '071846b8-b76f-5fa6-be6c-e557fe9766df', '10000000-0000-4000-8000-000000000003', 52.5323, 13.9026, '881f1d78b3fffff', '861f1d78fffffff', '2026-06-12T10:45:00Z', 'forest', 'moist'),
    ('c73fc8fa-9c2a-5fba-a835-8d8bb51f6c5c', '071846b8-b76f-5fa6-be6c-e557fe9766df', '10000000-0000-4000-8000-000000000003', 52.1205, 12.8919, '881f181157fffff', '861f18117ffffff', '2026-06-13T11:20:00Z', 'grassland', 'wet'),
    ('d24c7824-52f6-5333-86a8-1a3f6f0fb3b7', '071846b8-b76f-5fa6-be6c-e557fe9766df', '10000000-0000-4000-8000-000000000003', 51.8663, 13.7101, '881f182f4dfffff', '861f182f7ffffff', '2026-06-14T15:10:00Z', 'cropland', 'dry'),
    ('84fcb62a-8adb-5881-9351-24850fdec2d2', '071846b8-b76f-5fa6-be6c-e557fe9766df', '10000000-0000-4000-8000-000000000003', 52.6928, 13.2843, '881f1d4341fffff', '861f1d437ffffff', '2026-06-15T16:25:00Z', 'wetland', 'wet'),
    ('ad2fd2b3-848c-560f-ac4b-df61afa65250', '0ade88d1-f13d-56e2-80ed-65a0743d677e', '10000000-0000-4000-8000-000000000004', -15.5989, -47.7128, '88a8d1b82dfffff', '86a8d1b87ffffff', '2026-06-16T13:00:00Z', 'grassland', 'dry'),
    ('f607bc13-a22f-5423-9abe-0233daa85293', '0ade88d1-f13d-56e2-80ed-65a0743d677e', '10000000-0000-4000-8000-000000000004', -16.0333, -47.9500, '88a8c25a13fffff', '86a8c25afffffff', '2026-06-17T14:30:00Z', 'shrubland', 'dry'),
    ('55bfdfc6-5704-55a8-a402-f8fb39cb516c', '0ade88d1-f13d-56e2-80ed-65a0743d677e', '10000000-0000-4000-8000-000000000004', -15.2201, -48.9931, '88a8c34a91fffff', '86a8c34afffffff', '2026-06-18T09:50:00Z', 'cropland', 'moist'),
    ('3d96c7a9-1dc1-5a05-969c-c3acc0e5bb35', '0ade88d1-f13d-56e2-80ed-65a0743d677e', '10000000-0000-4000-8000-000000000004', -14.8619, -47.4218, '88a8de9a29fffff', '86a8de9a7ffffff', '2026-06-19T10:35:00Z', 'bare', 'dry'),
    ('a706d092-0708-54b2-86df-5d3e8ddad6ca', '0ade88d1-f13d-56e2-80ed-65a0743d677e', '10000000-0000-4000-8000-000000000004', -15.9403, -48.2622, '88a8c254d3fffff', '86a8c254fffffff', '2026-06-20T11:40:00Z', 'cropland', 'moist'),
    ('c5e64d17-7b3b-5860-92d3-9d937f9ceb52', 'c57529e0-2790-5e7b-9c83-f09d0e9c4f2a', '10000000-0000-4000-8000-000000000005', -34.1855, 142.1625, '88be5d32e3fffff', '86be5d32fffffff', '2026-06-21T08:05:00Z', 'cropland', 'dry'),
    ('42db6d0f-cb91-56e4-b7a6-ea913382437e', 'c57529e0-2790-5e7b-9c83-f09d0e9c4f2a', '10000000-0000-4000-8000-000000000005', -35.1082, 147.3598, '88be734c05fffff', '86be734c7ffffff', '2026-06-22T09:15:00Z', 'cropland', 'dry'),
    ('b7f4503b-2e9e-586e-9dd3-db6ccd8ff68e', 'c57529e0-2790-5e7b-9c83-f09d0e9c4f2a', '10000000-0000-4000-8000-000000000005', -34.2866, 146.0509, '88be55605dfffff', '86be55607ffffff', '2026-06-23T10:25:00Z', 'grassland', 'dry'),
    ('9deaa28d-b517-5cae-940a-9595b979d411', 'c57529e0-2790-5e7b-9c83-f09d0e9c4f2a', '10000000-0000-4000-8000-000000000005', -33.2833, 149.1013, '88be0b3211fffff', '86be0b327ffffff', '2026-06-24T11:35:00Z', 'grassland', 'moist'),
    ('c41d7126-5381-5473-842b-de0ef04c10ed', 'c57529e0-2790-5e7b-9c83-f09d0e9c4f2a', '10000000-0000-4000-8000-000000000005', -34.7208, 143.5608, '88be434411fffff', '86be43447ffffff', '2026-06-25T12:45:00Z', 'shrubland', 'dry')
)
insert into public.submissions (
    id, contributor_id, grant_id, geom_precise, h3_r8, h3_r6, captured_at,
    land_cover, surface_condition, disturbed, status
)
select id, contributor_id, grant_id,
    extensions.st_setsrid(extensions.st_makepoint(lon, lat), 4326),
    h3_r8, h3_r6, captured_at, land_cover, surface_condition, false, 'qa_pass'
from seed
on conflict (id) do nothing;

insert into public.photos (submission_id, shot_type, storage_path, card_detected, sharpness_score)
select id, 'B', 'seed/' || id::text || '-shot-b.jpg', true, 0.85
from public.submissions
where contributor_id in (
    'c6f3acc2-1ace-589c-9a02-4c015178914d',
    '1a4068aa-af34-5ce0-b4e9-e8e8fd2db974',
    '071846b8-b76f-5fa6-be6c-e557fe9766df',
    '0ade88d1-f13d-56e2-80ed-65a0743d677e',
    'c57529e0-2790-5e7b-9c83-f09d0e9c4f2a'
)
on conflict (submission_id, shot_type) do nothing;

insert into public.h3_cells (h3_index, n_submissions, updated_at)
select h3_r8, count(*)::integer, now()
from public.submissions
group by h3_r8
on conflict (h3_index) do update
set n_submissions = excluded.n_submissions, updated_at = excluded.updated_at;
