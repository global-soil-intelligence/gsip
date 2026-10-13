-- WP-AGENT-1: dataset_releases, the public record of every successful dataset push (SPEC section
-- 6). The export writes one row per push with the service role; anyone can read them, so people
-- and agents can cite exactly what they used. Rows are append-only: a release that was published
-- stays on record, and a re-run of the same date that pushes a new commit adds a newer row. Each
-- commit is recorded once, so the export can safely retry recording it. A push whose commit the
-- Hub did not report is recorded once per date (nulls are not distinct in the key).

create table public.dataset_releases (
    id uuid primary key default gen_random_uuid(),
    version text not null check (version ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'),
    released_at timestamptz not null default now(),
    rows integer not null check (rows >= 0),
    photos integer not null check (photos >= 0),
    hf_revision text check (hf_revision ~ '^[0-9a-f]{40}$'),
    constraint dataset_releases_push_key unique nulls not distinct (version, hf_revision)
);

create index dataset_releases_released_at_idx on public.dataset_releases (released_at desc);

comment on table public.dataset_releases is
    'WP-AGENT-1: one row per successful public dataset push (version = export date; hf_revision = the Hugging Face commit). Public read; service-role insert; append-only.';

alter table public.dataset_releases enable row level security;
revoke all on public.dataset_releases from public, anon, authenticated, service_role;
grant select on public.dataset_releases to anon, authenticated;
grant select, insert on public.dataset_releases to service_role;
create policy dataset_releases_read_all on public.dataset_releases
    for select to anon, authenticated using (true);

-- The anonymous role, which every agent interface uses (I12), executes no GSIP function except
-- capture_is_open(). These trigger functions could never be called directly, but nothing should
-- grant them to it either.
revoke all on function private.reject_contribution_grant_mutation() from public, anon, authenticated;
revoke all on function private.reject_grant_withdrawal_mutation() from public, anon, authenticated;
revoke all on function private.reject_truncate() from public, anon, authenticated;
