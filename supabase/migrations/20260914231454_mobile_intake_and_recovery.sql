-- Mobile intake is fail-closed. Enable explicitly for a controlled beta.
create table public.intake_settings (
    id boolean primary key default true check (id),
    enabled boolean not null default false
);
insert into public.intake_settings (enabled) values (false);
alter table public.intake_settings enable row level security;
grant select on public.intake_settings to anon, authenticated;
grant all on public.intake_settings to service_role;
create policy intake_settings_read on public.intake_settings for select to anon, authenticated using (true);

create function public.is_intake_open() returns boolean
language sql stable security invoker set search_path = '' as $$
    select coalesce((select enabled from public.intake_settings where id), false);
$$;
revoke all on function public.is_intake_open() from public;
grant execute on function public.is_intake_open() to anon, authenticated, service_role;

create policy submissions_intake_open on public.submissions as restrictive
    for insert to authenticated with check (public.is_intake_open());
create policy grants_intake_open on public.contribution_grants as restrictive
    for insert to authenticated with check (public.is_intake_open());
create policy photos_intake_open on public.photos as restrictive
    for insert to authenticated with check (public.is_intake_open());
create policy storage_intake_open on storage.objects as restrictive
    for insert to authenticated with check (bucket_id <> 'incoming-photos' or public.is_intake_open());
create policy storage_intake_update_open on storage.objects as restrictive
    for update to authenticated using (bucket_id <> 'incoming-photos' or public.is_intake_open())
    with check (bucket_id <> 'incoming-photos' or public.is_intake_open());

alter table public.submissions
    add column expected_shots text[] not null default array['A','B']::text[],
    add column upload_completed_at timestamptz,
    add constraint submissions_expected_shots check (
        expected_shots = array['A','B']::text[] or expected_shots = array['A','B','C']::text[]
    );
grant insert (expected_shots) on public.submissions to authenticated;

-- A completed upload is immutable from the client. Bind photo paths to their owner and shot.
create policy photos_upload_membership on public.photos as restrictive
for insert to authenticated with check (
    exists (select 1 from public.submissions s
        where s.id = submission_id and s.upload_completed_at is null
          and shot_type = any(s.expected_shots))
    and storage_path ~ ('^' || (select auth.uid())::text || '/' || submission_id::text || '/' || shot_type || '/[0-9a-f-]+\.jpg$')
);

create function public.complete_submission_upload(p_submission_id uuid) returns void
language plpgsql security definer set search_path = '' as $$
declare s public.submissions;
begin
    if auth.uid() is null or not public.is_intake_open() then
        raise exception 'Intake is closed';
    end if;
    select * into s from public.submissions
        where id = p_submission_id and contributor_id in
            (select id from public.contributors where auth_uid = auth.uid()) for update;
    if not found then raise exception 'Submission unavailable'; end if;
    if s.upload_completed_at is not null then return; end if;
    if (select count(*) from public.photos where submission_id = s.id) <> cardinality(s.expected_shots)
       or exists (select 1 from unnest(s.expected_shots) shot
          where not exists (select 1 from public.photos p join storage.objects o
            on o.bucket_id = 'incoming-photos' and o.name = p.storage_path
            where p.submission_id = s.id and p.shot_type = shot
              and split_part(p.storage_path, '/', 1) = auth.uid()::text)) then
        raise exception 'Required photos have not finished uploading';
    end if;
    update public.submissions set upload_completed_at = now() where id = s.id;
end;
$$;
revoke all on function public.complete_submission_upload(uuid) from public, anon;
grant execute on function public.complete_submission_upload(uuid) to authenticated;

-- Trust only a complete set of worker outcomes. Never infer success from absent events.
create function public.reconcile_submission_qa(p_submission_id uuid, p_h3_r6 text, p_h3_r8 text)
returns text language plpgsql security invoker set search_path = '' as $$
declare s public.submissions; result text := 'pending';
begin
    select * into s from public.submissions where id = p_submission_id for update;
    if not found then raise exception 'Submission unavailable'; end if;
    if s.upload_completed_at is not null then
        if exists (select 1 from public.photos p join public.qa_jobs j on j.photo_id = p.id
            where p.submission_id = s.id and j.status = 'dead_letter') then
            result := 'qa_fail';
        elsif not exists (select 1 from unnest(s.expected_shots) shot
            where not exists (select 1 from public.photos p join public.qa_jobs j on j.photo_id = p.id
                where p.submission_id = s.id and p.shot_type = shot and j.status = 'completed'))
          and not exists (select 1 from public.photos p
            cross join unnest(array['sharpness','exposure','card_detection','gps_plausibility','duplicate']) c
            where p.submission_id = s.id and not exists (select 1 from public.qa_events e
                where e.submission_id = s.id and e.check_name = c || '_' || p.shot_type)) then
            result := 'qa_pass';
            if exists (select 1 from public.qa_events where submission_id = s.id and not passed
                and check_name ~ '^(gps_plausibility|duplicate)_') then result := 'flagged'; end if;
            if exists (select 1 from public.qa_events where submission_id = s.id and not passed
                and check_name ~ '^(sharpness|exposure|is_soil)_') then result := 'qa_fail'; end if;
        end if;
    end if;
    update public.submissions set status = result, h3_r6 = p_h3_r6, h3_r8 = p_h3_r8 where id = s.id;
    return result;
end;
$$;
revoke all on function public.reconcile_submission_qa(uuid,text,text) from public, anon, authenticated;
grant execute on function public.reconcile_submission_qa(uuid,text,text) to service_role;

-- Expired leases are retryable; an active claim cannot be claimed twice.
create or replace function public.claim_prior_job_attempt(p_submission_id uuid)
returns smallint language sql volatile security invoker set search_path = '' as $$
    update public.prior_jobs set attempts = attempts + 1, last_error = null,
        started_at = now(), status = 'processing', updated_at = now()
    where submission_id = p_submission_id and attempts < 32
      and (status in ('pending','dead_letter') or
          (status = 'processing' and updated_at < now() - interval '15 minutes'))
    returning attempts;
$$;

create function public.requeue_stale_prior_jobs() returns void
language sql volatile security invoker set search_path = '' as $$
    update public.prior_jobs set status = 'dead_letter', last_error = 'processing_lease_expired', updated_at = now()
    where status = 'processing' and updated_at < now() - interval '15 minutes';
$$;
revoke all on function public.requeue_stale_prior_jobs() from public, anon, authenticated;
grant execute on function public.requeue_stale_prior_jobs() to service_role;
