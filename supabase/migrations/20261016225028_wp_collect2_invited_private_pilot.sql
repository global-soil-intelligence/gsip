-- WP-COLLECT-2: invited owner-private collection only. No enrollment, gate or publication go.
-- Existing payloads/rights/provenance and gate values are preserved; all new observations stay private.
create table private.collection_pilot_members (
    auth_uid uuid primary key references auth.users(id) on delete cascade,
    revoked_at timestamptz
);
alter table private.collection_pilot_members enable row level security;
revoke all on private.collection_pilot_members from public, anon, authenticated, service_role;
create policy collection_pilot_members_deny_client on private.collection_pilot_members
    as restrictive for all to public using(false) with check(false);
comment on table private.collection_pilot_members is
    'Owner-admin provisioned invitations only. No client/member enumeration or provisioning RPC.';

create function private.collection_pilot_member()
returns boolean language sql stable security definer set search_path=''
as $$ select exists(select 1 from private.collection_pilot_members m join auth.users u on u.id=m.auth_uid
    where m.auth_uid=(select auth.uid()) and m.revoked_at is null and u.is_anonymous is false); $$;
revoke all on function private.collection_pilot_member() from public,anon,authenticated,service_role;

create function private.collection_pilot_capabilities()
returns jsonb language sql stable security definer set search_path=''
as $$ select jsonb_build_object('version','gsip-invited-pilot-v1','mode','invited_private',
    'member',private.collection_pilot_member(),
    'capture_open',public.capture_is_open(),
    'library_intake_available',coalesce((private.library_intake_capabilities()->>'available')::boolean,false),
    'publication_held',true); $$;
revoke all on function private.collection_pilot_capabilities() from public,anon,authenticated,service_role;
grant execute on function private.collection_pilot_capabilities() to anon,authenticated,service_role;
create function public.collection_pilot_capabilities()
returns jsonb language sql stable security invoker set search_path=''
return private.collection_pilot_capabilities();
revoke all on function public.collection_pilot_capabilities() from public,anon,authenticated,service_role;
grant execute on function public.collection_pilot_capabilities() to anon,authenticated,service_role;

-- Lock membership and gate rows for the lifetime of an admitted write. Revocation/closure either
-- wins first and refuses the write, or waits for that earlier admitted transaction to finish.
create function private.require_collection_pilot()
returns void language plpgsql volatile security definer set search_path=''
as $$ begin
    perform 1 from private.collection_pilot_members m join auth.users u on u.id=m.auth_uid
      where m.auth_uid=(select auth.uid()) and m.revoked_at is null and u.is_anonymous is false
      for share of m;
    if not found then raise exception 'collection authorization refused' using errcode='42501'; end if;
    perform 1 from public.service_state where singleton and capture_open for share;
    if not found then raise exception 'collection intake unavailable' using errcode='LI001'; end if;
    perform 1 from private.library_service_state where singleton and intake_open for share;
    if not found then raise exception 'collection intake unavailable' using errcode='LI001'; end if;
end; $$;
revoke all on function private.require_collection_pilot() from public,anon,authenticated,service_role;

