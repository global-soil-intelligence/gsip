-- Bring the existing v2.1 development database to the canonical v2.2 schema.

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

create table public.contribution_grants (
    id uuid primary key default gen_random_uuid(),
    contributor_id uuid not null references public.contributors (id),
    terms_version text not null check (char_length(terms_version) between 1 and 64),
    accepted_at timestamptz not null,
    data_license text not null default 'ODbL-1.0' check (data_license = 'ODbL-1.0'),
    photo_license text not null default 'CC-BY-SA-4.0' check (photo_license = 'CC-BY-SA-4.0'),
    attribution_name text not null check (char_length(attribution_name) between 1 and 80),
    unique (id, contributor_id)
);

comment on table public.contribution_grants is
    'I6: immutable per-submission acceptance snapshot for structured data and photo licensing.';

do $$
begin
    if exists (
        select 1 from public.submissions s
        join public.contributors c on c.id = s.contributor_id
        where c.terms_version is null or c.terms_accepted_at is null
    ) then
        raise exception 'Cannot migrate submissions without recorded contribution terms';
    end if;
end;
$$;

insert into public.contribution_grants (
    contributor_id, terms_version, accepted_at, attribution_name
)
select c.id, c.terms_version, c.terms_accepted_at, c.handle
from public.contributors c
where c.terms_version is not null
  and exists (select 1 from public.submissions s where s.contributor_id = c.id)
  and not exists (
      select 1 from public.contribution_grants g where g.contributor_id = c.id
  );

alter table public.submissions add column grant_id uuid;
update public.submissions s
set grant_id = g.id
from public.contribution_grants g
where g.contributor_id = s.contributor_id and s.grant_id is null;
alter table public.submissions alter column grant_id set not null;
alter table public.submissions add constraint submissions_grant_owner_fkey
    foreign key (grant_id, contributor_id)
    references public.contribution_grants (id, contributor_id);
create index submissions_grant_idx on public.submissions (grant_id);

alter table public.contributors drop constraint terms_recorded_together;
alter table public.contributors drop column terms_version;
alter table public.contributors drop column terms_accepted_at;
comment on table public.contributors is 'Contributor profiles; licensing acceptance lives in immutable grants.';

alter table public.photos rename column exif to camera_metadata_private;
alter table public.photos add constraint photos_submission_shot_key unique (submission_id, shot_type);
alter table public.photos add constraint photos_camera_metadata_allowlist check (
    camera_metadata_private is null
    or (
        jsonb_typeof(camera_metadata_private) = 'object'
        and camera_metadata_private - array[
            'make', 'model', 'focal_length_mm', 'exposure_time_s', 'f_number', 'iso'
        ]::text[] = '{}'::jsonb
    )
);
comment on column public.photos.camera_metadata_private is
    'I7: private allowlisted non-location camera fields; raw EXIF/XMP is forbidden.';

alter table public.priors drop constraint priors_pkey;
alter table public.priors add column unit text;
alter table public.priors add column depth_top_cm integer;
alter table public.priors add column depth_bottom_cm integer;
update public.priors set
    unit = case property
        when 'ph' then 'pH'
        when 'bd' then 'kg/dm3'
        when 'cec' then 'cmol(+)/kg'
        else 'g/kg'
    end,
    depth_top_cm = case source_depth
        when '0-5cm' then 0 when '0-5' then 0 when '0_5' then 0
        when '0-30cm' then 0 when '0-30' then 0 when '0_30' then 0
    end,
    depth_bottom_cm = case source_depth
        when '0-5cm' then 5 when '0-5' then 5 when '0_5' then 5
        when '0-30cm' then 30 when '0-30' then 30 when '0_30' then 30
    end;
alter table public.priors alter column unit set not null;
alter table public.priors alter column depth_top_cm set not null;
alter table public.priors alter column depth_bottom_cm set not null;
alter table public.priors drop column source_depth;
alter table public.priors add constraint priors_canonical_unit check (
    (property in ('soc', 'clay', 'sand', 'silt', 'n') and unit = 'g/kg')
    or (property = 'ph' and unit = 'pH')
    or (property = 'bd' and unit = 'kg/dm3')
    or (property = 'cec' and unit = 'cmol(+)/kg')
);
alter table public.priors add constraint priors_depth_bounds check (
    0 <= depth_top_cm and depth_top_cm < depth_bottom_cm and depth_bottom_cm <= 200
);
alter table public.priors add constraint priors_uncertainty_order check (
    uncertainty_lo is null or uncertainty_hi is null or uncertainty_lo <= uncertainty_hi
);
alter table public.priors add primary key (
    submission_id, source, property, depth_top_cm, depth_bottom_cm
);

alter table public.gold_labels add column unit text;
alter table public.gold_labels add column depth_top_cm integer;
alter table public.gold_labels add column depth_bottom_cm integer;
update public.gold_labels set
    unit = case property
        when 'ph' then 'pH'
        when 'bd' then 'kg/dm3'
        when 'cec' then 'cmol(+)/kg'
        else 'g/kg'
    end,
    depth_top_cm = case sampled_depth
        when '0-5cm' then 0 when '0-5' then 0 when '0_5' then 0
        when '0-30cm' then 0 when '0-30' then 0 when '0_30' then 0
    end,
    depth_bottom_cm = case sampled_depth
        when '0-5cm' then 5 when '0-5' then 5 when '0_5' then 5
        when '0-30cm' then 30 when '0-30' then 30 when '0_30' then 30
    end;
