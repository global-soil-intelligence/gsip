-- WP-6b (launch blocker 5): settle a submission's status once, from its required shots.
-- Previously a submission turned qa_pass when its first photo passed, even if shot B never
-- arrived, and a blurry optional shot C failed the whole submission. Now:
--   * the owner finalizes a submission once shots A and B exist (SPEC I2);
--   * the QA worker records a per-photo verdict in photos.qa_status;
--   * settle_submission() derives the status from shots A and B only (SPEC section 5 table).

alter table public.submissions add column finalized_at timestamptz;
comment on column public.submissions.finalized_at is
    'Set once by finalize_submission() after shots A and B exist; status settles only afterwards.';

alter table public.photos add column qa_status text
    check (qa_status in ('pass', 'fail', 'flagged', 'error'));
comment on column public.photos.qa_status is
    'Per-photo QA verdict written by the service-role worker; null while QA is pending.';

create index submissions_settle_queue_idx on public.submissions (finalized_at)
    where status = 'pending' and finalized_at is not null;

create or replace function public.finalize_submission(p_submission_id uuid)
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

revoke all on function public.finalize_submission(uuid) from public, anon, service_role;
grant execute on function public.finalize_submission(uuid) to authenticated;

comment on function public.finalize_submission(uuid) is
    'Owner-only, idempotent: records finalized_at once photo rows for shots A and B exist.';

create or replace function public.settle_submission(p_submission_id uuid)
returns text
language plpgsql
volatile
security invoker
set search_path = ''
as $$
declare
    current_status text;
    finalized timestamptz;
    shot_a text;
    shot_b text;
    next_status text;
    has_cells boolean;
begin
    select s.status, s.finalized_at, s.h3_r8 is not null and s.h3_r6 is not null
    into current_status, finalized, has_cells
    from public.submissions s
    where s.id = p_submission_id
    for update;

    if not found then
        raise exception 'submission not found' using errcode = 'P0002';
    end if;
    if finalized is null then
        return current_status;
    end if;

    select
        max(p.qa_status) filter (where p.shot_type = 'A'),
        max(p.qa_status) filter (where p.shot_type = 'B')
    into shot_a, shot_b
    from public.photos p
    where p.submission_id = p_submission_id;

    next_status := case
        when shot_a is null or shot_b is null then 'pending'
        when shot_a = 'fail' or shot_b = 'fail' then 'qa_fail'
        when shot_a in ('flagged', 'error') or shot_b in ('flagged', 'error') then 'flagged'
        -- The worker derives the H3 cells before settling; without them a pass must wait.
        when not has_cells then 'pending'
        else 'qa_pass'
    end;

    if next_status is distinct from current_status then
        update public.submissions set status = next_status where id = p_submission_id;
    end if;
    return next_status;
end;
$$;

revoke all on function public.settle_submission(uuid) from public, anon, authenticated;
grant execute on function public.settle_submission(uuid) to service_role;

comment on function public.settle_submission(uuid) is
    'Service role only: the single source of truth for submission status (SPEC section 5). Shot C never changes it.';

-- Existing rows predate finalize. Treat complete pre-v3 submissions as finalized and derive the
-- per-photo verdict from completed QA, so nothing already settled is reopened.
update public.submissions s
set finalized_at = now()
where s.finalized_at is null
  and (
      select count(distinct p.shot_type)
      from public.photos p
      where p.submission_id = s.id and p.shot_type in ('A', 'B')
  ) = 2;

update public.photos p
set qa_status = case
    when exists (
        select 1 from public.qa_events e
        where e.submission_id = p.submission_id
          and not e.passed
          and e.check_name in ('sharpness_' || p.shot_type, 'exposure_' || p.shot_type, 'is_soil_' || p.shot_type)
    ) then 'fail'
    when exists (
        select 1 from public.qa_events e
        where e.submission_id = p.submission_id
          and not e.passed
          and e.check_name in ('gps_plausibility_' || p.shot_type, 'duplicate_' || p.shot_type)
    ) then 'flagged'
    else 'pass'
end
where p.qa_status is null
  and exists (select 1 from public.qa_jobs j where j.photo_id = p.id and j.status = 'completed');

update public.photos p
set qa_status = 'error'
where p.qa_status is null
  and exists (select 1 from public.qa_jobs j where j.photo_id = p.id and j.status = 'dead_letter');

-- Re-settle every pre-v3 decision under the v3 rules: a status the old per-photo logic set without
-- passing shots A and B must not stay publishable.
create or replace function private.resettle_all_submissions()
returns integer
language plpgsql
volatile
security invoker
set search_path = ''
as $$
declare
    changed integer := 0;
    reopened integer;
    item record;
    before text;
begin
    update public.submissions
    set status = 'pending'
    where finalized_at is null and status <> 'pending';
    get diagnostics reopened = row_count;

    for item in select s.id, s.status from public.submissions s where s.finalized_at is not null loop
        before := item.status;
        if public.settle_submission(item.id) is distinct from before then
            changed := changed + 1;
        end if;
    end loop;
    return reopened + changed;
end;
$$;

revoke all on function private.resettle_all_submissions() from public, anon, authenticated;

comment on function private.resettle_all_submissions() is
    'WP-6b one-off repair: re-derives every submission status under the v3 settlement rules.';

select private.resettle_all_submissions();
