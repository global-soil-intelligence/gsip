alter table public.submissions add column is_synthetic boolean not null default false;

update public.submissions
set is_synthetic = true
where contributor_id in (
    'c6f3acc2-1ace-589c-9a02-4c015178914d',
    '1a4068aa-af34-5ce0-b4e9-e8e8fd2db974',
    '071846b8-b76f-5fa6-be6c-e557fe9766df',
    '0ade88d1-f13d-56e2-80ed-65a0743d677e',
    'c57529e0-2790-5e7b-9c83-f09d0e9c4f2a'
);

comment on column public.submissions.is_synthetic is
    'Server-controlled guardrail: synthetic development rows never enter public dataset exports.';

revoke update (is_synthetic) on public.submissions from authenticated;