-- RLS restricts all existing permissive client-write predicates without replacing them. No
-- select/delete/rights policy is gated on an invitation. Incoming-object UPDATE is covered too.
do $$ declare t text; begin
    foreach t in array array['contributors','contribution_grants','submissions','photos'] loop
        execute format('create policy %I on public.%I as restrictive for insert to authenticated with check
          (public.collection_pilot_capabilities() @> ''{"member":true,"capture_open":true,"library_intake_available":true}''::jsonb)',t||'_pilot_insert',t);
        execute format('create policy %I on public.%I as restrictive for update to authenticated using
          (public.collection_pilot_capabilities() @> ''{"member":true,"capture_open":true,"library_intake_available":true}''::jsonb) with check
          (public.collection_pilot_capabilities() @> ''{"member":true,"capture_open":true,"library_intake_available":true}''::jsonb)',t||'_pilot_update',t);
    end loop;
end; $$;
create policy incoming_photos_pilot_insert on storage.objects as restrictive for insert to authenticated
with check(bucket_id<>'incoming-photos' or public.collection_pilot_capabilities() @>
    '{"member":true,"capture_open":true,"library_intake_available":true}'::jsonb);
create policy incoming_photos_pilot_update on storage.objects as restrictive for update to authenticated
using(bucket_id<>'incoming-photos' or public.collection_pilot_capabilities() @>
    '{"member":true,"capture_open":true,"library_intake_available":true}'::jsonb)
with check(bucket_id<>'incoming-photos' or public.collection_pilot_capabilities() @>
    '{"member":true,"capture_open":true,"library_intake_available":true}'::jsonb);

create function private.guard_collection_pilot_client_write()
returns trigger language plpgsql security definer set search_path=''
as $$ begin
    -- SET ROLE survives a SECURITY DEFINER call; current_user does not. Trusted worker writes
    -- remain available for QA/cleanup, but PostgREST's authenticated role must lock admission.
    if current_setting('role',true)='authenticated' then
        if tg_table_schema='storage' then
            if new.bucket_id='incoming-photos' then perform private.require_collection_pilot(); end if;
        else
            perform private.require_collection_pilot();
        end if;
    end if;
    return new;
end; $$;
revoke all on function private.guard_collection_pilot_client_write() from public,anon,authenticated,service_role;
do $$ declare t text; begin
    foreach t in array array['contributors','contribution_grants','submissions','photos'] loop
        execute format('create trigger %I before insert or update on public.%I for each row execute function private.guard_collection_pilot_client_write()',t||'_zz_pilot_admission',t);
    end loop;
end; $$;
create trigger incoming_photos_00_pilot_admission before insert or update on storage.objects
for each row execute function private.guard_collection_pilot_client_write();

alter table public.submissions add column collection_scope text not null default 'legacy'
    check(collection_scope in('legacy','private_pilot'));
alter table public.submissions alter column collection_scope set default 'private_pilot';
comment on column public.submissions.collection_scope is
    'Server-owned immutable origin. Legacy backfill grants no new eligibility; every new row is private_pilot regardless of caller/QA/optional library data.';
create function private.guard_submission_collection_scope()
returns trigger language plpgsql security invoker set search_path=''
as $$ begin
    if tg_op='INSERT' then new.collection_scope:='private_pilot';
    elsif new.collection_scope is distinct from old.collection_scope then
        raise exception 'collection scope is immutable' using errcode='23514';
    end if;
    return new;
end; $$;
revoke all on function private.guard_submission_collection_scope() from public,anon,authenticated,service_role;
create trigger submissions_00_private_scope before insert or update on public.submissions
for each row execute function private.guard_submission_collection_scope();

-- Fixed refusal: there is deliberately no mutable gate, enable operation, exemption or release token.
create function private.collection_publication_capabilities()
returns jsonb language sql immutable security invoker set search_path=''
as $$ select '{"version":"gsip-collection-publication-v1","publication_allowed":false}'::jsonb; $$;
revoke all on function private.collection_publication_capabilities() from public,anon,authenticated,service_role;
grant execute on function private.collection_publication_capabilities() to service_role;
create function public.collection_publication_capabilities()
returns jsonb language sql immutable security invoker set search_path=''
return private.collection_publication_capabilities();
revoke all on function public.collection_publication_capabilities() from public,anon,authenticated,service_role;
grant execute on function public.collection_publication_capabilities() to service_role;
create function private.reject_collection_publication()
returns trigger language plpgsql security invoker set search_path=''
as $$ begin raise exception 'collection publication is held' using errcode='CP001'; end; $$;
revoke all on function private.reject_collection_publication() from public,anon,authenticated,service_role;
create trigger h3_cells_collection_publication_held before insert or update on public.h3_cells
for each statement execute function private.reject_collection_publication();
create trigger dataset_releases_collection_publication_held before insert or update on public.dataset_releases
for each statement execute function private.reject_collection_publication();

-- Privileged finalization cannot bypass current invitation and both intake gates.
create or replace function private.finalize_submission(p_submission_id uuid)
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

    perform private.require_collection_pilot();

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

-- Withdrawal-first rules remain before admission, so revoked rights cannot be resurrected.
create or replace function private.record_library_intake(p_request jsonb)
returns jsonb language plpgsql volatile security definer set search_path = ''
as $$
declare
    normalized jsonb;
    contributor uuid;
    human_actor uuid;
    intake uuid;
    node uuid;
    sample uuid;
    submission uuid;
    original_grant uuid;
    source_photo uuid;
    source_synthetic boolean;
    existing private.library_intakes%rowtype;
    original_sample private.library_samples%rowtype;
    v_declaration jsonb;
    source_digest text;
    used smallint;
begin
    if auth.uid() is null or not exists (select 1 from auth.users u where u.id = auth.uid()) then
        raise exception 'library authorization refused' using errcode = '42501';
    end if;
    select c.id into contributor from public.contributors c
    where c.auth_uid = auth.uid() for update;
    if contributor is null then
        raise exception 'library authorization refused' using errcode = '42501';
    end if;
    select a.id into human_actor from public.actors a
    where a.contributor_id = contributor and a.kind = 'human' and a.status = 'active';
    if human_actor is null then
        raise exception 'library authorization refused' using errcode = '42501';
    end if;
    normalized := private.validate_library_request(p_request);
    intake := (normalized ->> 'intake_id')::uuid;
    node := (normalized ->> 'node_id')::uuid;
    sample := (normalized ->> 'sample_id')::uuid;
    submission := (normalized ->> 'submission_id')::uuid;
    select s.grant_id, s.is_synthetic, p.id into original_grant, source_synthetic, source_photo
    from public.submissions s
    join public.photos p on p.submission_id = s.id and p.shot_type = 'B'
    where s.id = submission and s.contributor_id = contributor and s.finalized_at is not null
      and p.storage_path ~ ('^' || auth.uid()::text || '/' || submission::text || '/B/'
          || '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jpg$');
    if original_grant is null then
        raise exception 'library authorization refused' using errcode = '42501';
    end if;
    if exists (select 1 from public.grant_withdrawals w where w.grant_id = original_grant)
       or exists (select 1 from public.deletion_requests r where r.contributor_id = contributor
           and (r.kind = 'delete_account' or r.requested_at >=
               (select g.accepted_at from public.contribution_grants g where g.id = original_grant)))
       or exists (select 1 from private.library_sample_tombstones t where t.node_id = node and t.sample_id = sample)
    then
        raise exception 'library contribution withdrawn' using errcode = 'WD001';
    end if;
    if not exists (
        select 1 from public.contribution_grants g join public.terms_versions t on t.version = g.terms_version
        where g.id = original_grant and g.contributor_id = contributor
          and g.data_license = 'ODbL-1.0' and g.photo_license = 'CC-BY-SA-4.0' and g.accepted_at <= now()
          and t.published_at <= g.accepted_at and (t.retired_at is null or t.retired_at > g.accepted_at)
    ) then
        raise exception 'library authorization refused' using errcode = '42501';
    end if;
    perform private.require_collection_pilot();
    if not (private.library_intake_capabilities() ->> 'available')::boolean then
        raise exception 'library intake unavailable' using errcode = 'LI001';
    end if;
    select * into existing from private.library_intakes i where i.intake_id = intake;
    if found then
        if existing.payload = normalized
           and exists (select 1 from private.library_samples s where s.node_id = existing.node_id
                       and s.sample_id = existing.sample_id and s.contributor_id = contributor) then
            return jsonb_build_object('intake_id', intake, 'status', 'already_stored');
        end if;
        raise exception 'library identity or context conflict' using errcode = 'LI002';
    end if;
    if exists (select 1 from private.library_retired_declaration_ids r where r.identity_kind = 'intake' and r.identity_id = intake)
       or exists (select 1 from private.library_retired_nodes n where n.node_id = node)
       or exists (select 1 from private.library_nodes n where n.node_id = node and n.contributor_id <> contributor)
       or exists (select 1 from private.library_intakes i where i.submission_id = submission or i.source_photo_id = source_photo)
    then
        raise exception 'library identity or context conflict' using errcode = 'LI002';
    end if;
    select * into original_sample from private.library_samples s where s.node_id = node and s.sample_id = sample;
    if found and (original_sample.contributor_id <> contributor or original_sample.grant_id <> original_grant
        or original_sample.protocol_version <> normalized ->> 'protocol_version'
        or original_sample.context <> normalized -> 'context') then
        raise exception 'library identity or context conflict' using errcode = 'LI002';
    end if;
    v_declaration := normalized -> 'instrument_declaration';
    if v_declaration <> 'null'::jsonb then
        source_digest := v_declaration -> 'measurement' ->> 'source_sha256';
        if exists (select 1 from private.library_retired_declaration_ids r where r.identity_kind = 'measurement'
                      and r.identity_id = (v_declaration ->> 'measurement_id')::uuid)
           or exists (select 1 from private.library_instrument_declarations d
                   where d.measurement_id = (v_declaration ->> 'measurement_id')::uuid)
           or exists (select 1 from private.library_instrument_declarations d
                      where d.contributor_id = contributor and d.source_sha256 = source_digest
                        and (d.node_id <> node or d.sample_id <> sample)) then
            raise exception 'library identity or context conflict' using errcode = 'LI002';
        end if;
    end if;
    select q.intakes into used from private.library_intake_daily_usage q
    where q.contributor_id = contributor and q.utc_day = (now() at time zone 'UTC')::date;
    if used >= 100 then
        raise exception 'library daily intake quota reached' using errcode = 'LI003';
    end if;
    insert into private.library_nodes (node_id, contributor_id) values (node, contributor) on conflict (node_id) do nothing;
    insert into private.library_samples (node_id, sample_id, contributor_id, grant_id, protocol_version, context)
    values (node, sample, contributor, original_grant, normalized ->> 'protocol_version', normalized -> 'context')
    on conflict (node_id, sample_id) do nothing;
    insert into private.library_sample_restrictions (node_id, sample_id, synthetic, holdout)
    values (node, sample, source_synthetic, exists (select 1 from public.gold_labels g where g.submission_id = submission and g.holdout))
    on conflict (node_id, sample_id) do update set
        synthetic = private.library_sample_restrictions.synthetic or excluded.synthetic,
        holdout = private.library_sample_restrictions.holdout or excluded.holdout;
    insert into private.library_intakes (intake_id, node_id, sample_id, submission_id, source_photo_id,
        actor_id, payload, payload_text, payload_sha256)
    values (intake, node, sample, submission, source_photo, human_actor, normalized, normalized::text,
        encode(extensions.digest(convert_to(normalized::text, 'UTF8'), 'sha256'), 'hex'));
    if v_declaration <> 'null'::jsonb then
        insert into private.library_instrument_declarations (measurement_id, intake_id, contributor_id,
            node_id, sample_id, source_sha256, declaration)
        values ((v_declaration ->> 'measurement_id')::uuid, intake, contributor, node, sample, source_digest, v_declaration);
    end if;
    insert into private.library_intake_daily_usage (contributor_id, utc_day, intakes)
    values (contributor, (now() at time zone 'UTC')::date, 1)
    on conflict (contributor_id, utc_day) do update set intakes = private.library_intake_daily_usage.intakes + 1;
    return jsonb_build_object('intake_id', intake, 'status', 'stored_private_unverified');
exception when foreign_key_violation then
    -- A concurrent administrative source deletion can win after the owned read.
    raise exception 'library authorization refused' using errcode = '42501';
when unique_violation then
    -- Different contributors cannot take a global UUID through simultaneous writes.
    raise exception 'library identity or context conflict' using errcode = 'LI002';
end;
$$;

-- Keep malformed/k-anonymity validation; even valid or empty aggregate-only refresh is held.
create or replace function public.refresh_public_h3_cells(payload jsonb)
returns integer
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
    refreshed integer;
    violations integer;
begin
    if jsonb_typeof(payload) is distinct from 'array' then
        raise exception 'payload must be a JSON array' using errcode = '22023';
    end if;

    select count(*) into violations
    from jsonb_to_recordset(payload) as item (
        h3_index text,
        resolution integer,
        n_submissions integer,
        n_contributors integer,
        latest_submission_date date
    )
    where item.resolution is null
       or item.resolution not in (4, 6, 8)
       or item.h3_index is null
       or item.h3_index !~ ('^8' || to_hex(item.resolution) || '[0-9a-f]{13}$')
       or item.n_contributors is null
       or item.n_contributors < 3
       or item.n_submissions is null
       or item.n_submissions < item.n_contributors;

    if violations > 0 then
        raise exception 'payload contains % cell(s) that are malformed or not k-anonymous', violations
            using errcode = '22023';
    end if;

    raise exception 'collection publication is held' using errcode='CP001';

    delete from public.h3_cells where true;
    insert into public.h3_cells (
        h3_index,
        resolution,
        n_submissions,
        n_contributors,
        latest_submission_date,
        updated_at
    )
    select
        item.h3_index,
        item.resolution::smallint,
        item.n_submissions,
        item.n_contributors,
        item.latest_submission_date,
        now()
    from jsonb_to_recordset(payload) as item (
        h3_index text,
        resolution integer,
        n_submissions integer,
        n_contributors integer,
        latest_submission_date date
    );

    get diagnostics refreshed = row_count;
    return refreshed;
end;
$$;

