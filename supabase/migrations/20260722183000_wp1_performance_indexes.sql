create index contribution_grants_contributor_idx
    on public.contribution_grants (contributor_id);

drop index public.submissions_grant_idx;
create index submissions_grant_owner_idx
    on public.submissions (grant_id, contributor_id);
