alter table public.contributors enable row level security;
alter table public.submissions enable row level security;
alter table public.photos enable row level security;
alter table public.priors enable row level security;
alter table public.gold_labels enable row level security;
alter table public.predictions enable row level security;
alter table public.qa_events enable row level security;
alter table public.h3_cells enable row level security;

revoke all on public.contributors, public.submissions, public.photos,
    public.priors, public.gold_labels, public.predictions, public.qa_events from anon;

create or replace function public.current_contributor_id()
returns uuid language sql stable security definer set search_path = public as $$
    select id from public.contributors where auth_uid = (select auth.uid());
$$;
revoke execute on function public.current_contributor_id from public, anon;

create policy contributors_select_own on public.contributors
    for select to authenticated using (auth_uid = (select auth.uid()));
create policy contributors_insert_self on public.contributors
    for insert to authenticated with check (auth_uid = (select auth.uid()));
create policy contributors_update_own on public.contributors
    for update to authenticated using (auth_uid = (select auth.uid()))
    with check (auth_uid = (select auth.uid()));

revoke update on public.contributors from authenticated;
grant update (handle, precise_location_optin, terms_version, terms_accepted_at)
    on public.contributors to authenticated;

create policy submissions_select_own on public.submissions
    for select to authenticated using (contributor_id = public.current_contributor_id());
create policy submissions_insert_own on public.submissions
    for insert to authenticated with check (contributor_id = public.current_contributor_id());

create policy photos_select_own on public.photos for select to authenticated using (
    submission_id in (select id from public.submissions where contributor_id = public.current_contributor_id())
);
create policy photos_insert_own on public.photos for insert to authenticated with check (
    submission_id in (select id from public.submissions where contributor_id = public.current_contributor_id())
);
create policy priors_select_own on public.priors for select to authenticated using (
    submission_id in (select id from public.submissions where contributor_id = public.current_contributor_id())
);
create policy gold_labels_select_own on public.gold_labels for select to authenticated using (
    submission_id in (select id from public.submissions where contributor_id = public.current_contributor_id())
);
create policy predictions_select_own on public.predictions for select to authenticated using (
    submission_id in (select id from public.submissions where contributor_id = public.current_contributor_id())
);
create policy qa_events_select_own on public.qa_events for select to authenticated using (
    submission_id in (select id from public.submissions where contributor_id = public.current_contributor_id())
);
create policy h3_cells_select_all on public.h3_cells
    for select to anon, authenticated using (true);

grant select (id, h3_r8, h3_r6, captured_at, land_cover, surface_condition,
    disturbed, precip_flag, elevation, status) on public.submissions to anon;
create policy submissions_select_public_qa_pass on public.submissions
    for select to anon using (status = 'qa_pass');

create view public.public_submissions with (security_invoker = true, security_barrier = true) as
select id, h3_r8, h3_r6, captured_at, land_cover, surface_condition,
    disturbed, precip_flag, elevation, status
from public.submissions where status = 'qa_pass';
grant select on public.public_submissions to anon, authenticated;
