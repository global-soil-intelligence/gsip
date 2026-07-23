alter table public.submissions add column if not exists gps_accuracy_m real
    check (gps_accuracy_m is null or gps_accuracy_m >= 0);
grant insert (gps_accuracy_m) on public.submissions to authenticated;

alter table public.photos add column perceptual_hash text
    check (perceptual_hash is null or perceptual_hash ~ '^[0-9a-f]{16}$');
alter table public.photos add column calibration_status text
    check (calibration_status in ('calibrated', 'uncalibrated'));

create table public.qa_jobs (
    photo_id uuid primary key references public.photos (id) on delete cascade,
    status text not null default 'pending'
        check (status in ('pending', 'processing', 'retrying', 'completed', 'dead_letter')),
    attempts smallint not null default 0 check (attempts between 0 and 4),
    last_error text check (char_length(last_error) <= 1000),
    completed_at timestamptz,
    updated_at timestamptz not null default now()
);

alter table public.qa_jobs enable row level security;
revoke all on public.qa_jobs from public, anon, authenticated;
create policy qa_jobs_server_only on public.qa_jobs for all to anon, authenticated
    using (false) with check (false);

create function public.enqueue_qa_job() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
    insert into public.qa_jobs (photo_id) values (new.id)
    on conflict (photo_id) do nothing;
    return new;
end;
$$;
revoke execute on function public.enqueue_qa_job() from public, anon, authenticated;
create trigger photos_enqueue_qa_job after insert on public.photos
for each row execute function public.enqueue_qa_job();

insert into public.qa_jobs (photo_id) select id from public.photos
on conflict (photo_id) do nothing;
