-- WP-6b (launch blocker 8): a database-enforced capture gate.
-- The capture app's build flag is cosmetic on its own: a deployed client configured for production
-- could write before legal review. Every contribution insert now requires service_state.capture_open,
-- which defaults to closed and only the service role can change.

create table public.service_state (
    singleton boolean primary key default true check (singleton),
    capture_open boolean not null default false,
    updated_at timestamptz not null default now()
);

comment on table public.service_state is
    'WP-6b: single-row operational switches. capture_open gates every contribution insert; the product owner opens it after the SPEC section 11 launch gates.';

insert into public.service_state (singleton) values (true)
on conflict (singleton) do nothing;

alter table public.service_state enable row level security;
revoke all on public.service_state from public, anon, authenticated;
grant select (capture_open, updated_at) on public.service_state to anon, authenticated;
grant select, insert, update on public.service_state to service_role;
create policy service_state_read_all on public.service_state
    for select to anon, authenticated using (true);

create or replace function public.capture_is_open()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select coalesce((select s.capture_open from public.service_state s where s.singleton), false);
$$;

revoke all on function public.capture_is_open() from public;
grant execute on function public.capture_is_open() to anon, authenticated, service_role;

drop policy if exists contribution_grants_insert_own on public.contribution_grants;
create policy contribution_grants_insert_own on public.contribution_grants
    for insert to authenticated
    with check (
        contributor_id = public.current_contributor_id()
        and accepted_at <= now()
        and public.capture_is_open()
    );

drop policy if exists submissions_insert_own on public.submissions;
create policy submissions_insert_own on public.submissions
    for insert to authenticated
    with check (
        contributor_id = public.current_contributor_id()
        and status = 'pending'
        and public.capture_is_open()
    );

drop policy if exists photos_insert_own on public.photos;
create policy photos_insert_own on public.photos
    for insert to authenticated
    with check (
        submission_id in (
            select id from public.submissions where contributor_id = public.current_contributor_id()
        )
        and public.capture_is_open()
    );
