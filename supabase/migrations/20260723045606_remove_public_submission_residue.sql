drop view if exists public.public_submissions;
drop policy if exists submissions_select_public_qa_pass on public.submissions;

comment on table public.h3_cells is
    'The sole anonymous contribution-data surface; aggregates contain no per-submission rows.';