alter table public.gold_labels alter column unit set not null;
alter table public.gold_labels alter column depth_top_cm set not null;
alter table public.gold_labels alter column depth_bottom_cm set not null;
alter table public.gold_labels drop column sampled_depth;
alter table public.gold_labels add constraint gold_labels_canonical_unit check (
    (property in ('soc', 'clay', 'sand', 'silt', 'n') and unit = 'g/kg')
    or (property = 'ph' and unit = 'pH')
    or (property = 'bd' and unit = 'kg/dm3')
    or (property = 'cec' and unit = 'cmol(+)/kg')
);
alter table public.gold_labels add constraint gold_labels_depth_bounds check (
    0 <= depth_top_cm and depth_top_cm < depth_bottom_cm and depth_bottom_cm <= 200
);
alter table public.gold_labels add constraint gold_labels_uncertainty_nonnegative check (
    uncertainty is null or uncertainty >= 0
);

alter table public.predictions add column unit text;
update public.predictions set unit = case property
    when 'ph' then 'pH'
    when 'bd' then 'kg/dm3'
    when 'cec' then 'cmol(+)/kg'
    else 'g/kg'
end;
alter table public.predictions alter column unit set not null;
alter table public.predictions add constraint predictions_canonical_unit check (
    (property in ('soc', 'clay', 'sand', 'silt', 'n') and unit = 'g/kg')
    or (property = 'ph' and unit = 'pH')
    or (property = 'bd' and unit = 'kg/dm3')
    or (property = 'cec' and unit = 'cmol(+)/kg')
);

create or replace function public.current_contributor_id()
returns uuid language sql stable security invoker set search_path = public as $$
    select id from public.contributors where auth_uid = (select auth.uid());
$$;
revoke execute on function public.current_contributor_id from public, anon;
grant execute on function public.current_contributor_id to authenticated;

create function private.reject_contribution_grant_mutation()
returns trigger language plpgsql security invoker set search_path = '' as $$
begin
    raise exception 'contribution_grants are immutable';
end;
$$;
create trigger contribution_grants_immutable
before update or delete on public.contribution_grants
for each row execute function private.reject_contribution_grant_mutation();

alter table public.contribution_grants enable row level security;
create policy contribution_grants_select_own on public.contribution_grants
    for select to authenticated
    using (contributor_id = public.current_contributor_id());
create policy contribution_grants_insert_own on public.contribution_grants
    for insert to authenticated
    with check (
        contributor_id = public.current_contributor_id()
        and accepted_at <= now()
    );

revoke all on public.contributors, public.contribution_grants, public.submissions,
    public.photos, public.priors, public.gold_labels, public.predictions,
    public.qa_events, public.h3_cells from anon, authenticated;
grant select on public.contributors to authenticated;
grant insert (auth_uid, handle) on public.contributors to authenticated;
grant update (handle, precise_location_optin) on public.contributors to authenticated;
grant select, insert on public.contribution_grants to authenticated;
grant select on public.submissions to authenticated;
grant insert (
    contributor_id, grant_id, geom_precise, h3_r8, h3_r6, captured_at,
    land_cover, surface_condition, disturbed, device_model, status
) on public.submissions to authenticated;
grant select (
    id, h3_r8, h3_r6, captured_at, land_cover, surface_condition,
    disturbed, precip_flag, elevation, status
) on public.submissions to anon;
grant select, insert on public.photos to authenticated;
grant select on public.priors, public.gold_labels, public.predictions, public.qa_events
    to authenticated;
grant select on public.h3_cells to anon, authenticated;

revoke all on public.public_submissions from public, anon, authenticated;
grant select on public.public_submissions to anon, authenticated;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
    ('incoming-photos', 'incoming-photos', false, 12582912, array['image/jpeg']),
    ('submission-photos', 'submission-photos', false, 12582912, array['image/jpeg'])
on conflict (id) do update set
    public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

create policy incoming_photos_insert_own on storage.objects
    for insert to authenticated with check (
        bucket_id = 'incoming-photos'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );
create policy incoming_photos_select_own on storage.objects
    for select to authenticated using (
        bucket_id = 'incoming-photos'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );
create policy incoming_photos_update_own on storage.objects
    for update to authenticated using (
        bucket_id = 'incoming-photos'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    ) with check (
        bucket_id = 'incoming-photos'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );
create policy incoming_photos_delete_own on storage.objects
    for delete to authenticated using (
        bucket_id = 'incoming-photos'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );
create policy submission_photos_select_own on storage.objects
    for select to authenticated using (
        bucket_id = 'submission-photos'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );

comment on view public.public_submissions is
    'I7: safe H3-only public window. No precise geometry, contributor ID, device model, grants, or camera metadata.';
