-- LOCAL PROPOSAL ONLY: NOT EXECUTED IN PRODUCTION OR CHECKED-IN SOURCE.
-- Spec-first privilege-boundary review and full isolated role tests are prerequisites.
-- No old migration changes, RLS weakening, private schema/table grants or suppression.
create policy grant_withdrawals_deny_client
    on public.grant_withdrawals as restrictive
    for all to public using (false) with check (false);
create policy attribution_reviews_deny_client
    on public.attribution_reviews as restrictive
    for all to public using (false) with check (false);

-- At most one switch row is enforced by the existing singleton PK/check.
-- Avoid singleton in the query so existing column-only client SELECT suffices.
create or replace function public.capture_is_open()
returns boolean language sql stable security invoker set search_path = ''
as $$ select coalesce((select s.capture_open from public.service_state s), false); $$;
revoke all on function public.capture_is_open() from public, anon, authenticated, service_role;
grant execute on function public.capture_is_open() to anon, authenticated, service_role;

create function private.finalize_submission(p_submission_id uuid)
returns timestamptz
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
    finalized timestamptz;
    caller uuid := (select auth.uid());
begin
    if caller is null then
        raise exception 'authentication required' using errcode = '42501';
    end if;

    select s.finalized_at into finalized
    from public.submissions s
    join public.contributors c on c.id = s.contributor_id
    where s.id = p_submission_id and c.auth_uid = caller
    for update of s;

    if not found then
        raise exception 'submission not found' using errcode = 'P0002';
    end if;
    if finalized is not null then
        return finalized;
    end if;

    if (
        select count(distinct p.shot_type)
        from public.photos p
        where p.submission_id = p_submission_id and p.shot_type in ('A', 'B')
    ) < 2 then
        raise exception 'shots A and B are required before a submission can be finalized'
            using errcode = '23514';
    end if;

    update public.submissions
    set finalized_at = now()
    where id = p_submission_id
    returning finalized_at into finalized;
    return finalized;
end;
$$;

revoke all on function private.finalize_submission(uuid) from public, anon, authenticated, service_role;
grant execute on function private.finalize_submission(uuid) to authenticated;

create function private.current_auth_user_exists()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select exists (select 1 from auth.users u where u.id = (select auth.uid()));
$$;

revoke all on function private.current_auth_user_exists() from public, anon, authenticated, service_role;
grant execute on function private.current_auth_user_exists() to authenticated, service_role;

create function private.my_submission_accepts_uploads(p_submission text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select exists (
        select 1
        from public.submissions s
        join public.contributors c on c.id = s.contributor_id
        where s.id::text = p_submission
          and c.auth_uid = (select auth.uid())
          and not exists (select 1 from public.grant_withdrawals w where w.grant_id = s.grant_id)
    );
$$;

revoke all on function private.my_submission_accepts_uploads(text) from public, anon, authenticated, service_role;
grant execute on function private.my_submission_accepts_uploads(text) to authenticated, service_role;

-- SQL-standard body resolves its private callee at definition time; no private USAGE.
create or replace function public.finalize_submission(p_submission_id uuid)
returns timestamptz language sql volatile security invoker set search_path = ''
return private.finalize_submission(p_submission_id);
revoke all on function public.finalize_submission(uuid) from public, anon, authenticated, service_role;
grant execute on function public.finalize_submission(uuid) to authenticated;

-- SQL-standard body resolves its private callee at definition time; no private USAGE.
create or replace function public.current_auth_user_exists()
returns boolean language sql stable security invoker set search_path = ''
return private.current_auth_user_exists();
revoke all on function public.current_auth_user_exists() from public, anon, authenticated, service_role;
grant execute on function public.current_auth_user_exists() to authenticated, service_role;

-- SQL-standard body resolves its private callee at definition time; no private USAGE.
create or replace function public.my_submission_accepts_uploads(p_submission text)
returns boolean language sql stable security invoker set search_path = ''
return private.my_submission_accepts_uploads(p_submission);
revoke all on function public.my_submission_accepts_uploads(text) from public, anon, authenticated, service_role;
grant execute on function public.my_submission_accepts_uploads(text) to authenticated, service_role;

