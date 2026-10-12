-- WP-6b (launch blocker 6): public cells must be k-anonymous (SPEC I7, k = 3).
-- An observation is published at the finest of resolutions 8, 6 and 4 whose published cell
-- aggregates at least 3 distinct contributors; the export computes the assignment and this
-- table refuses anything else.

alter table public.h3_cells add column resolution smallint;
alter table public.h3_cells add column n_contributors integer;

-- Pre-v3 rows carry no contributor counts and cannot prove k-anonymity. The nightly export
-- rebuilds the table after its next successful publication.
delete from public.h3_cells where n_contributors is null;

alter table public.h3_cells alter column resolution set not null;
alter table public.h3_cells alter column n_contributors set not null;
alter table public.h3_cells add constraint h3_cells_resolution_check
    check (resolution in (4, 6, 8));
alter table public.h3_cells add constraint h3_cells_index_matches_resolution
    check (h3_index ~ ('^8' || to_hex(resolution::integer) || '[0-9a-f]{13}$'));
alter table public.h3_cells add constraint h3_cells_k_anonymous
    check (n_contributors >= 3);
alter table public.h3_cells add constraint h3_cells_counts_consistent
    check (n_submissions >= n_contributors);

comment on column public.h3_cells.resolution is
    'H3 resolution of the published cell: 8, 6 or 4 (SPEC I7 k-anonymous generalization).';
comment on column public.h3_cells.n_contributors is
    'Distinct contributors aggregated in this published cell; never below 3.';

create or replace function public.refresh_public_h3_cells(payload jsonb)
returns integer
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
    refreshed integer;
    violations integer;
begin
    if jsonb_typeof(payload) is distinct from 'array' then
        raise exception 'payload must be a JSON array' using errcode = '22023';
    end if;

    select count(*) into violations
    from jsonb_to_recordset(payload) as item (
        h3_index text,
        resolution integer,
        n_submissions integer,
        n_contributors integer,
        latest_submission_date date
    )
    where item.resolution is null
       or item.resolution not in (4, 6, 8)
       or item.h3_index is null
       or item.h3_index !~ ('^8' || to_hex(item.resolution) || '[0-9a-f]{13}$')
       or item.n_contributors is null
       or item.n_contributors < 3
       or item.n_submissions is null
       or item.n_submissions < item.n_contributors;

    if violations > 0 then
        raise exception 'payload contains % cell(s) that are malformed or not k-anonymous', violations
            using errcode = '22023';
    end if;

    delete from public.h3_cells where true;
    insert into public.h3_cells (
        h3_index,
        resolution,
        n_submissions,
        n_contributors,
        latest_submission_date,
        updated_at
    )
    select
        item.h3_index,
        item.resolution::smallint,
        item.n_submissions,
        item.n_contributors,
        item.latest_submission_date,
        now()
    from jsonb_to_recordset(payload) as item (
        h3_index text,
        resolution integer,
        n_submissions integer,
        n_contributors integer,
        latest_submission_date date
    );

    get diagnostics refreshed = row_count;
    return refreshed;
end;
$$;

revoke all on function public.refresh_public_h3_cells(jsonb) from public, anon, authenticated;
grant execute on function public.refresh_public_h3_cells(jsonb) to service_role;

comment on function public.refresh_public_h3_cells(jsonb) is
    'Atomically replaces the public k-anonymous cells after a successful dataset push; rejects any cell below k = 3.';
