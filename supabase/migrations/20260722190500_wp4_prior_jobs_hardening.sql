revoke execute on function public.enqueue_prior_job() from public, anon, authenticated;

create policy prior_jobs_server_only
on public.prior_jobs
for all
to anon, authenticated
using (false)
with check (false);
