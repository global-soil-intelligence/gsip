create function public.claim_prior_job_attempt(p_submission_id uuid)
returns smallint
language sql
volatile
security invoker
set search_path = ''
as $$
    update public.prior_jobs
    set
        attempts = attempts + 1,
        last_error = null,
        started_at = now(),
        status = 'processing',
        updated_at = now()
    where submission_id = p_submission_id
      and attempts < 32
    returning attempts;
$$;

comment on function public.claim_prior_job_attempt(uuid) is
    'Atomically claims and counts one prior-enrichment attempt; service role only.';

revoke all on function public.claim_prior_job_attempt(uuid) from public, anon, authenticated;
grant execute on function public.claim_prior_job_attempt(uuid) to service_role;
