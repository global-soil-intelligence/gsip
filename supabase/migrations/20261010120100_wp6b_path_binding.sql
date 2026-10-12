-- WP-6b (launch blocker 4): bind every photo's storage path to its owner, submission and shot.
-- photos.storage_path was client-written text that a privileged worker trusted. From here on the
-- database accepts only {auth_uid}/{submission_id}/{shot_type}/{uuid}.jpg, where auth_uid belongs
-- to the submission's contributor, for every role including service_role.

create or replace function private.bind_photo_storage_path()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
    owner_uid uuid;
begin
    select c.auth_uid into owner_uid
    from public.submissions s
    join public.contributors c on c.id = s.contributor_id
    where s.id = new.submission_id;

    if owner_uid is null then
        raise exception 'photo storage path cannot be bound: the submission owner has no auth identity'
            using errcode = '23514';
    end if;

    if new.storage_path is null or new.storage_path !~ (
        '^' || owner_uid::text || '/' || new.submission_id::text || '/' || new.shot_type
        || '/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jpg$'
    ) then
        raise exception 'photo storage_path must be {auth_uid}/{submission_id}/{shot_type}/{uuid}.jpg'
            using errcode = '23514';
    end if;
    return new;
end;
$$;

revoke all on function private.bind_photo_storage_path() from public, anon, authenticated;

drop trigger if exists photos_bind_storage_path on public.photos;
create trigger photos_bind_storage_path
before insert or update of storage_path, submission_id, shot_type on public.photos
for each row execute function private.bind_photo_storage_path();

comment on function private.bind_photo_storage_path() is
    'WP-6b: storage paths are derived facts, not client choices. Workers still re-derive the prefix before touching Storage.';

-- Quarantine uploads must use the same full pattern, inside the caller's own submission.
drop policy if exists incoming_photos_insert_own on storage.objects;
create policy incoming_photos_insert_own on storage.objects
    for insert to authenticated with check (
        bucket_id = 'incoming-photos'
        and name ~ (
            '^' || (select auth.uid())::text
            || '/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[ABC]/'
            || '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jpg$'
        )
        and exists (
            select 1
            from public.submissions s
            where s.id::text = (storage.foldername(name))[2]
              and s.contributor_id = public.current_contributor_id()
        )
        and public.capture_is_open()
    );

drop policy if exists incoming_photos_update_own on storage.objects;
create policy incoming_photos_update_own on storage.objects
    for update to authenticated using (
        bucket_id = 'incoming-photos'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    ) with check (
        bucket_id = 'incoming-photos'
        and name ~ (
            '^' || (select auth.uid())::text
            || '/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[ABC]/'
            || '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jpg$'
        )
    );
