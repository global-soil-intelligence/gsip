-- WP-LIB-4B: private declaration intake only. No physical verification, training or activation.
-- Private data never enters the public schema; caller entry points are bound invoker wrappers.

create function private.library_uuid_text(p_value jsonb)
returns boolean language sql immutable security invoker set search_path = ''
as $$ select coalesce(jsonb_typeof(p_value) = 'string' and
    (p_value #>> '{}') ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', false); $$;
revoke all on function private.library_uuid_text(jsonb) from public, anon, authenticated, service_role;

create function private.validate_library_request(p_request jsonb)
returns jsonb language plpgsql immutable security invoker set search_path = ''
as $$
declare
    ctx jsonb;
    declaration jsonb;
    measurement jsonb;
    bands integer;
    previous_band numeric;
    band numeric;
    i integer;
    key text;
    normalized jsonb := p_request;
begin
    if p_request is null or jsonb_typeof(p_request) <> 'object'
       or octet_length(convert_to(p_request::text, 'UTF8')) > 2000000
       or p_request - array['schema_version', 'intake_id', 'node_id', 'sample_id',
           'submission_id', 'protocol_version', 'context', 'instrument_declaration']::text[] <> '{}'::jsonb
       or not (p_request ?& array['schema_version', 'intake_id', 'node_id', 'sample_id',
           'submission_id', 'protocol_version', 'context', 'instrument_declaration'])
       or p_request ->> 'schema_version' is distinct from 'gsip-library-intake-v1'
       or p_request ->> 'protocol_version' is distinct from 'gsip-capture-v1'
    then
        raise exception 'invalid library request' using errcode = '22023';
    end if;
    foreach key in array array['intake_id', 'node_id', 'sample_id', 'submission_id'] loop
        if not private.library_uuid_text(p_request -> key) then
            raise exception 'invalid library request' using errcode = '22023';
        end if;
        normalized := jsonb_set(normalized, array[key], to_jsonb((p_request ->> key)::uuid::text));
    end loop;
    ctx := p_request -> 'context';
    if jsonb_typeof(ctx) <> 'object'
       or ctx - array['depth_top_cm', 'depth_bottom_cm', 'condition']::text[] <> '{}'::jsonb
       or not (ctx ?& array['depth_top_cm', 'depth_bottom_cm', 'condition'])
       or jsonb_typeof(ctx -> 'depth_top_cm') <> 'number'
       or jsonb_typeof(ctx -> 'depth_bottom_cm') <> 'number'
       or jsonb_typeof(ctx -> 'condition') <> 'string'
       or ctx ->> 'condition' not in ('dry', 'moist', 'wet', 'unknown')
    then
        raise exception 'invalid library request' using errcode = '22023';
    end if;
    if (ctx ->> 'depth_top_cm')::numeric < 0
       or (ctx ->> 'depth_bottom_cm')::numeric > 200
       or (ctx ->> 'depth_top_cm')::numeric >= (ctx ->> 'depth_bottom_cm')::numeric
    then
        raise exception 'invalid library request' using errcode = '22023';
    end if;
    declaration := p_request -> 'instrument_declaration';
    if declaration = 'null'::jsonb then return normalized; end if;
    if jsonb_typeof(declaration) <> 'object'
       or declaration - array['measurement_id', 'measurement']::text[] <> '{}'::jsonb
       or not (declaration ?& array['measurement_id', 'measurement'])
       or not private.library_uuid_text(declaration -> 'measurement_id')
    then
        raise exception 'invalid library request' using errcode = '22023';
    end if;
    normalized := jsonb_set(normalized, '{instrument_declaration,measurement_id}',
        to_jsonb((declaration ->> 'measurement_id')::uuid::text));
    measurement := declaration -> 'measurement';
    if jsonb_typeof(measurement) <> 'object'
       or measurement - array['kind', 'source_sha256', 'instrument_id', 'calibration_id',
           'wavelength_nm', 'reflectance', 'uncertainty']::text[] <> '{}'::jsonb
       or not (measurement ?& array['kind', 'source_sha256', 'instrument_id', 'calibration_id',
           'wavelength_nm', 'reflectance', 'uncertainty'])
       or measurement ->> 'kind' is distinct from 'instrument_reflectance'
       or jsonb_typeof(measurement -> 'source_sha256') <> 'string'
       or measurement ->> 'source_sha256' !~ '^[0-9a-f]{64}$'
       or not private.library_uuid_text(measurement -> 'instrument_id')
       or not private.library_uuid_text(measurement -> 'calibration_id')
       or jsonb_typeof(measurement -> 'wavelength_nm') <> 'array'
       or jsonb_typeof(measurement -> 'reflectance') <> 'array'
       or jsonb_typeof(measurement -> 'uncertainty') <> 'array'
    then
        raise exception 'invalid library request' using errcode = '22023';
    end if;
    foreach key in array array['instrument_id', 'calibration_id'] loop
        normalized := jsonb_set(normalized, array['instrument_declaration', 'measurement', key],
            to_jsonb((measurement ->> key)::uuid::text));
    end loop;
    bands := jsonb_array_length(measurement -> 'wavelength_nm');
    if bands < 3 or bands > 10000
       or jsonb_array_length(measurement -> 'reflectance') <> bands
       or jsonb_array_length(measurement -> 'uncertainty') <> bands
    then
        raise exception 'invalid library request' using errcode = '22023';
    end if;
    for i in 0..bands - 1 loop
        if jsonb_typeof(measurement -> 'wavelength_nm' -> i) <> 'number'
           or jsonb_typeof(measurement -> 'reflectance' -> i) <> 'number'
           or jsonb_typeof(measurement -> 'uncertainty' -> i) <> 'number'
        then
            raise exception 'invalid library request' using errcode = '22023';
        end if;
        band := (measurement -> 'wavelength_nm' ->> i)::numeric;
        if band < 200 or band > 25000 or (previous_band is not null and band <= previous_band)
           or (measurement -> 'reflectance' ->> i)::numeric not between 0 and 1
           or (measurement -> 'uncertainty' ->> i)::numeric not between 0 and 1
        then
            raise exception 'invalid library request' using errcode = '22023';
        end if;
        previous_band := band;
    end loop;
    return normalized;
end;
$$;
revoke all on function private.validate_library_request(jsonb) from public, anon, authenticated, service_role;

create table private.library_service_state (
    singleton boolean primary key default true check (singleton),
    intake_open boolean not null default false
);
insert into private.library_service_state (singleton) values (true);

create table private.library_nodes (
    node_id uuid primary key,
    contributor_id uuid not null references public.contributors (id),
    created_at timestamptz not null default now(),
    unique (node_id, contributor_id)
);
-- Account deletion keeps only an opaque UUID to prevent namespace reassignment.
create table private.library_retired_nodes (
    node_id uuid primary key
);
create table private.library_retired_declaration_ids (
    identity_kind text not null check (identity_kind in ('intake', 'measurement')),
    identity_id uuid not null,
    primary key (identity_kind, identity_id)
);
create table private.library_samples (
    node_id uuid not null,
    sample_id uuid not null,
    contributor_id uuid not null,
    grant_id uuid not null,
    protocol_version text not null check (protocol_version = 'gsip-capture-v1'),
    context jsonb not null,
    created_at timestamptz not null default now(),
    primary key (node_id, sample_id),
    foreign key (node_id, contributor_id) references private.library_nodes (node_id, contributor_id),
    foreign key (grant_id, contributor_id) references public.contribution_grants (id, contributor_id)
);
create table private.library_intakes (
    intake_id uuid primary key,
    node_id uuid not null,
    sample_id uuid not null,
    submission_id uuid not null unique references public.submissions (id) on delete cascade,
    source_photo_id uuid not null unique references public.photos (id) on delete cascade,
    actor_id uuid not null references public.actors (id),
    payload jsonb not null,
    payload_text text not null,
    payload_sha256 text not null check (payload_sha256 ~ '^[0-9a-f]{64}$'),
    created_at timestamptz not null default now(),
    foreign key (node_id, sample_id) references private.library_samples (node_id, sample_id) on delete cascade,
    check (payload_text = payload::text),
    check (octet_length(convert_to(payload_text, 'UTF8')) <= 2000000),
    check (payload_sha256 = encode(extensions.digest(convert_to(payload_text, 'UTF8'), 'sha256'), 'hex'))
);
create table private.library_instrument_declarations (
    measurement_id uuid primary key,
    intake_id uuid not null unique references private.library_intakes (intake_id) on delete cascade,
    contributor_id uuid not null references public.contributors (id),
    node_id uuid not null,
    sample_id uuid not null,
    source_sha256 text not null check (source_sha256 ~ '^[0-9a-f]{64}$'),
    declaration jsonb not null,
    source_verified boolean not null default false check (not source_verified),
    calibration_verified boolean not null default false check (not calibration_verified),
    pairing_verified boolean not null default false check (not pairing_verified),
    foreign key (node_id, sample_id) references private.library_samples (node_id, sample_id) on delete cascade
);
create index library_declarations_owner_source_idx
    on private.library_instrument_declarations (contributor_id, source_sha256);
create table private.library_sample_restrictions (
    node_id uuid not null,
    sample_id uuid not null,
    synthetic boolean not null default false,
    holdout boolean not null default false,
    primary key (node_id, sample_id),
    foreign key (node_id, sample_id) references private.library_samples (node_id, sample_id) on delete cascade
);
create table private.library_sample_tombstones (
    node_id uuid not null,
    sample_id uuid not null,
    grant_id uuid not null references public.contribution_grants (id),
    reason text not null check (reason in ('withdrawn', 'account_deletion', 'source_deleted')),
    withdrawn_at timestamptz not null default now(),
    primary key (node_id, sample_id)
);
create table private.library_intake_daily_usage (
    contributor_id uuid not null references public.contributors (id),
    utc_day date not null,
    intakes smallint not null check (intakes between 1 and 100),
    primary key (contributor_id, utc_day)
);

-- Deny explicitly even if a future permissive policy or client grant is accidentally added.
do $$
declare tbl text;
begin
    foreach tbl in array array['library_service_state', 'library_nodes', 'library_samples',
        'library_intakes', 'library_instrument_declarations', 'library_sample_restrictions',
        'library_sample_tombstones', 'library_intake_daily_usage', 'library_retired_nodes', 'library_retired_declaration_ids'] loop
        execute format('alter table private.%I enable row level security', tbl);
        execute format('revoke all on private.%I from public, anon, authenticated, service_role', tbl);
        execute format('create policy %I on private.%I as restrictive for all to public using (false) with check (false)',
            tbl || '_deny_client', tbl);
    end loop;
end;
$$;

create function private.guard_library_immutable()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
    if tg_op = 'UPDATE' then
        raise exception 'library identity and payload are immutable' using errcode = 'LI002';
    end if;
    if tg_table_name = 'library_nodes' then
        if not exists (select 1 from private.library_retired_nodes n where n.node_id = old.node_id)
           or exists (select 1 from private.library_samples s where s.node_id = old.node_id) then
            raise exception 'library payload remains' using errcode = '55000';
        end if;
    elsif not exists (
        select 1 from private.library_sample_tombstones t
        where t.node_id = old.node_id and t.sample_id = old.sample_id
    ) then
        raise exception 'library deletion requires a tombstone' using errcode = '55000';
    end if;
    if tg_table_name = 'library_intakes' then
        insert into private.library_retired_declaration_ids (identity_kind, identity_id)
        values ('intake', old.intake_id) on conflict do nothing;
    elsif tg_table_name = 'library_instrument_declarations' then
        insert into private.library_retired_declaration_ids (identity_kind, identity_id)
        values ('measurement', old.measurement_id) on conflict do nothing;
    end if;
    return old;
end;
$$;
revoke all on function private.guard_library_immutable() from public, anon, authenticated, service_role;
create trigger library_nodes_immutable before update or delete on private.library_nodes
    for each row execute function private.guard_library_immutable();
create trigger library_samples_immutable before update or delete on private.library_samples
    for each row execute function private.guard_library_immutable();
create trigger library_intakes_immutable before update or delete on private.library_intakes
    for each row execute function private.guard_library_immutable();
create trigger library_declarations_immutable before update or delete on private.library_instrument_declarations
    for each row execute function private.guard_library_immutable();

create function private.guard_library_restrictions()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
    if tg_op = 'UPDATE' then
        if new.node_id is distinct from old.node_id or new.sample_id is distinct from old.sample_id
           or (old.holdout and not new.holdout) or (old.synthetic and not new.synthetic) then
            raise exception 'library restrictions are permanent' using errcode = '23514';
        end if;
        return new;
    end if;
    if not exists (select 1 from private.library_sample_tombstones t
                   where t.node_id = old.node_id and t.sample_id = old.sample_id) then
        raise exception 'library deletion requires a tombstone' using errcode = '55000';
    end if;
    return old;
end;
$$;
revoke all on function private.guard_library_restrictions() from public, anon, authenticated, service_role;
create trigger library_restrictions_monotonic before update or delete on private.library_sample_restrictions
    for each row execute function private.guard_library_restrictions();
create trigger library_retired_declaration_ids_append_only before update or delete on private.library_retired_declaration_ids
    for each row execute function private.reject_grant_withdrawal_mutation();
create trigger library_retired_nodes_append_only before update or delete on private.library_retired_nodes
    for each row execute function private.reject_grant_withdrawal_mutation();
create trigger library_tombstones_append_only before update or delete on private.library_sample_tombstones
    for each row execute function private.reject_grant_withdrawal_mutation();
do $$
declare tbl text;
begin
    foreach tbl in array array['library_nodes', 'library_samples', 'library_intakes',
        'library_instrument_declarations', 'library_sample_restrictions', 'library_sample_tombstones',
        'library_intake_daily_usage', 'library_retired_nodes', 'library_retired_declaration_ids'] loop
        execute format('create trigger %I before truncate on private.%I for each statement execute function private.reject_truncate()',
            tbl || '_no_truncate', tbl);
    end loop;
end;
$$;

create function private.library_intake_capabilities()
returns jsonb language sql stable security definer set search_path = ''
as $$ select jsonb_build_object('version', 'gsip-library-intake-v1', 'available',
    public.capture_is_open() and coalesce((select intake_open from private.library_service_state), false)); $$;
revoke all on function private.library_intake_capabilities() from public, anon, authenticated, service_role;
grant execute on function private.library_intake_capabilities() to anon, authenticated;
create function public.library_intake_capabilities()
returns jsonb language sql stable security invoker set search_path = ''
return private.library_intake_capabilities();
revoke all on function public.library_intake_capabilities() from public, anon, authenticated, service_role;
grant execute on function public.library_intake_capabilities() to anon, authenticated;

create function private.set_library_intake_open(p_open boolean)
returns void language sql volatile security definer set search_path = ''
as $$ update private.library_service_state set intake_open = p_open where singleton; $$;
revoke all on function private.set_library_intake_open(boolean) from public, anon, authenticated, service_role;
grant execute on function private.set_library_intake_open(boolean) to service_role;
create function public.set_library_intake_open(p_open boolean)
returns void language sql volatile security invoker set search_path = ''
return private.set_library_intake_open(p_open);
revoke all on function public.set_library_intake_open(boolean) from public, anon, authenticated, service_role;
grant execute on function public.set_library_intake_open(boolean) to service_role;

create function private.record_library_intake(p_request jsonb)
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
revoke all on function private.record_library_intake(jsonb) from public, anon, authenticated, service_role;
grant execute on function private.record_library_intake(jsonb) to authenticated;
create function public.record_library_intake(p_request jsonb)
returns jsonb language sql volatile security invoker set search_path = ''
return private.record_library_intake(p_request);
revoke all on function public.record_library_intake(jsonb) from public, anon, authenticated, service_role;
grant execute on function public.record_library_intake(jsonb) to authenticated;

create function private.my_library_intake_receipt(p_intake_id uuid)
returns jsonb language plpgsql stable security definer set search_path = ''
as $$
begin
    if auth.uid() is null or not exists (select 1 from auth.users u where u.id = auth.uid()) then
        raise exception 'library authorization refused' using errcode = '42501';
    end if;
    if not exists (
        select 1 from private.library_intakes i
        join private.library_samples s on s.node_id = i.node_id and s.sample_id = i.sample_id
        join public.contributors c on c.id = s.contributor_id
        join public.actors a on a.contributor_id = c.id and a.kind = 'human' and a.status = 'active'
        where i.intake_id = p_intake_id and c.auth_uid = auth.uid()
          and not exists (select 1 from public.grant_withdrawals w where w.grant_id = s.grant_id)
    ) then
        raise exception 'library authorization refused' using errcode = '42501';
    end if;
    return jsonb_build_object('intake_id', p_intake_id, 'status', 'already_stored');
end;
$$;
revoke all on function private.my_library_intake_receipt(uuid) from public, anon, authenticated, service_role;
grant execute on function private.my_library_intake_receipt(uuid) to authenticated;
create function public.my_library_intake_receipt(p_intake_id uuid)
returns jsonb language sql stable security invoker set search_path = ''
return private.my_library_intake_receipt(p_intake_id);
revoke all on function public.my_library_intake_receipt(uuid) from public, anon, authenticated, service_role;
grant execute on function public.my_library_intake_receipt(uuid) to authenticated;

-- Both request filing and direct service withdrawal take the same contributor lock as intake.
create function private.lock_library_rights_contributor()
returns trigger language plpgsql security definer set search_path = ''
as $$
declare owner_id uuid;
begin
    if tg_table_name = 'deletion_requests' then owner_id := new.contributor_id;
    else select g.contributor_id into owner_id from public.contribution_grants g where g.id = new.grant_id;
    end if;
    perform 1 from public.contributors c where c.id = owner_id for update;
    return new;
end;
$$;
revoke all on function private.lock_library_rights_contributor() from public, anon, authenticated, service_role;
create trigger deletion_requests_00_library_lock before insert on public.deletion_requests
    for each row execute function private.lock_library_rights_contributor();
create trigger grant_withdrawals_00_library_lock before insert on public.grant_withdrawals
    for each row execute function private.lock_library_rights_contributor();

create function private.erase_library_grant(p_grant uuid, p_reason text)
returns void language plpgsql volatile security definer set search_path = ''
as $$
begin
    insert into private.library_sample_tombstones (node_id, sample_id, grant_id, reason)
    select s.node_id, s.sample_id, s.grant_id, p_reason from private.library_samples s where s.grant_id = p_grant
    on conflict (node_id, sample_id) do nothing;
    delete from private.library_samples s where s.grant_id = p_grant;
end;
$$;
revoke all on function private.erase_library_grant(uuid, text) from public, anon, authenticated, service_role;
create function private.erase_library_on_withdrawal()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
    perform private.erase_library_grant(new.grant_id,
        case when new.reason = 'account_deletion' then 'account_deletion' else 'withdrawn' end);
    return new;
end;
$$;
revoke all on function private.erase_library_on_withdrawal() from public, anon, authenticated, service_role;
create trigger grant_withdrawals_erase_library after insert on public.grant_withdrawals
    for each row execute function private.erase_library_on_withdrawal();

create function private.library_account_request_cleanup()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
    if new.kind = 'delete_account' then
        -- Runs after deletion_requests_withdraw_grants, so all sample payloads are gone first.
        insert into private.library_retired_nodes (node_id)
        select n.node_id from private.library_nodes n where n.contributor_id = new.contributor_id
        on conflict do nothing;
        delete from private.library_nodes n where n.contributor_id = new.contributor_id;
        delete from private.library_intake_daily_usage q where q.contributor_id = new.contributor_id;
    end if;
    return new;
end;
$$;
revoke all on function private.library_account_request_cleanup() from public, anon, authenticated, service_role;
create trigger deletion_requests_z_library_cleanup after insert on public.deletion_requests
    for each row execute function private.library_account_request_cleanup();

create function private.guard_library_request_completion()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
    if new.status = 'completed' and (exists (
        select 1 from private.library_samples s
        where s.contributor_id = new.contributor_id and (new.kind = 'delete_account'
            or exists (select 1 from public.grant_withdrawals w where w.grant_id = s.grant_id))
    ) or (new.kind = 'delete_account' and (
        exists (select 1 from private.library_nodes n where n.contributor_id = new.contributor_id)
        or exists (select 1 from private.library_intake_daily_usage q where q.contributor_id = new.contributor_id)
    ))) then
        raise exception 'covered library payload remains' using errcode = '55000';
    end if;
    return new;
end;
$$;
revoke all on function private.guard_library_request_completion() from public, anon, authenticated, service_role;
create trigger deletion_requests_library_completion_guard before insert or update of status on public.deletion_requests
    for each row execute function private.guard_library_request_completion();

-- Preserve refusal records before a source deletion can cascade a payload away.
create function private.tombstone_library_source()
returns trigger language plpgsql security definer set search_path = ''
as $$
declare item record;
begin
    -- Rights workflows already hold contributor first. A direct source DELETE has
    -- acquired its source row before this trigger, so taking contributor here
    -- would invert intake's contributor -> source-FK lock order. Source row/FK
    -- locking itself serializes this erasure with a concurrent intake insert.
    for item in select distinct s.node_id, s.sample_id, s.grant_id
        from private.library_samples s join private.library_intakes i
            on i.node_id = s.node_id and i.sample_id = s.sample_id
        where (tg_table_name = 'submissions' and i.submission_id = old.id)
           or (tg_table_name = 'photos' and i.source_photo_id = old.id)
    loop
        insert into private.library_sample_tombstones (node_id, sample_id, grant_id, reason)
        values (item.node_id, item.sample_id, item.grant_id, 'source_deleted') on conflict do nothing;
        delete from private.library_samples s where s.node_id = item.node_id and s.sample_id = item.sample_id;
    end loop;
    return old;
end;
$$;
revoke all on function private.tombstone_library_source() from public, anon, authenticated, service_role;
create trigger submissions_tombstone_library before delete on public.submissions
    for each row execute function private.tombstone_library_source();
create trigger photos_tombstone_library before delete on public.photos
    for each row execute function private.tombstone_library_source();

-- Restrictions can only grow; public source flags never leak through the safe receipt.
create function private.propagate_library_source_restriction()
returns trigger language plpgsql security definer set search_path = ''
as $$
declare source_submission uuid;
    owner_id uuid;
begin
    if tg_table_name = 'gold_labels' then source_submission := new.submission_id;
    else source_submission := new.id;
    end if;
    select s.contributor_id into owner_id from public.submissions s where s.id = source_submission;
    perform 1 from public.contributors c where c.id = owner_id for update;
    if tg_table_name = 'gold_labels' then
        if new.holdout then
            update private.library_sample_restrictions r set holdout = true
            where exists (select 1 from private.library_intakes i where i.node_id = r.node_id
                and i.sample_id = r.sample_id and i.submission_id = source_submission);
        end if;
    elsif new.is_synthetic then
        update private.library_sample_restrictions r set synthetic = true
        where exists (select 1 from private.library_intakes i where i.node_id = r.node_id
            and i.sample_id = r.sample_id and i.submission_id = source_submission);
    end if;
    return new;
end;
$$;
revoke all on function private.propagate_library_source_restriction() from public, anon, authenticated, service_role;
create trigger gold_labels_library_holdout after insert or update of holdout, submission_id on public.gold_labels
    for each row execute function private.propagate_library_source_restriction();
create trigger submissions_library_synthetic after update of is_synthetic on public.submissions
    for each row execute function private.propagate_library_source_restriction();

comment on table private.library_intakes is
    'Owner-private immutable declarations. Server payload digests are not proof of absent instrument source bytes or physical pairing. No scientific eligibility.';
comment on table private.library_instrument_declarations is
    'All origin, calibration and pairing flags are permanently false in version one. No original files or lab labels.';
comment on table private.library_sample_tombstones is
    'Durable opaque refusal records preserved before payload deletion. No measurement, context, instrument or location content.';
comment on function public.record_library_intake(jsonb) is
    'Authenticated owner only: strict private declaration intake. Live rights are checked again on every retry. LI001 hold, LI002 conflict, LI003 quota, WD001 withdrawn.';
comment on function public.set_library_intake_open(boolean) is
    'Service-only independent library gate. Migration defaults closed; production changes require exact-target owner authorization.';
