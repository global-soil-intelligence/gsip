-- WP-6d (launch blocker 7, mechanisms; counsel still approves the text): contributor rights.
--   * deletion_requests: a contributor asks to withdraw their contributions or delete their
--     account. Owners create and read only their own requests, with at most one open at a time.
--   * grant_withdrawals: append-only. A request withdraws the contributor's grants the moment it
--     is made, so the next release already excludes them (SPEC section 6); the daily rights worker
--     (pipeline/rights_worker.py) then deletes the rows and objects.
--   * A withdrawn grant can never gain a new submission.
--   * attribution_reviews: a typed attribution name is published with photos only once approved.
--   * Grants stay immutable. The single exception is account deletion, which replaces the
--     attribution names on the deleted account's (already withdrawn) grants with the default
--     pseudonym; ids, terms version, dates and licences remain as the record of what was granted.

create table public.deletion_requests (
    id uuid primary key default gen_random_uuid(),
    contributor_id uuid not null references public.contributors (id),
    kind text not null check (kind in ('withdraw_contributions', 'delete_account')),
    status text not null default 'pending'
        check (status in ('pending', 'processing', 'completed')),
    requested_at timestamptz not null default now(),
    claimed_at timestamptz,
    not_before timestamptz,
    completed_at timestamptz,
    attempts smallint not null default 0 check (attempts >= 0),
    last_error text check (char_length(last_error) <= 1000),
    constraint deletion_requests_completion_recorded
        check ((status = 'completed') = (completed_at is not null))
);

create unique index deletion_requests_one_open
    on public.deletion_requests (contributor_id) where status <> 'completed';
create index deletion_requests_queue_idx on public.deletion_requests (status, requested_at);

comment on table public.deletion_requests is
    'WP-6d: a contributor''s request to withdraw contributions or delete the account. Owners insert and read their own (at most one open); the rights worker processes them daily.';

alter table public.deletion_requests enable row level security;
revoke all on public.deletion_requests from public, anon, authenticated;
grant select (id, kind, status, requested_at, completed_at) on public.deletion_requests
    to authenticated;
grant insert (contributor_id, kind) on public.deletion_requests to authenticated;
grant select, insert, update on public.deletion_requests to service_role;
create policy deletion_requests_select_own on public.deletion_requests
    for select to authenticated
    using (contributor_id = public.current_contributor_id());
create policy deletion_requests_insert_own on public.deletion_requests
    for insert to authenticated
    with check (contributor_id = public.current_contributor_id());

create table public.grant_withdrawals (
    grant_id uuid primary key references public.contribution_grants (id),
    request_id uuid references public.deletion_requests (id),
    reason text not null
        check (reason in ('contributor_request', 'account_deletion', 'steward_action')),
    withdrawn_at timestamptz not null default now()
);

comment on table public.grant_withdrawals is
    'WP-6d: append-only. A withdrawn grant''s observations never enter a later release and are deleted by the rights worker; a grant itself is never rewritten.';

alter table public.grant_withdrawals enable row level security;
revoke all on public.grant_withdrawals from public, anon, authenticated;
grant select, insert on public.grant_withdrawals to service_role;

create function private.reject_grant_withdrawal_mutation()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    raise exception 'grant_withdrawals are append-only';
end;
$$;

create trigger grant_withdrawals_append_only
before update or delete on public.grant_withdrawals
for each row execute function private.reject_grant_withdrawal_mutation();

-- A request takes effect for publication at once: every grant the contributor holds is withdrawn
-- in the same transaction as the request, whatever the worker's schedule.
create function private.withdraw_grants_on_request()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.grant_withdrawals (grant_id, request_id, reason)
    select
        g.id,
        new.id,
        case new.kind when 'delete_account' then 'account_deletion' else 'contributor_request' end
    from public.contribution_grants g
    where g.contributor_id = new.contributor_id
    on conflict (grant_id) do nothing;
    return new;
end;
$$;

revoke all on function private.withdraw_grants_on_request() from public, anon, authenticated;

create trigger deletion_requests_withdraw_grants
after insert on public.deletion_requests
for each row execute function private.withdraw_grants_on_request();

-- A device that queued an observation before its owner withdrew must not attach it to a withdrawn
-- grant: it would never be released, and no request would delete it.
create function private.refuse_withdrawn_grant()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    if exists (select 1 from public.grant_withdrawals w where w.grant_id = new.grant_id) then
        raise exception 'contribution grant % has been withdrawn', new.grant_id
            using errcode = '42501';
    end if;
    return new;
end;
$$;

revoke all on function private.refuse_withdrawn_grant() from public, anon, authenticated;

create trigger submissions_refuse_withdrawn_grant
before insert or update of grant_id on public.submissions
for each row execute function private.refuse_withdrawn_grant();

