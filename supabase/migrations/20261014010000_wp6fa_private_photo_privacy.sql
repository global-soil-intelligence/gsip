-- WP-6fA: private authority only. No detector selection, deployment or publication activation.
begin;
create table private.photo_privacy_policies (
    policy_id uuid primary key,
    screening_version text not null check (screening_version ~ '^[A-Za-z0-9._-]{1,64}$'),
    calibration_version text not null check (calibration_version ~ '^[A-Za-z0-9._-]{1,64}$'),
    detector_manifest_sha256 text not null check (detector_manifest_sha256 ~ '^[0-9a-f]{64}$'),
    calibration_manifest_sha256 text not null check (calibration_manifest_sha256 ~ '^[0-9a-f]{64}$'),
    margin_version text not null check (margin_version ~ '^[A-Za-z0-9._-]{1,64}$'),
    configuration jsonb not null check (jsonb_typeof(configuration) = 'object'
        and octet_length(convert_to(configuration::text, 'UTF8')) <= 16384),
    owner_approval_sha256 text check (owner_approval_sha256 ~ '^[0-9a-f]{64}$'),
    unique (screening_version, calibration_version)
);
create table private.photo_privacy_state (
    singleton boolean primary key default true check (singleton),
    policy_id uuid references private.photo_privacy_policies (policy_id),
    policy_revision bigint not null default 0 check (policy_revision >= 0),
    implementation_deployed boolean not null default false,
    publication_open boolean not null default false
);
insert into private.photo_privacy_state (singleton) values (true);
create table private.photo_privacy_content (
    photo_id uuid primary key references public.photos (id) on delete cascade,
    submission_id uuid not null references public.submissions (id) on delete cascade,
    contributor_id uuid not null references public.contributors (id),
    grant_id uuid not null references public.contribution_grants (id),
    content_revision bigint not null default 0 check (content_revision >= 0),
    sanitized_sha256 text check (sanitized_sha256 ~ '^[0-9a-f]{64}$'),
    byte_count integer check (byte_count between 1 and 10485760),
    sanitizer_version text check (sanitizer_version ~ '^[A-Za-z0-9._-]{1,64}$'),
    policy_id uuid references private.photo_privacy_policies (policy_id),
    policy_revision bigint,
    status text not null default 'pending' check (status in ('pending','processing','clear','review','withheld','error')),
    created_at timestamptz not null default now(),
    check ((sanitized_sha256 is null) = (byte_count is null)),
    check ((sanitized_sha256 is null) = (sanitizer_version is null)),
    check ((policy_id is null) = (policy_revision is null))
);
create index photo_privacy_content_owner_idx on private.photo_privacy_content (contributor_id, grant_id);
create table private.photo_privacy_jobs (
    photo_id uuid not null,
    contributor_id uuid not null,
    grant_id uuid not null,
    content_revision bigint not null,
    policy_id uuid not null references private.photo_privacy_policies (policy_id),
    policy_revision bigint not null,
    attempts smallint not null default 0 check (attempts between 0 and 5),
    lease_id uuid unique,
    lease_expires_at timestamptz,
    ready_at timestamptz not null default now(),
    status text not null default 'pending' check (status in ('pending','processing','completed','error','invalidated')),
    last_error text check (last_error in ('storage','decode','sanitize','unsupported','detector','timeout')),
    primary key (photo_id, content_revision, policy_id, policy_revision),
    check ((lease_id is null) = (lease_expires_at is null))
);
create index photo_privacy_jobs_queue_idx on private.photo_privacy_jobs (ready_at, photo_id);
create unique index photo_privacy_one_active_lease on private.photo_privacy_jobs (photo_id) where status = 'processing';
create table private.photo_privacy_screens (
    request_id uuid primary key,
    lease_id uuid not null unique,
    photo_id uuid not null,
    contributor_id uuid not null,
    grant_id uuid not null,
    content_revision bigint not null,
    policy_id uuid not null references private.photo_privacy_policies (policy_id),
    policy_revision bigint not null,
    sanitized_sha256 text not null check (sanitized_sha256 ~ '^[0-9a-f]{64}$'),
    screening_version text not null,
    calibration_version text not null,
    status text not null check (status in ('clear','review','error')),
    receipt jsonb not null,
    receipt_sha256 text not null check (receipt_sha256 = encode(extensions.digest(convert_to(receipt::text,'UTF8'),'sha256'),'hex')),
    completed_at timestamptz not null default now()
);
create index photo_privacy_screens_photo_idx on private.photo_privacy_screens (photo_id, content_revision, policy_revision);
create table private.photo_privacy_operators (
    operator_id uuid primary key,
    auth_uid uuid not null unique references auth.users (id) on delete cascade,
    token_sha256 text not null unique check (token_sha256 ~ '^[0-9a-f]{64}$'),
    active boolean not null default false
);
create table private.photo_privacy_reviews (
    review_id uuid primary key,
    photo_id uuid not null,
    contributor_id uuid not null,
    grant_id uuid not null,
    content_revision bigint not null,
    policy_id uuid not null references private.photo_privacy_policies (policy_id),
    policy_revision bigint not null,
    sanitized_sha256 text not null check (sanitized_sha256 ~ '^[0-9a-f]{64}$'),
    operator_id uuid not null,
    decision text not null check (decision in ('clear','withhold')),
    reason text not null check ((decision = 'clear' and reason = 'false_positive')
        or (decision = 'withhold' and reason = 'privacy_risk')),
    request jsonb not null,
    request_sha256 text not null check (request_sha256 = encode(extensions.digest(convert_to(request::text,'UTF8'),'sha256'),'hex')),
    reviewed_at timestamptz not null default now()
);
create index photo_privacy_reviews_photo_idx on private.photo_privacy_reviews (photo_id, reviewed_at);
create table private.photo_privacy_tombstones (
    identity_kind text not null check (identity_kind in ('photo','screen','review','withhold')),
    identity_id uuid not null,
    grant_id uuid not null,
    reason text not null check (reason in ('withdrawn','account_deletion','source_deleted','privacy_risk')),
    primary key (identity_kind, identity_id)
);

do $$
declare tbl text;
begin
    foreach tbl in array array['photo_privacy_policies','photo_privacy_state','photo_privacy_content',
        'photo_privacy_jobs','photo_privacy_screens','photo_privacy_operators','photo_privacy_reviews','photo_privacy_tombstones'] loop
        execute format('alter table private.%I enable row level security',tbl);
        execute format('revoke all on private.%I from public, anon, authenticated, service_role',tbl);
        execute format('create policy %I on private.%I as restrictive for all to public using (false) with check (false)',tbl||'_deny_client',tbl);
        execute format('create trigger %I before truncate on private.%I for each statement execute function private.reject_truncate()',tbl||'_no_truncate',tbl);
    end loop;
end;
$$;

create function private.guard_photo_privacy_policy()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
    if tg_op = 'DELETE' or (to_jsonb(new) - 'owner_approval_sha256') is distinct from (to_jsonb(old) - 'owner_approval_sha256')
       or old.owner_approval_sha256 is not null then
        raise exception 'photo privacy policy is immutable' using errcode='PP003';
    end if;
    return new;
end;
$$;
create trigger photo_privacy_policy_immutable before update or delete on private.photo_privacy_policies
    for each row execute function private.guard_photo_privacy_policy();
