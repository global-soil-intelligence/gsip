-- Phase-1 actor hardening. The hosted tier does not provide h3-pg, so client
-- H3 values are treated as untrusted hints and cleared before persistence.
-- The service-role QA worker derives both cells from geom_precise before a
-- submission can transition to a public status.

alter table public.submissions add column if not exists gps_accuracy_m real
    check (gps_accuracy_m is null or gps_accuracy_m >= 0);

alter table public.submissions alter column h3_r8 drop not null;
alter table public.submissions alter column h3_r6 drop not null;
alter table public.submissions add constraint submissions_public_h3_required
    check (status <> 'qa_pass' or (h3_r8 is not null and h3_r6 is not null));

create or replace function private.clear_untrusted_submission_h3()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    if current_user = 'authenticated' then
        new.h3_r8 := null;
        new.h3_r6 := null;
    end if;
    return new;
end;
$$;

revoke execute on function private.clear_untrusted_submission_h3() from public, anon, authenticated;

drop trigger if exists submissions_clear_untrusted_h3 on public.submissions;
create trigger submissions_clear_untrusted_h3
before insert or update of geom_precise, h3_r8, h3_r6 on public.submissions
for each row execute function private.clear_untrusted_submission_h3();

revoke insert on public.submissions from authenticated;
grant insert (
    id, contributor_id, grant_id, geom_precise, h3_r8, h3_r6, captured_at,
    land_cover, surface_condition, disturbed, device_model, gps_accuracy_m, status
) on public.submissions to authenticated;

revoke insert on public.photos from authenticated;
grant insert (submission_id, shot_type, storage_path) on public.photos to authenticated;

grant select, insert, update, delete on
    public.contributors,
    public.contribution_grants,
    public.submissions,
    public.photos,
    public.priors,
    public.gold_labels,
    public.predictions,
    public.qa_events,
    public.h3_cells
to service_role;

do $$
begin
    if to_regclass('public.prior_jobs') is not null then
        grant select, insert, update, delete on public.prior_jobs to service_role;
    end if;
    if to_regclass('public.qa_jobs') is not null then
        grant select, insert, update, delete on public.qa_jobs to service_role;
    end if;
end;
$$;

comment on function private.clear_untrusted_submission_h3() is
    'I8 containment: client H3 assertions never persist; trusted QA derives H3 from private geometry.';
