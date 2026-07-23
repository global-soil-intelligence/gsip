alter table public.h3_cells
    add column latest_submission_date date;

-- The v2 seed cells were synthetic UI fixtures. Public coverage is rebuilt from
-- non-synthetic, QA-passed submissions after a successful dataset publication.
delete from public.h3_cells;

revoke select (
    id,
    h3_r8,
    h3_r6,
    captured_at,
    land_cover,
    surface_condition,
    disturbed,
    precip_flag,
    elevation,
    status
) on public.submissions from anon;
revoke select on public.public_submissions from anon, authenticated;

grant select on public.h3_cells to anon, authenticated;

comment on column public.h3_cells.latest_submission_date is
    'Date-only freshness marker for the public aggregate; never a capture timestamp.';