create function private.guard_photo_privacy_state()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
    if tg_op = 'DELETE' then raise exception 'photo privacy state cannot be deleted' using errcode='55000'; end if;
    if new.publication_open and (not new.implementation_deployed or not exists (
        select 1 from private.photo_privacy_policies p where p.policy_id=new.policy_id and p.owner_approval_sha256 is not null
    )) then raise exception 'photo privacy publication unavailable' using errcode='55000'; end if;
    if tg_op = 'INSERT' then new.policy_revision := 0;
    elsif (new.policy_id,new.publication_open,new.implementation_deployed) is distinct from
          (old.policy_id,old.publication_open,old.implementation_deployed) then new.policy_revision:=old.policy_revision+1;
    else new.policy_revision:=old.policy_revision;
    end if;
    return new;
end;
$$;
create trigger photo_privacy_state_owner_guard before insert or update or delete on private.photo_privacy_state
    for each row execute function private.guard_photo_privacy_state();

create function private.guard_photo_privacy_payload()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
    if tg_op='UPDATE' then raise exception 'photo privacy audit is immutable' using errcode='PP003'; end if;
    if not exists (select 1 from private.photo_privacy_tombstones t
                   where t.identity_kind='photo' and t.identity_id=old.photo_id) then
        raise exception 'photo privacy erasure requires refusal record' using errcode='55000';
    end if;
    if tg_table_name='photo_privacy_screens' then
        insert into private.photo_privacy_tombstones values ('screen',old.request_id,old.grant_id,'source_deleted') on conflict do nothing;
    elsif tg_table_name='photo_privacy_reviews' then
        insert into private.photo_privacy_tombstones values ('review',old.review_id,old.grant_id,'source_deleted') on conflict do nothing;
    end if;
    return old;
end;
$$;
create trigger photo_privacy_screens_immutable before update or delete on private.photo_privacy_screens
    for each row execute function private.guard_photo_privacy_payload();
create trigger photo_privacy_reviews_immutable before update or delete on private.photo_privacy_reviews
    for each row execute function private.guard_photo_privacy_payload();
create trigger photo_privacy_tombstones_immutable before update or delete on private.photo_privacy_tombstones
    for each row execute function private.reject_grant_withdrawal_mutation();
create function private.guard_photo_privacy_content()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
    if tg_op='DELETE' then
        if not exists (select 1 from private.photo_privacy_tombstones t where t.identity_kind='photo' and t.identity_id=old.photo_id) then
            raise exception 'photo privacy erasure requires refusal record' using errcode='55000';
        end if;
        return old;
    end if;
    if (new.photo_id,new.submission_id,new.contributor_id,new.grant_id) is distinct from
       (old.photo_id,old.submission_id,old.contributor_id,old.grant_id) or new.content_revision < old.content_revision
       or ((new.sanitized_sha256,new.byte_count,new.sanitizer_version) is distinct from
           (old.sanitized_sha256,old.byte_count,old.sanitizer_version) and new.content_revision <> old.content_revision+1)
       or (old.status='withheld' and new.status<>'withheld') then
        raise exception 'photo privacy identity or restriction is immutable' using errcode='PP003';
    end if;
    return new;
end;
$$;
create trigger photo_privacy_content_guard before update or delete on private.photo_privacy_content
    for each row execute function private.guard_photo_privacy_content();

-- Fresh rights checks after waiting require PostgreSQL READ COMMITTED snapshots.
-- Every private RPC and source admission fails closed for stronger stale snapshots.
create function private.photo_privacy_require_current_transaction()
returns void language plpgsql stable security invoker set search_path = '' as $$
begin
    if current_setting('transaction_isolation') is distinct from 'read committed' then
        raise exception 'photo privacy transaction refused' using errcode='55000';
    end if;
end;
$$;
create function private.photo_privacy_require_service()
returns void language plpgsql stable security invoker set search_path = '' as $$
begin
    if auth.role() is distinct from 'service_role' then
        raise exception 'photo privacy authorization refused' using errcode='42501';
    end if;
    perform private.photo_privacy_require_current_transaction();
end;
$$;
create function private.photo_privacy_object(p_value jsonb,p_keys text[],p_max integer default 16384)
returns void language plpgsql immutable security invoker set search_path = '' as $$
begin
    if p_value is null or jsonb_typeof(p_value)<>'object' or p_value-p_keys<>'{}'::jsonb
       or not(p_value ?& p_keys) or octet_length(convert_to(p_value::text,'UTF8'))>p_max then
        raise exception 'invalid photo privacy request' using errcode='22023';
    end if;
end;
$$;
create function private.photo_privacy_int(p_value jsonb,p_min bigint,p_max bigint)
returns bigint language plpgsql immutable security invoker set search_path = '' as $$
begin
    if p_value is null or jsonb_typeof(p_value)<>'number' or p_value::text !~ '^[0-9]+$'
       or (p_value::text)::numeric not between p_min and p_max then
        raise exception 'invalid photo privacy request' using errcode='22023';
    end if;
    return (p_value::text)::bigint;
