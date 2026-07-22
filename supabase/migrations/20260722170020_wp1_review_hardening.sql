alter table public.submissions drop constraint submissions_h3_r8_check;
alter table public.submissions add constraint submissions_h3_r8_check
    check (h3_r8 ~ '^88[0-9a-f]{13}$');
alter table public.submissions drop constraint submissions_h3_r6_check;
alter table public.submissions add constraint submissions_h3_r6_check
    check (h3_r6 ~ '^86[0-9a-f]{13}$');

drop policy submissions_insert_own on public.submissions;
create policy submissions_insert_own on public.submissions
    for insert to authenticated with check (
        contributor_id = public.current_contributor_id() and status = 'pending'
    );

revoke all on public.h3_cells from anon;
grant select on public.h3_cells to anon, authenticated;
