-- SPEC section 6: keep guarded rights lookups outside exposed API schemas.
-- Preserve the existing caller permissions and service-only table access.
-- Explicit restrictive policies remain deny-all; no stored rows or auth settings change.

create policy grant_withdrawals_deny_client
    on public.grant_withdrawals as restrictive
    for all to public using (false) with check (false);
create policy attribution_reviews_deny_client
    on public.attribution_reviews as restrictive
    for all to public using (false) with check (false);

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

create or replace function public.current_auth_user_exists()
returns boolean language sql stable security invoker set search_path = ''
return private.current_auth_user_exists();
revoke all on function public.current_auth_user_exists() from public, anon, authenticated, service_role;
grant execute on function public.current_auth_user_exists() to authenticated, service_role;

create or replace function public.my_submission_accepts_uploads(p_submission text)
returns boolean language sql stable security invoker set search_path = ''
return private.my_submission_accepts_uploads(p_submission);
revoke all on function public.my_submission_accepts_uploads(text) from public, anon, authenticated, service_role;
grant execute on function public.my_submission_accepts_uploads(text) to authenticated, service_role;