-- Grants remain immutable, except that account deletion may replace the attribution name of a
-- withdrawn grant with the default pseudonym, through complete_deletion_request() only.
create or replace function private.reject_contribution_grant_mutation()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    if tg_op = 'UPDATE'
        and current_setting('gsip.redacting_attribution', true) = 'on'
        and new.attribution_name = 'Anonymous soil contributor'
        and (to_jsonb(new) - 'attribution_name') = (to_jsonb(old) - 'attribution_name')
        and exists (select 1 from public.grant_withdrawals w where w.grant_id = old.id)
    then
        return new;
    end if;
    raise exception 'contribution_grants are immutable';
end;
$$;

create table public.attribution_reviews (
    contributor_id uuid not null references public.contributors (id),
    attribution_name text not null check (char_length(attribution_name) between 1 and 80),
    decision text not null check (decision in ('approved', 'rejected')),
    reviewer text not null check (char_length(reviewer) between 1 and 80),
    note text check (char_length(note) <= 500),
    reviewed_at timestamptz not null default now(),
    primary key (contributor_id, attribution_name)
);

comment on table public.attribution_reviews is
    'WP-6d: a typed attribution name is published with photos only once approved here for that contributor. Until then the observation is released without photos.';

alter table public.attribution_reviews enable row level security;
revoke all on public.attribution_reviews from public, anon, authenticated;
grant select, insert, update, delete on public.attribution_reviews to service_role;

create view public.attribution_review_queue
with (security_invoker = true)
as
select
    g.contributor_id,
    g.attribution_name,
    min(g.accepted_at) as first_accepted_at,
    count(*)::integer as grants
from public.contribution_grants g
where g.attribution_name <> 'Anonymous soil contributor'
  and not exists (select 1 from public.grant_withdrawals w where w.grant_id = g.id)
  and not exists (
      select 1 from public.attribution_reviews a
      where a.contributor_id = g.contributor_id and a.attribution_name = g.attribution_name
  )
group by g.contributor_id, g.attribution_name;

comment on view public.attribution_review_queue is
    'WP-6d: typed attribution names awaiting review (service role; pipeline/attribution_review.py).';

revoke all on public.attribution_review_queue from public, anon, authenticated;
grant select on public.attribution_review_queue to service_role;

-- The rights worker's steps. Each is idempotent, so a failure anywhere leaves the request retryable.

create or replace function public.claim_deletion_request(
    p_stale interval default interval '1 hour'
)
returns table (
    request_id uuid,
    contributor_id uuid,
    kind text,
    auth_uid uuid,
    attempts smallint
)
language plpgsql
volatile
security invoker
set search_path = ''
as $$
begin
    return query
    with next_request as (
        select r.id
        from public.deletion_requests r
        where (r.status = 'pending' and (r.not_before is null or r.not_before <= now()))
           or (r.status = 'processing' and r.claimed_at < now() - p_stale)
        order by r.requested_at
        limit 1
        for update skip locked
    ), claimed as (
        update public.deletion_requests r
        set status = 'processing', claimed_at = now(), attempts = r.attempts + 1
        from next_request
        where r.id = next_request.id
        returning r.id, r.contributor_id, r.kind, r.attempts
    )
    select claimed.id, claimed.contributor_id, claimed.kind, c.auth_uid, claimed.attempts
    from claimed
    join public.contributors c on c.id = claimed.contributor_id;
end;
$$;

create or replace function public.apply_deletion_request(p_request_id uuid)
returns table (withdrawn_grants integer, deleted_submissions integer)
language plpgsql
volatile
security invoker
set search_path = ''
as $$
declare
    request_contributor uuid;
    request_kind text;
    request_status text;
    withdrawn integer := 0;
    deleted integer := 0;
begin
    select r.contributor_id, r.kind, r.status
    into request_contributor, request_kind, request_status
    from public.deletion_requests r
    where r.id = p_request_id
    for update;
    if not found then
        raise exception 'deletion request % not found', p_request_id using errcode = 'P0002';
    end if;
    if request_status <> 'processing' then
        raise exception 'deletion request % is not claimed', p_request_id using errcode = '55000';
    end if;

    -- An account deletion covers grants created after the request too.
    if request_kind = 'delete_account' then
        insert into public.grant_withdrawals (grant_id, request_id, reason)
        select g.id, p_request_id, 'account_deletion'
        from public.contribution_grants g
        where g.contributor_id = request_contributor
        on conflict (grant_id) do nothing;
        get diagnostics withdrawn = row_count;
    end if;

    -- Every submission under a withdrawn grant goes, with its photos, priors, QA events, jobs,
    -- gold labels and predictions (all cascade). Contributions made under a new grant after a
    -- withdrawal request stay.
    delete from public.submissions s
    where s.contributor_id = request_contributor
      and exists (select 1 from public.grant_withdrawals w where w.grant_id = s.grant_id);
    get diagnostics deleted = row_count;

    return query select withdrawn, deleted;
