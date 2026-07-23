create or replace function public.refresh_public_h3_cells(payload jsonb)
returns integer
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
    refreshed integer;
begin
    if jsonb_typeof(payload) is distinct from 'array' then
        raise exception 'payload must be a JSON array' using errcode = '22023';
    end if;

    delete from public.h3_cells;
    insert into public.h3_cells (
        h3_index,
        n_submissions,
        latest_submission_date,
        updated_at
    )
    select
        item.h3_index,
        item.n_submissions,
        item.latest_submission_date,
        now()
    from jsonb_to_recordset(payload) as item (
        h3_index text,
        n_submissions integer,
        latest_submission_date date
    )
    where item.n_submissions > 0;

    get diagnostics refreshed = row_count;
    return refreshed;
end;
$$;

revoke all on function public.refresh_public_h3_cells(jsonb) from public, anon, authenticated;
grant execute on function public.refresh_public_h3_cells(jsonb) to service_role;

comment on function public.refresh_public_h3_cells(jsonb) is
    'Atomically replaces public non-synthetic H3 coverage after a successful dataset push.';