end;
$$;
create function private.photo_privacy_uuid(p_value jsonb)
returns uuid language plpgsql immutable security invoker set search_path = '' as $$
begin
    if not private.library_uuid_text(p_value) then raise exception 'invalid photo privacy request' using errcode='22023'; end if;
    return (p_value #>> '{}')::uuid;
end;
$$;
create function private.photo_privacy_text(p_value jsonb,p_kind text)
returns text language plpgsql immutable security invoker set search_path = '' as $$
declare value text:=p_value #>> '{}';
begin
    if p_value is null or jsonb_typeof(p_value)<>'string'
       or (p_kind='sha' and value !~ '^[0-9a-f]{64}$')
       or (p_kind='version' and value !~ '^[A-Za-z0-9._-]{1,64}$') then
        raise exception 'invalid photo privacy request' using errcode='22023';
    end if;
    return value;
end;
$$;

-- Derive the contributor before locking private rows. Source SHARE locks precede
-- private content/job locks, so direct source DELETE/UPDATE cannot invert this order.
create function private.lock_photo_privacy_source(p_photo uuid,p_skip boolean default false)
returns private.photo_privacy_content language plpgsql volatile security definer set search_path = '' as $$
declare owner_id uuid; v_submission_id uuid; source record; item private.photo_privacy_content;
begin
    if exists (select 1 from private.photo_privacy_tombstones t where t.identity_kind='photo' and t.identity_id=p_photo) then
        raise exception 'photo privacy contribution withdrawn' using errcode='WD001';
    end if;
    select s.contributor_id,s.id into owner_id,v_submission_id from public.photos p join public.submissions s on s.id=p.submission_id where p.id=p_photo;
    if owner_id is null then raise exception 'photo privacy authorization refused' using errcode='42501'; end if;
    if p_skip then
        perform 1 from public.contributors c where c.id=owner_id for update skip locked;
        if not found then return null; end if;
    else perform 1 from public.contributors c where c.id=owner_id for update;
    end if;
    -- Explicit parent-before-photo order: a join's row locking order is plan dependent.
    -- Never wait on either source row: bulk source deletion can hold parents in
    -- another order, and direct photo deletion's AFTER hook updates its parent.
    -- Busy source exceptions release this helper's acquired locks and fail closed.
    perform 1 from public.submissions s where s.id=v_submission_id and s.contributor_id=owner_id for share nowait;
    if not found then raise exception 'photo privacy authorization refused' using errcode='42501'; end if;
    perform 1 from public.photos p where p.id=p_photo and p.submission_id=v_submission_id for share nowait;
    if not found then raise exception 'photo privacy authorization refused' using errcode='42501'; end if;
    select p.id,p.submission_id,p.shot_type,p.storage_path,s.contributor_id,s.grant_id,c.auth_uid,g.accepted_at
    into source from public.photos p join public.submissions s on s.id=p.submission_id
    join public.contributors c on c.id=s.contributor_id join public.contribution_grants g on g.id=s.grant_id
    where p.id=p_photo and p.submission_id=v_submission_id and s.contributor_id=owner_id;
    if not found or source.auth_uid is null
       or source.storage_path !~ ('^'||source.auth_uid::text||'/'||source.submission_id::text||'/'||source.shot_type||'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jpg$') then
        raise exception 'photo privacy authorization refused' using errcode='42501';
    end if;
    -- Auth deletion locks auth before its operator cascade. Take the live auth lock
    -- before any private content or operator row, and recheck after waiting.
    perform 1 from auth.users u where u.id=source.auth_uid for share;
    if not found then raise exception 'photo privacy authorization refused' using errcode='42501'; end if;
    if exists(select 1 from public.grant_withdrawals w where w.grant_id=source.grant_id)
       or exists(select 1 from public.deletion_requests r where r.contributor_id=owner_id
          and (r.kind='delete_account' or r.requested_at>=source.accepted_at)) then
        raise exception 'photo privacy contribution withdrawn' using errcode='WD001';
    end if;
    select * into item from private.photo_privacy_content c where c.photo_id=p_photo for update;
    if not found or (item.submission_id,item.contributor_id,item.grant_id) is distinct from
                    (source.submission_id,source.contributor_id,source.grant_id) then
        raise exception 'photo privacy authorization refused' using errcode='42501';
    end if;
    return item;
exception when lock_not_available then
    raise exception 'stale photo privacy state' using errcode='PP002';
end;
$$;

create function private.photo_privacy_capabilities()
returns jsonb language plpgsql stable security definer set search_path = '' as $$
declare state private.photo_privacy_state; policy private.photo_privacy_policies;
begin
    perform private.photo_privacy_require_service();
    select * into state from private.photo_privacy_state;
    select * into policy from private.photo_privacy_policies p where p.policy_id=state.policy_id;
    return jsonb_build_object('version','gsip-photo-privacy-v1','publication_open',
        coalesce(state.publication_open and state.implementation_deployed and policy.owner_approval_sha256 is not null,false),
        'policy_id',policy.policy_id,'policy_revision',coalesce(state.policy_revision,0),
        'screening_version',policy.screening_version,'calibration_version',policy.calibration_version);
end;
$$;

create function private.record_photo_privacy_content(p_request jsonb)
returns jsonb language plpgsql volatile security definer set search_path = '' as $$
declare photo uuid; revision bigint; digest text; bytes integer; sanitizer text; item private.photo_privacy_content;
begin
    perform private.photo_privacy_require_service();
    perform private.photo_privacy_object(p_request,array['schema_version','photo_id','expected_content_revision','sanitized_sha256','byte_count','sanitizer_version']);
    if p_request->>'schema_version' is distinct from 'gsip-photo-privacy-v1' then raise exception 'invalid photo privacy request' using errcode='22023'; end if;
    photo:=private.photo_privacy_uuid(p_request->'photo_id');
    revision:=private.photo_privacy_int(p_request->'expected_content_revision',0,9007199254740991);
    digest:=private.photo_privacy_text(p_request->'sanitized_sha256','sha');
    bytes:=private.photo_privacy_int(p_request->'byte_count',1,10485760);
    sanitizer:=private.photo_privacy_text(p_request->'sanitizer_version','version');
    item:=private.lock_photo_privacy_source(photo);
    if (item.sanitized_sha256,item.byte_count,item.sanitizer_version) is not distinct from (digest,bytes,sanitizer) then
        return jsonb_build_object('photo_id',photo,'content_revision',item.content_revision,'status','already_current');
    end if;
    if item.content_revision<>revision then raise exception 'stale photo privacy state' using errcode='PP002'; end if;
    update private.photo_privacy_jobs j set status='invalidated' where j.photo_id=photo and j.status<>'invalidated';
    update private.photo_privacy_content c set content_revision=c.content_revision+1,
        sanitized_sha256=digest,byte_count=bytes,sanitizer_version=sanitizer,policy_id=null,policy_revision=null,
        status=case when c.status='withheld' or exists(select 1 from private.photo_privacy_tombstones t where t.identity_kind='withhold' and t.identity_id=photo)
            then 'withheld' else 'pending' end where c.photo_id=photo returning * into item;
    return jsonb_build_object('photo_id',photo,'content_revision',item.content_revision,'status','registered');
end;
$$;

create function private.claim_photo_privacy_job()
returns jsonb language plpgsql volatile security definer set search_path = '' as $$
declare candidate record; item private.photo_privacy_content; state private.photo_privacy_state;
    policy private.photo_privacy_policies; job private.photo_privacy_jobs; source record; delay_seconds integer;
begin
    perform private.photo_privacy_require_service();
    select * into state from private.photo_privacy_state;
    select * into policy from private.photo_privacy_policies p where p.policy_id=state.policy_id;
    if policy.policy_id is null then return null; end if;
    for candidate in select c.photo_id from private.photo_privacy_content c
        left join private.photo_privacy_jobs j on j.photo_id=c.photo_id and j.content_revision=c.content_revision
            and j.policy_id=state.policy_id and j.policy_revision=state.policy_revision
        where c.status<>'withheld' and not exists(select 1 from private.photo_privacy_tombstones t where t.identity_kind='withhold' and t.identity_id=c.photo_id)
          and (c.policy_id is distinct from state.policy_id or c.policy_revision is distinct from state.policy_revision
            or c.status in ('pending','processing')) and (j.ready_at is null or j.ready_at<=clock_timestamp())
        order by coalesce(j.ready_at,c.created_at),c.photo_id
    loop
        begin
            item:=private.lock_photo_privacy_source(candidate.photo_id,true);
            if item.photo_id is null then continue; end if;
            select * into state from private.photo_privacy_state for share;
            select * into policy from private.photo_privacy_policies p where p.policy_id=state.policy_id;
            if policy.policy_id is null then return null; end if;
            if item.status='withheld' then continue; end if;
            update private.photo_privacy_jobs j set status='invalidated' where j.photo_id=item.photo_id and j.status='processing'
                and (j.content_revision,j.policy_id,j.policy_revision) is distinct from (item.content_revision,state.policy_id,state.policy_revision);
            insert into private.photo_privacy_jobs(photo_id,contributor_id,grant_id,content_revision,policy_id,policy_revision)
            values(item.photo_id,item.contributor_id,item.grant_id,item.content_revision,state.policy_id,state.policy_revision) on conflict do nothing;
            select * into job from private.photo_privacy_jobs j where j.photo_id=item.photo_id and j.content_revision=item.content_revision
                and j.policy_id=state.policy_id and j.policy_revision=state.policy_revision for update skip locked;
            if not found then continue; end if;
            if job.status='processing' then
                if job.lease_expires_at>clock_timestamp() then continue; end if;
                delay_seconds:=case job.attempts when 1 then 60 when 2 then 120 when 3 then 240 else 480 end;
                update private.photo_privacy_jobs j set status=case when job.attempts>=5 then 'error' else 'pending' end,
                    last_error='timeout',ready_at=clock_timestamp()+make_interval(secs=>delay_seconds)
                    where j.photo_id=job.photo_id and j.content_revision=job.content_revision and j.policy_id=job.policy_id and j.policy_revision=job.policy_revision;
                update private.photo_privacy_content c set status=case when job.attempts>=5 then 'error' else 'pending' end,
                    policy_id=state.policy_id,policy_revision=state.policy_revision where c.photo_id=item.photo_id;
                continue;
            end if;
            if job.status<>'pending' or job.attempts>=5 or job.ready_at>clock_timestamp() then continue; end if;
            update private.photo_privacy_jobs j set attempts=j.attempts+1,lease_id=gen_random_uuid(),
                lease_expires_at=clock_timestamp()+interval '300 seconds',status='processing'
                where j.photo_id=job.photo_id and j.content_revision=job.content_revision and j.policy_id=job.policy_id and j.policy_revision=job.policy_revision returning * into job;
            update private.photo_privacy_content c set policy_id=state.policy_id,policy_revision=state.policy_revision,status='processing' where c.photo_id=item.photo_id;
            select p.submission_id,p.shot_type,p.storage_path into source from public.photos p where p.id=item.photo_id;
            return jsonb_build_object('lease_id',job.lease_id,'photo_id',item.photo_id,'submission_id',source.submission_id,
                'shot_type',source.shot_type,'storage_path',source.storage_path,'content_revision',item.content_revision,
                'sanitized_sha256',item.sanitized_sha256,'byte_count',item.byte_count,'sanitizer_version',item.sanitizer_version,
                'policy_id',policy.policy_id,'policy_revision',state.policy_revision,'screening_version',policy.screening_version,
                'calibration_version',policy.calibration_version,'detector_manifest_sha256',policy.detector_manifest_sha256,
                'calibration_manifest_sha256',policy.calibration_manifest_sha256,'lease_expires_at',job.lease_expires_at,'attempt',job.attempts);
        exception when sqlstate 'WD001' or sqlstate '42501' or sqlstate 'PP002' then continue;
        end;
    end loop;
    return null;
end;
$$;

create function private.validate_photo_privacy_screen(p_receipt jsonb)
returns jsonb language plpgsql immutable security invoker set search_path = '' as $$
declare normalized jsonb:=p_receipt; category text; outcome jsonb; count bigint; evidence jsonb;
    width bigint; height bigint; excluded bigint; key text;
begin
    perform private.photo_privacy_object(p_receipt,array['schema_version','request_id','photo_id','content_revision','policy_id','policy_revision',
        'sanitized_sha256','screening_version','calibration_version','detector_manifest_sha256','calibration_manifest_sha256',
        'face','scene_text','card_exception_used','card_exclusion']);
    if p_receipt->>'schema_version' is distinct from 'gsip-photo-privacy-v1' then raise exception 'invalid photo privacy request' using errcode='22023'; end if;
    foreach key in array array['request_id','photo_id','policy_id'] loop
        normalized:=jsonb_set(normalized,array[key],to_jsonb(private.photo_privacy_uuid(p_receipt->key)::text));
    end loop;
    perform private.photo_privacy_int(p_receipt->'content_revision',0,9007199254740991);
    perform private.photo_privacy_int(p_receipt->'policy_revision',0,9007199254740991);
    foreach key in array array['sanitized_sha256','detector_manifest_sha256','calibration_manifest_sha256'] loop
        perform private.photo_privacy_text(p_receipt->key,'sha');
    end loop;
    foreach key in array array['screening_version','calibration_version'] loop
        perform private.photo_privacy_text(p_receipt->key,'version');
    end loop;
    foreach category in array array['face','scene_text'] loop
        outcome:=p_receipt->category;
        perform private.photo_privacy_object(outcome,array['result','candidates']);
        if jsonb_typeof(outcome->'result')<>'string' or outcome->>'result' not in ('pass','flag','unsupported','error') then
            raise exception 'invalid photo privacy request' using errcode='22023';
        end if;
        count:=private.photo_privacy_int(outcome->'candidates',0,10000);
        if (outcome->>'result'='pass' and count<>0) or (outcome->>'result'='flag' and count=0) then
            raise exception 'invalid photo privacy request' using errcode='22023';
        end if;
    end loop;
    if jsonb_typeof(p_receipt->'card_exception_used')<>'boolean' then raise exception 'invalid photo privacy request' using errcode='22023'; end if;
    evidence:=p_receipt->'card_exclusion';
    if not(p_receipt->>'card_exception_used')::boolean then
        if evidence<>'null'::jsonb then raise exception 'invalid photo privacy request' using errcode='22023'; end if;
    else
        perform private.photo_privacy_object(evidence,array['image_width','image_height','mask_sha256','excluded_pixels','margin_version']);
        width:=private.photo_privacy_int(evidence->'image_width',1,40000000);
        height:=private.photo_privacy_int(evidence->'image_height',1,40000000);
        excluded:=private.photo_privacy_int(evidence->'excluded_pixels',1,40000000);
        if width*height>40000000 or excluded>=width*height then raise exception 'invalid photo privacy request' using errcode='22023'; end if;
        perform private.photo_privacy_text(evidence->'mask_sha256','sha');
        perform private.photo_privacy_text(evidence->'margin_version','version');
    end if;
    return normalized;
end;
$$;

create function private.complete_photo_privacy_job(p_lease_id uuid,p_receipt jsonb)
returns jsonb language plpgsql volatile security definer set search_path = '' as $$
declare request jsonb; item private.photo_privacy_content; job private.photo_privacy_jobs;
    state private.photo_privacy_state; policy private.photo_privacy_policies; prior private.photo_privacy_screens;
    result text; v_request_id uuid;
begin
    perform private.photo_privacy_require_service();
    request:=private.validate_photo_privacy_screen(p_receipt);
    v_request_id:=(request->>'request_id')::uuid;
    select * into job from private.photo_privacy_jobs j where j.lease_id=p_lease_id;
    if not found then raise exception 'stale photo privacy state' using errcode='PP002'; end if;
    item:=private.lock_photo_privacy_source(job.photo_id);
    select * into state from private.photo_privacy_state for share;
    select * into policy from private.photo_privacy_policies p where p.policy_id=state.policy_id;
    select * into job from private.photo_privacy_jobs j where j.lease_id=p_lease_id for update;
    if item.status='withheld' or item.sanitized_sha256 is null
       or (job.photo_id,job.content_revision,job.policy_id,job.policy_revision) is distinct from
          (item.photo_id,item.content_revision,state.policy_id,state.policy_revision)
       or (request->>'photo_id')::uuid<>item.photo_id
       or (request->>'content_revision')::bigint<>item.content_revision
       or (request->>'policy_id')::uuid is distinct from state.policy_id
       or (request->>'policy_revision')::bigint<>state.policy_revision
       or request->>'sanitized_sha256' is distinct from item.sanitized_sha256
       or request->>'screening_version' is distinct from policy.screening_version
       or request->>'calibration_version' is distinct from policy.calibration_version
       or request->>'detector_manifest_sha256' is distinct from policy.detector_manifest_sha256
       or request->>'calibration_manifest_sha256' is distinct from policy.calibration_manifest_sha256
       or ((request->>'card_exception_used')::boolean and request->'card_exclusion'->>'margin_version' is distinct from policy.margin_version) then
        raise exception 'stale photo privacy state' using errcode='PP002';
    end if;
    select * into prior from private.photo_privacy_screens s where s.lease_id=p_lease_id;
    if found then
        if prior.receipt=request then return jsonb_build_object('photo_id',item.photo_id,'content_revision',item.content_revision,'status',prior.status); end if;
        raise exception 'photo privacy receipt conflict' using errcode='PP003';
    end if;
    if exists(select 1 from private.photo_privacy_screens s where s.request_id=v_request_id)
       or exists(select 1 from private.photo_privacy_tombstones t where t.identity_kind='screen' and t.identity_id=v_request_id) then
        raise exception 'photo privacy receipt conflict' using errcode='PP003';
    end if;
    if job.status<>'processing' or job.lease_expires_at<=clock_timestamp() then
        raise exception 'stale photo privacy state' using errcode='PP002';
    end if;
    result:=case when request->'face'->>'result' in ('unsupported','error') or request->'scene_text'->>'result' in ('unsupported','error') then 'error'
        when request->'face'->>'result'='flag' or request->'scene_text'->>'result'='flag' then 'review' else 'clear' end;
    insert into private.photo_privacy_screens(request_id,lease_id,photo_id,contributor_id,grant_id,content_revision,policy_id,policy_revision,
        sanitized_sha256,screening_version,calibration_version,status,receipt,receipt_sha256)
    values(v_request_id,p_lease_id,item.photo_id,item.contributor_id,item.grant_id,item.content_revision,state.policy_id,state.policy_revision,
        item.sanitized_sha256,policy.screening_version,policy.calibration_version,result,request,
        encode(extensions.digest(convert_to(request::text,'UTF8'),'sha256'),'hex'));
    update private.photo_privacy_jobs j set status=case when result='error' then 'error' else 'completed' end where j.lease_id=p_lease_id;
    update private.photo_privacy_content c set status=result,policy_id=state.policy_id,policy_revision=state.policy_revision where c.photo_id=item.photo_id;
    return jsonb_build_object('photo_id',item.photo_id,'content_revision',item.content_revision,'status',result);
exception when unique_violation then raise exception 'photo privacy receipt conflict' using errcode='PP003';
end;
$$;

create function private.fail_photo_privacy_job(p_lease_id uuid,p_error_code text)
returns jsonb language plpgsql volatile security definer set search_path = '' as $$
declare item private.photo_privacy_content; job private.photo_privacy_jobs; state private.photo_privacy_state;
    result text; delay_seconds integer;
begin
    perform private.photo_privacy_require_service();
    if p_error_code is null or p_error_code not in ('storage','decode','sanitize','unsupported','detector','timeout') then
        raise exception 'invalid photo privacy request' using errcode='22023';
    end if;
    select * into job from private.photo_privacy_jobs j where j.lease_id=p_lease_id;
    if not found then raise exception 'stale photo privacy state' using errcode='PP002'; end if;
    item:=private.lock_photo_privacy_source(job.photo_id);
    select * into state from private.photo_privacy_state for share;
    select * into job from private.photo_privacy_jobs j where j.lease_id=p_lease_id for update;
    if item.status='withheld' or job.status<>'processing' or job.lease_expires_at<=clock_timestamp()
       or (job.content_revision,job.policy_id,job.policy_revision) is distinct from
          (item.content_revision,state.policy_id,state.policy_revision) then
        raise exception 'stale photo privacy state' using errcode='PP002';
    end if;
    result:=case when job.attempts>=5 or p_error_code in ('decode','sanitize','unsupported') then 'error' else 'pending' end;
    delay_seconds:=case job.attempts when 1 then 60 when 2 then 120 when 3 then 240 else 480 end;
    update private.photo_privacy_jobs j set status=result,last_error=p_error_code,ready_at=clock_timestamp()+make_interval(secs=>delay_seconds)
        where j.lease_id=p_lease_id;
    update private.photo_privacy_content c set status=result where c.photo_id=item.photo_id;
    return jsonb_build_object('photo_id',item.photo_id,'status',result);
end;
$$;

create function private.photo_privacy_receipt(p_photo_id uuid)
returns jsonb language plpgsql volatile security definer set search_path = '' as $$
declare item private.photo_privacy_content; state private.photo_privacy_state; policy private.photo_privacy_policies; result text;
begin
    perform private.photo_privacy_require_service();
    if not exists(select 1 from private.photo_privacy_content c where c.photo_id=p_photo_id) then return null; end if;
    item:=private.lock_photo_privacy_source(p_photo_id);
    select * into state from private.photo_privacy_state for share;
    select * into policy from private.photo_privacy_policies p where p.policy_id=state.policy_id;
    result:=case when item.status='withheld' then 'withheld'
        when (item.policy_id,item.policy_revision) is distinct from (state.policy_id,state.policy_revision) then 'pending' else item.status end;
    return jsonb_build_object('photo_id',item.photo_id,'content_revision',item.content_revision,'sanitized_sha256',item.sanitized_sha256,
        'policy_id',policy.policy_id,'policy_revision',coalesce(state.policy_revision,0),'screening_version',policy.screening_version,
        'calibration_version',policy.calibration_version,'status',result);
exception when sqlstate 'WD001' then return null;
end;
$$;

create function private.photo_privacy_operator(p_token text)
returns uuid language plpgsql volatile security definer set search_path = '' as $$
declare operator uuid; actor uuid; token_hash text;
begin
    if p_token is null or p_token !~ '^[0-9a-f]{64}$' then raise exception 'photo privacy authorization refused' using errcode='42501'; end if;
    token_hash:=encode(extensions.digest(convert_to(p_token,'UTF8'),'sha256'),'hex');
    select o.auth_uid into actor from private.photo_privacy_operators o where o.active and o.token_sha256=token_hash;
    if actor is null then raise exception 'photo privacy authorization refused' using errcode='42501'; end if;
    -- Explicit auth-before-operator order matches auth.users ON DELETE CASCADE.
    perform 1 from auth.users u where u.id=actor for share;
    if not found then raise exception 'photo privacy authorization refused' using errcode='42501'; end if;
    select o.operator_id into operator from private.photo_privacy_operators o
    where o.active and o.auth_uid=actor and o.token_sha256=token_hash for share;
    if operator is null then raise exception 'photo privacy authorization refused' using errcode='42501'; end if;
    return operator;
end;
$$;

create function private.photo_privacy_review_context(p_photo_id uuid,p_operator_token text)
returns jsonb language plpgsql volatile security definer set search_path = '' as $$
declare receipt jsonb; path text;
begin
    perform private.photo_privacy_require_service();
    -- The source/contributor locks must precede the operator/auth-row locks.
    receipt:=private.photo_privacy_receipt(p_photo_id);
    perform private.photo_privacy_operator(p_operator_token);
    if receipt is null or receipt->'sanitized_sha256'='null'::jsonb or receipt->'policy_id'='null'::jsonb then return null; end if;
    select p.storage_path into path from public.photos p where p.id=p_photo_id;
    return receipt||jsonb_build_object('storage_path',path);
end;
$$;

create function private.review_photo_privacy(p_operator_token text,p_request jsonb)
returns jsonb language plpgsql volatile security definer set search_path = '' as $$
declare request jsonb:=p_request; photo uuid; review uuid; operator uuid; key text;
    item private.photo_privacy_content; state private.photo_privacy_state; policy private.photo_privacy_policies;
    prior private.photo_privacy_reviews; decision text; result text;
begin
    perform private.photo_privacy_require_service();
    perform private.photo_privacy_object(request,array['schema_version','review_id','photo_id','content_revision','sanitized_sha256',
        'policy_id','policy_revision','screening_version','calibration_version','decision','reason']);
    if request->>'schema_version' is distinct from 'gsip-photo-privacy-v1' then raise exception 'invalid photo privacy request' using errcode='22023'; end if;
    foreach key in array array['review_id','photo_id','policy_id'] loop request:=jsonb_set(request,array[key],to_jsonb(private.photo_privacy_uuid(request->key)::text)); end loop;
    perform private.photo_privacy_int(request->'content_revision',0,9007199254740991);
    perform private.photo_privacy_int(request->'policy_revision',0,9007199254740991);
    perform private.photo_privacy_text(request->'sanitized_sha256','sha');
    perform private.photo_privacy_text(request->'screening_version','version');
    perform private.photo_privacy_text(request->'calibration_version','version');
    decision:=request->>'decision';
    if jsonb_typeof(request->'decision')<>'string' or jsonb_typeof(request->'reason')<>'string'
       or not((decision='clear' and request->>'reason'='false_positive') or (decision='withhold' and request->>'reason'='privacy_risk')) then
        raise exception 'invalid photo privacy request' using errcode='22023';
    end if;
    photo:=(request->>'photo_id')::uuid; review:=(request->>'review_id')::uuid;
    item:=private.lock_photo_privacy_source(photo);
    operator:=private.photo_privacy_operator(p_operator_token);
    select * into state from private.photo_privacy_state for share;
    select * into policy from private.photo_privacy_policies p where p.policy_id=state.policy_id;
    if item.sanitized_sha256 is null or (request->>'content_revision')::bigint<>item.content_revision
       or request->>'sanitized_sha256' is distinct from item.sanitized_sha256
       or (request->>'policy_id')::uuid is distinct from state.policy_id or (request->>'policy_revision')::bigint<>state.policy_revision
       or request->>'screening_version' is distinct from policy.screening_version or request->>'calibration_version' is distinct from policy.calibration_version then
        raise exception 'stale photo privacy state' using errcode='PP002';
    end if;
    select * into prior from private.photo_privacy_reviews r where r.review_id=review;
    if found then
        if prior.request=request and prior.operator_id=operator and not(decision='clear' and item.status='withheld') then
            return jsonb_build_object('photo_id',photo,'content_revision',item.content_revision,'status',case decision when 'clear' then 'clear' else 'withheld' end,'review_id',review);
        end if;
        raise exception 'photo privacy receipt conflict' using errcode='PP003';
    end if;
    if exists(select 1 from private.photo_privacy_tombstones t where t.identity_kind='review' and t.identity_id=review) then
        raise exception 'photo privacy receipt conflict' using errcode='PP003';
    end if;
    if decision='clear' and (item.status not in ('review','clear')
       or (item.policy_id,item.policy_revision) is distinct from (state.policy_id,state.policy_revision)
       or exists(select 1 from private.photo_privacy_tombstones t where t.identity_kind='withhold' and t.identity_id=photo)
       or not exists(select 1 from private.photo_privacy_screens s where s.photo_id=photo and s.content_revision=item.content_revision
           and s.policy_id=state.policy_id and s.policy_revision=state.policy_revision and s.status in ('clear','review'))) then
        raise exception 'stale photo privacy state' using errcode='PP002';
    end if;
    insert into private.photo_privacy_reviews(review_id,photo_id,contributor_id,grant_id,content_revision,policy_id,policy_revision,
        sanitized_sha256,operator_id,decision,reason,request,request_sha256)
    values(review,photo,item.contributor_id,item.grant_id,item.content_revision,state.policy_id,state.policy_revision,
        item.sanitized_sha256,operator,decision,request->>'reason',request,encode(extensions.digest(convert_to(request::text,'UTF8'),'sha256'),'hex'));
    result:=case decision when 'clear' then 'clear' else 'withheld' end;
    if decision='withhold' then
        insert into private.photo_privacy_tombstones values('withhold',photo,item.grant_id,'privacy_risk') on conflict do nothing;
        update private.photo_privacy_jobs j set status='invalidated' where j.photo_id=photo and j.status='processing';
    end if;
    update private.photo_privacy_content c set status=result,policy_id=state.policy_id,policy_revision=state.policy_revision where c.photo_id=photo;
    return jsonb_build_object('photo_id',photo,'content_revision',item.content_revision,'status',result,'review_id',review);
exception when unique_violation then raise exception 'photo privacy receipt conflict' using errcode='PP003';
end;
$$;

create function private.authorize_photo_privacy_export(p_request jsonb)
returns jsonb language plpgsql volatile security definer set search_path = '' as $$
declare request jsonb:=p_request; entry jsonb; normalized jsonb:='[]'::jsonb; photo uuid; seen uuid[]:=array[]::uuid[];
    owner_id uuid; key text; item private.photo_privacy_content; state private.photo_privacy_state; policy private.photo_privacy_policies;
    allowed boolean; publication boolean; authorizations jsonb:='[]'::jsonb;
begin
    perform private.photo_privacy_require_service();
    perform private.photo_privacy_object(request,array['schema_version','photos'],8000000);
    if request->>'schema_version' is distinct from 'gsip-photo-privacy-v1' or jsonb_typeof(request->'photos')<>'array' then
        raise exception 'invalid photo privacy request' using errcode='22023';
    end if;
    if jsonb_array_length(request->'photos')>10000 then raise exception 'invalid photo privacy request' using errcode='22023'; end if;
    for entry in select value from jsonb_array_elements(request->'photos') loop
        perform private.photo_privacy_object(entry,array['photo_id','content_revision','policy_id','policy_revision','sanitized_sha256','screening_version','calibration_version']);
        foreach key in array array['photo_id','policy_id'] loop entry:=jsonb_set(entry,array[key],to_jsonb(private.photo_privacy_uuid(entry->key)::text)); end loop;
        photo:=(entry->>'photo_id')::uuid;
        if photo=any(seen) then raise exception 'invalid photo privacy request' using errcode='22023'; end if;
        seen:=array_append(seen,photo);
        perform private.photo_privacy_int(entry->'content_revision',0,9007199254740991);
        perform private.photo_privacy_int(entry->'policy_revision',0,9007199254740991);
        perform private.photo_privacy_text(entry->'sanitized_sha256','sha');
        perform private.photo_privacy_text(entry->'screening_version','version');
        perform private.photo_privacy_text(entry->'calibration_version','version');
        normalized:=normalized||jsonb_build_array(entry);
    end loop;
    -- Contributor order precedes private, source and policy locks for the whole batch.
    for owner_id in select distinct s.contributor_id from public.photos p join public.submissions s on s.id=p.submission_id
        where p.id=any(seen) order by s.contributor_id loop
        perform 1 from public.contributors c where c.id=owner_id for update;
    end loop;
    -- Lock each source/content before policy; a gate update never seeks contributors.
    for photo in select unnest(seen) loop
        begin perform private.lock_photo_privacy_source(photo); exception when sqlstate 'WD001' or sqlstate '42501' or sqlstate 'PP002' then null; end;
    end loop;
    select * into state from private.photo_privacy_state for share;
    select * into policy from private.photo_privacy_policies p where p.policy_id=state.policy_id;
    publication:=coalesce(state.publication_open and state.implementation_deployed and policy.owner_approval_sha256 is not null,false);
    for entry in select value from jsonb_array_elements(normalized) loop
        photo:=(entry->>'photo_id')::uuid; allowed:=false;
        begin
            item:=private.lock_photo_privacy_source(photo);
            allowed:=publication and item.status='clear'
                and (item.policy_id,item.policy_revision) is not distinct from (state.policy_id,state.policy_revision)
                and item.content_revision=(entry->>'content_revision')::bigint and item.sanitized_sha256=entry->>'sanitized_sha256'
                and state.policy_id=(entry->>'policy_id')::uuid and state.policy_revision=(entry->>'policy_revision')::bigint
                and policy.screening_version=entry->>'screening_version' and policy.calibration_version=entry->>'calibration_version'
                and not exists(select 1 from private.photo_privacy_tombstones t where t.identity_kind='withhold' and t.identity_id=photo)
                -- The mutable current-state flag alone is never detector/manual authority.
                and exists(select 1 from private.photo_privacy_screens screen where screen.photo_id=photo
                    and screen.content_revision=item.content_revision and screen.policy_id=state.policy_id
                    and screen.policy_revision=state.policy_revision and screen.sanitized_sha256=item.sanitized_sha256
                    and (screen.status='clear' or (screen.status='review' and exists(
                        select 1 from private.photo_privacy_reviews review where review.photo_id=photo
                          and review.content_revision=item.content_revision and review.policy_id=state.policy_id
                          and review.policy_revision=state.policy_revision and review.sanitized_sha256=item.sanitized_sha256
                          and review.decision='clear'))))
                and exists(select 1 from public.photos p join public.submissions s on s.id=p.submission_id
                    join public.contribution_grants g on g.id=s.grant_id join public.terms_versions t on t.version=g.terms_version
                    join public.actors a on a.id=s.actor_id
                    where p.id=photo and p.qa_status='pass' and p.provenance_tier>=0 and s.status='qa_pass' and s.finalized_at is not null
                      and not s.is_synthetic and s.provenance_tier>=0 and a.status='active'
                      and g.data_license='ODbL-1.0' and g.photo_license='CC-BY-SA-4.0' and g.accepted_at<=now()
                      and t.published_at<=g.accepted_at and (t.retired_at is null or t.retired_at>g.accepted_at)
                      and (g.attribution_name='Anonymous soil contributor' or exists(select 1 from public.attribution_reviews r
                          where r.contributor_id=g.contributor_id and r.attribution_name=g.attribution_name and r.decision='approved'))
                      and exists(select 1 from public.photos required where required.submission_id=s.id and required.shot_type='A' and required.qa_status='pass')
                      and exists(select 1 from public.photos required where required.submission_id=s.id and required.shot_type='B' and required.qa_status='pass'));
        exception when sqlstate 'WD001' or sqlstate '42501' or sqlstate 'PP002' then allowed:=false;
        end;
        authorizations:=authorizations||jsonb_build_array(jsonb_build_object('photo_id',photo,'authorized',coalesce(allowed,false)));
    end loop;
    return jsonb_build_object('version','gsip-photo-privacy-v1','publication_open',publication,'policy_id',policy.policy_id,
        'policy_revision',coalesce(state.policy_revision,0),'screening_version',policy.screening_version,
        'calibration_version',policy.calibration_version,'authorizations',authorizations);
end;
$$;

create function private.erase_photo_privacy_photo(p_photo uuid,p_grant uuid,p_reason text)
returns void language plpgsql volatile security definer set search_path = '' as $$
begin
    insert into private.photo_privacy_tombstones values('photo',p_photo,p_grant,p_reason) on conflict do nothing;
    insert into private.photo_privacy_tombstones(identity_kind,identity_id,grant_id,reason)
        select 'screen',s.request_id,s.grant_id,p_reason from private.photo_privacy_screens s where s.photo_id=p_photo on conflict do nothing;
    insert into private.photo_privacy_tombstones(identity_kind,identity_id,grant_id,reason)
        select 'review',r.review_id,r.grant_id,p_reason from private.photo_privacy_reviews r where r.photo_id=p_photo on conflict do nothing;
    delete from private.photo_privacy_screens s where s.photo_id=p_photo;
    delete from private.photo_privacy_reviews r where r.photo_id=p_photo;
    delete from private.photo_privacy_jobs j where j.photo_id=p_photo;
    delete from private.photo_privacy_content c where c.photo_id=p_photo;
end;
$$;
create function private.erase_photo_privacy_grant(p_grant uuid,p_reason text)
returns void language plpgsql volatile security definer set search_path = '' as $$
declare photo uuid;
begin
    for photo in select distinct photo_id from (
        select c.photo_id from private.photo_privacy_content c where c.grant_id=p_grant union all
        select j.photo_id from private.photo_privacy_jobs j where j.grant_id=p_grant union all
        select s.photo_id from private.photo_privacy_screens s where s.grant_id=p_grant union all
        select r.photo_id from private.photo_privacy_reviews r where r.grant_id=p_grant
    ) covered loop perform private.erase_photo_privacy_photo(photo,p_grant,p_reason); end loop;
end;
$$;
create function private.erase_photo_privacy_on_withdrawal()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
    -- Existing grant_withdrawals_00_library_lock already serializes contributor first.
    perform private.erase_photo_privacy_grant(new.grant_id,case new.reason when 'account_deletion' then 'account_deletion' else 'withdrawn' end);
    return new;
end;
$$;
create trigger grant_withdrawals_erase_photo_privacy after insert on public.grant_withdrawals
    for each row execute function private.erase_photo_privacy_on_withdrawal();
create function private.photo_privacy_account_cleanup()
returns trigger language plpgsql security definer set search_path = '' as $$
declare item record;
begin
    if new.kind='delete_account' then
        for item in select distinct photo_id,grant_id from (
            select c.photo_id,c.grant_id from private.photo_privacy_content c where c.contributor_id=new.contributor_id union all
            select j.photo_id,j.grant_id from private.photo_privacy_jobs j where j.contributor_id=new.contributor_id union all
            select s.photo_id,s.grant_id from private.photo_privacy_screens s where s.contributor_id=new.contributor_id union all
            select r.photo_id,r.grant_id from private.photo_privacy_reviews r where r.contributor_id=new.contributor_id
        ) covered loop perform private.erase_photo_privacy_photo(item.photo_id,item.grant_id,'account_deletion'); end loop;
    end if;
    return new;
end;
$$;
create trigger deletion_requests_z_photo_privacy_cleanup after insert on public.deletion_requests
    for each row execute function private.photo_privacy_account_cleanup();
create function private.guard_photo_privacy_request_completion()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
    if new.status='completed' and exists(select 1 from (
        select c.contributor_id,c.grant_id from private.photo_privacy_content c union all
        select j.contributor_id,j.grant_id from private.photo_privacy_jobs j union all
        select s.contributor_id,s.grant_id from private.photo_privacy_screens s union all
        select r.contributor_id,r.grant_id from private.photo_privacy_reviews r
    ) covered where covered.contributor_id=new.contributor_id and (new.kind='delete_account'
        or exists(select 1 from public.grant_withdrawals w where w.grant_id=covered.grant_id)
        or exists(select 1 from public.contribution_grants g where g.id=covered.grant_id and g.accepted_at<=new.requested_at))) then
        raise exception 'covered photo privacy payload remains' using errcode='55000';
    end if;
    return new;
end;
$$;
create trigger deletion_requests_photo_privacy_completion_guard before insert or update of status on public.deletion_requests
    for each row execute function private.guard_photo_privacy_request_completion();
create function private.erase_photo_privacy_source()
returns trigger language plpgsql security definer set search_path = '' as $$
declare item record; original_grant uuid;
begin
    -- The direct DELETE already holds its source row. Never acquire contributor here.
    if tg_table_name='submissions' then
        for item in select p.id as photo_id from public.photos p where p.submission_id=old.id
            union select c.photo_id from private.photo_privacy_content c where c.submission_id=old.id
        loop perform private.erase_photo_privacy_photo(item.photo_id,old.grant_id,'source_deleted'); end loop;
    else
        select s.grant_id into original_grant from public.submissions s where s.id=old.submission_id;
        if original_grant is null then select c.grant_id into original_grant from private.photo_privacy_content c where c.photo_id=old.id; end if;
        if original_grant is not null then perform private.erase_photo_privacy_photo(old.id,original_grant,'source_deleted'); end if;
    end if;
    return old;
end;
$$;
create trigger submissions_tombstone_photo_privacy before delete on public.submissions
    for each row execute function private.erase_photo_privacy_source();
create trigger photos_tombstone_photo_privacy before delete on public.photos
    for each row execute function private.erase_photo_privacy_source();
-- This BEFORE trigger precedes legacy source checks and source/FK row locks.
-- A statement begun before withdrawal must recheck rights after waiting on its owner.
create function private.admit_photo_privacy_source()
returns trigger language plpgsql security definer set search_path = '' as $$
declare owner_id uuid; original_grant uuid; accepted timestamptz;
begin
    perform private.photo_privacy_require_current_transaction();
    select s.contributor_id into owner_id from public.submissions s where s.id=new.submission_id;
    if owner_id is null then raise exception 'photo privacy authorization refused' using errcode='42501'; end if;
    perform 1 from public.contributors c where c.id=owner_id for update;
    if not found then raise exception 'photo privacy authorization refused' using errcode='42501'; end if;
    -- Parent ownership/grant is refreshed and fenced before the source is inserted.
    select s.grant_id,g.accepted_at into original_grant,accepted from public.submissions s
        join public.contribution_grants g on g.id=s.grant_id
        where s.id=new.submission_id and s.contributor_id=owner_id for share of s nowait;
    if not found then raise exception 'photo privacy authorization refused' using errcode='42501'; end if;
    if exists(select 1 from public.grant_withdrawals w where w.grant_id=original_grant) then
        -- Preserve the existing public photo-insert rights error contract.
        raise exception 'the contribution grant for this photo has been withdrawn' using errcode='WD001';
    end if;
    if exists(select 1 from public.deletion_requests r where r.contributor_id=owner_id
            and (r.kind='delete_account' or r.requested_at>=accepted))
       or exists(select 1 from private.photo_privacy_tombstones t where t.identity_kind in ('photo','withhold') and t.identity_id=new.id) then
        raise exception 'photo privacy contribution withdrawn' using errcode='WD001';
    end if;
    return new;
exception when lock_not_available then
    raise exception 'stale photo privacy state' using errcode='PP002';
end;
$$;
create trigger photos_00_privacy_admission before insert on public.photos
    for each row execute function private.admit_photo_privacy_source();
create function private.initialize_photo_privacy()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
    if exists(select 1 from private.photo_privacy_tombstones t where t.identity_kind in ('photo','withhold') and t.identity_id=new.id) then
        raise exception 'photo privacy contribution withdrawn' using errcode='WD001';
    end if;
    -- The BEFORE admission guard still holds contributor/parent locks here.
    insert into private.photo_privacy_content(photo_id,submission_id,contributor_id,grant_id)
    select new.id,s.id,s.contributor_id,s.grant_id from public.submissions s where s.id=new.submission_id;
    return new;
end;
$$;
create trigger photos_initialize_privacy after insert on public.photos
    for each row execute function private.initialize_photo_privacy();
create function private.invalidate_photo_privacy_source()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
    if new.submission_id is distinct from old.submission_id or new.shot_type is distinct from old.shot_type then
        raise exception 'photo privacy source identity is immutable' using errcode='PP003';
    end if;
    if new.storage_path is distinct from old.storage_path then
        -- UPDATE holds source first; no contributor lock is added in this trigger.
        update private.photo_privacy_content c set content_revision=c.content_revision+1,sanitized_sha256=null,
            byte_count=null,sanitizer_version=null,policy_id=null,policy_revision=null,
            status=case when c.status='withheld' then 'withheld' else 'pending' end where c.photo_id=old.id;
        update private.photo_privacy_jobs j set status='invalidated' where j.photo_id=old.id and j.status<>'invalidated';
    end if;
    return new;
end;
$$;
create trigger photos_invalidate_privacy before update of storage_path,submission_id,shot_type on public.photos
    for each row execute function private.invalidate_photo_privacy_source();

-- Initial state is unverified/pending even for previously QA-passing photographs.
insert into private.photo_privacy_content(photo_id,submission_id,contributor_id,grant_id)
select p.id,s.id,s.contributor_id,s.grant_id from public.photos p join public.submissions s on s.id=p.submission_id;
-- Historic withdrawals are already effective; backfill must not retain their new payload.
do $$
declare item record;
begin
    for item in select distinct c.grant_id from private.photo_privacy_content c
        join public.contribution_grants g on g.id=c.grant_id
        where exists(select 1 from public.grant_withdrawals w where w.grant_id=c.grant_id)
           or exists(select 1 from public.deletion_requests r where r.contributor_id=c.contributor_id
                and (r.kind='delete_account' or r.requested_at>=g.accepted_at))
    loop perform private.erase_photo_privacy_grant(item.grant_id,'withdrawn'); end loop;
end;
$$;

-- Private helpers have no callable service/client entry point. Only the nine
-- definition-time bound public invoker wrappers dispatch to their private bodies.
do $$
declare fn record;
begin
    for fn in select p.oid::regprocedure as signature from pg_proc p join pg_namespace n on n.oid=p.pronamespace
        where n.nspname='private' and p.proname like '%photo_privacy%'
    loop execute format('revoke all on function %s from public, anon, authenticated, service_role',fn.signature); end loop;
end;
$$;

create function public.photo_privacy_capabilities() returns jsonb language sql stable security invoker set search_path=''
return private.photo_privacy_capabilities();
create function public.record_photo_privacy_content(p_request jsonb) returns jsonb language sql volatile security invoker set search_path=''
return private.record_photo_privacy_content(p_request);
create function public.claim_photo_privacy_job() returns jsonb language sql volatile security invoker set search_path=''
return private.claim_photo_privacy_job();
create function public.complete_photo_privacy_job(p_lease_id uuid,p_receipt jsonb) returns jsonb language sql volatile security invoker set search_path=''
return private.complete_photo_privacy_job(p_lease_id,p_receipt);
create function public.fail_photo_privacy_job(p_lease_id uuid,p_error_code text) returns jsonb language sql volatile security invoker set search_path=''
return private.fail_photo_privacy_job(p_lease_id,p_error_code);
create function public.photo_privacy_receipt(p_photo_id uuid) returns jsonb language sql volatile security invoker set search_path=''
return private.photo_privacy_receipt(p_photo_id);
create function public.photo_privacy_review_context(p_photo_id uuid,p_operator_token text) returns jsonb language sql volatile security invoker set search_path=''
return private.photo_privacy_review_context(p_photo_id,p_operator_token);
create function public.review_photo_privacy(p_operator_token text,p_request jsonb) returns jsonb language sql volatile security invoker set search_path=''
return private.review_photo_privacy(p_operator_token,p_request);
create function public.authorize_photo_privacy_export(p_request jsonb) returns jsonb language sql volatile security invoker set search_path=''
return private.authorize_photo_privacy_export(p_request);
do $$
declare signature text;
begin
    foreach signature in array array['photo_privacy_capabilities()','record_photo_privacy_content(jsonb)',
        'claim_photo_privacy_job()','complete_photo_privacy_job(uuid,jsonb)','fail_photo_privacy_job(uuid,text)',
        'photo_privacy_receipt(uuid)','photo_privacy_review_context(uuid,text)','review_photo_privacy(text,jsonb)',
        'authorize_photo_privacy_export(jsonb)'] loop
        execute 'revoke all on function public.'||signature||' from public, anon, authenticated, service_role';
        execute 'grant execute on function public.'||signature||' to service_role';
        execute 'grant execute on function private.'||signature||' to service_role';
    end loop;
end;
$$;
comment on table private.photo_privacy_state is 'Owner-admin configuration only. Missing/unapproved policy and initial publication gate are closed. No service provisioning RPC.';
comment on table private.photo_privacy_screens is 'Immutable private exact-byte/policy screen receipts, bounded card-mask evidence only. No OCR, detector boxes, crops or public release.';
comment on table private.photo_privacy_tombstones is 'Opaque immutable refusal IDs and original grant reference only. Permanent human withholding never resets for a photo UUID.';
commit;
