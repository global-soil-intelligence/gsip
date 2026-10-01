create table public.prior_jobs (
    submission_id uuid primary key references public.submissions (id) on delete cascade,
    status text not null default 'pending'
        check (status in ('pending', 'processing', 'completed', 'dead_letter')),
    attempts smallint not null default 0 check (attempts between 0 and 32),
    last_error text check (char_length(last_error) <= 1000),
    started_at timestamptz,
    completed_at timestamptz,
    updated_at timestamptz not null default now()
);

comment on table public.prior_jobs is
    'WP4 durable prior-enrichment state; exact upstream errors remain server-only.';

create function public.enqueue_prior_job() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
    insert into public.prior_jobs (submission_id) values (new.id)
    on conflict (submission_id) do nothing;
    return new;
end;
$$;

create trigger submissions_enqueue_prior_job
after insert on public.submissions
for each row execute function public.enqueue_prior_job();

insert into public.prior_jobs (submission_id)
select id from public.submissions
on conflict (submission_id) do nothing;

alter table public.prior_jobs enable row level security;
revoke all on public.prior_jobs from public, anon, authenticated;