end;
$$;

create or replace function public.complete_deletion_request(p_request_id uuid)
returns void
language plpgsql
volatile
security invoker
set search_path = ''
as $$
declare
    request_contributor uuid;
    request_kind text;
    request_status text;
begin
    select r.contributor_id, r.kind, r.status
    into request_contributor, request_kind, request_status
    from public.deletion_requests r
    where r.id = p_request_id
    for update;
    if not found then
        raise exception 'deletion request % not found', p_request_id using errcode = 'P0002';
    end if;
    if request_status = 'completed' then
        return;
    end if;
    if request_status <> 'processing' then
        raise exception 'deletion request % is not claimed', p_request_id using errcode = '55000';
    end if;
    if exists (
        select 1 from public.submissions s
        join public.grant_withdrawals w on w.grant_id = s.grant_id
        where s.contributor_id = request_contributor
    ) or (
        request_kind = 'delete_account'
        and exists (select 1 from public.submissions s where s.contributor_id = request_contributor)
    ) then
        raise exception 'withdrawn contributions remain; apply the request first'
            using errcode = '55000';
    end if;

    if request_kind = 'delete_account' then
        perform set_config('gsip.redacting_attribution', 'on', true);
        update public.contribution_grants g
        set attribution_name = 'Anonymous soil contributor'
        where g.contributor_id = request_contributor
          and g.attribution_name <> 'Anonymous soil contributor';
        perform set_config('gsip.redacting_attribution', 'off', true);

        delete from public.attribution_reviews a where a.contributor_id = request_contributor;

        update public.contributors c
        set
            auth_uid = null,
            handle = 'deleted-' || substr(replace(c.id::text, '-', ''), 1, 24),
            precise_location_optin = false
        where c.id = request_contributor;
    end if;

    update public.deletion_requests r
    set status = 'completed', completed_at = now(), last_error = null
    where r.id = p_request_id;
end;
$$;

create or replace function public.release_deletion_request(
    p_request_id uuid,
    p_error text,
    p_retry_after interval default interval '1 hour'
)
returns void
language sql
volatile
security invoker
set search_path = ''
as $$
    update public.deletion_requests
    set
        status = 'pending',
        claimed_at = null,
        not_before = now() + p_retry_after,
        last_error = left(p_error, 1000)
    where id = p_request_id and status = 'processing';
$$;

revoke all on function public.claim_deletion_request(interval) from public, anon, authenticated;
revoke all on function public.apply_deletion_request(uuid) from public, anon, authenticated;
revoke all on function public.complete_deletion_request(uuid) from public, anon, authenticated;
revoke all on function public.release_deletion_request(uuid, text, interval) from public, anon, authenticated;
grant execute on function public.claim_deletion_request(interval) to service_role;
grant execute on function public.apply_deletion_request(uuid) to service_role;
grant execute on function public.complete_deletion_request(uuid) to service_role;
grant execute on function public.release_deletion_request(uuid, text, interval) to service_role;

comment on function public.claim_deletion_request(interval) is
    'Service role only: claims the oldest pending deletion request (or one stuck in processing) and returns what the worker needs, including the auth user id for Storage and Auth.';
comment on function public.apply_deletion_request(uuid) is
    'Service role only: withdraws any remaining grants of a deleted account and deletes every submission under a withdrawn grant (cascading). Idempotent.';
comment on function public.complete_deletion_request(uuid) is
    'Service role only: for an account deletion, replaces attribution names with the default pseudonym, removes attribution reviews and pseudonymizes the contributor; then marks the request completed. Refuses while withdrawn submissions remain.';
comment on function public.release_deletion_request(uuid, text, interval) is
    'Service role only: returns a claimed request to pending after a failed step, not to be retried before the given delay, keeping the error for the operator.';

-- Catch-all for I7: no canonical photo object may outlive its photo row (a race with a withdrawal,
-- or a failed compensating delete). Objects must be deleted through the Storage API, so this only
-- lists them; the rights worker deletes them daily.
create index if not exists photos_storage_path_idx on public.photos (storage_path);

create or replace function public.orphaned_photo_objects(p_limit integer default 1000)
returns table (name text)
language sql
stable
security definer
set search_path = ''
as $$
    select o.name
    from storage.objects o
    where o.bucket_id = 'submission-photos'
      and not exists (select 1 from public.photos p where p.storage_path = o.name)
    order by o.created_at, o.name
    limit greatest(1, least(coalesce(p_limit, 1000), 1000));
$$;

revoke all on function public.orphaned_photo_objects(integer) from public, anon, authenticated;
grant execute on function public.orphaned_photo_objects(integer) to service_role;

comment on function public.orphaned_photo_objects(integer) is
    'Service role only: canonical photo objects with no photo row (at most 1000 per call), for the rights worker to delete through the Storage API.';
