-- WP-6e: the provenance foundation (SPEC I9, I10, I11 and the I15 holdout flag), landed while
-- production holds little or no real data so no later backfill is needed.
--   * actors: every contributor has exactly one human actor, revoked when the contributor has no
--     sign-in; agents, devices and labs act only for an active human operator (I9). An actor's
--     identity never changes and revocation is final, reaching every actor the operator runs.
--   * submissions carry a server-set actor, a provenance tier and four client claims
--     (ingest_path, capture_method, location_source, client_version). Claims never raise a tier
--     (I10). Synthetic rows are exactly tier -1 and never become field data again (I11).
--   * photos carry private capture evidence (never coordinates or timestamps). The database
--     derives every tier from that evidence; a direct write cannot set one. A submission's tier is
--     the minimum of shots A and B; tiers 2 (attested) and 3 (lab-verified) are reserved.
--   * terms_versions: a grant must cite a published, unretired version, be accepted within the
--     last 30 days and not in the future; the server records when it received the grant.
--   * gold_labels.holdout: server-only; releases never carry holdout labels (I15).

-- Actors -----------------------------------------------------------------------------------------

create table public.actors (
    id uuid primary key default gen_random_uuid(),
    kind text not null check (kind in ('human', 'agent', 'device', 'lab')),
    contributor_id uuid references public.contributors (id),
    operator_id uuid references public.actors (id),
    model_family text check (char_length(model_family) between 1 and 80),
    model_version text check (char_length(model_version) between 1 and 80),
    status text not null default 'active' check (status in ('active', 'revoked')),
    created_at timestamptz not null default now(),
    constraint actors_human_is_a_contributor check (
        (kind = 'human') = (contributor_id is not null and operator_id is null)
    ),
    constraint actors_non_human_has_operator check (kind = 'human' or operator_id is not null)
);

create unique index actors_one_human_per_contributor
    on public.actors (contributor_id) where kind = 'human';
create index actors_operator_idx on public.actors (operator_id);

comment on table public.actors is
    'WP-6e (I9, I10): who acted. One human actor per contributor; agents, devices and labs act only for an active human operator. Identity is immutable and revocation is final.';

alter table public.actors enable row level security;
-- Not even the service role deletes or truncates actors: revocation is how an actor ends.
revoke all on public.actors from public, anon, authenticated, service_role;
grant select (id, kind, status, created_at) on public.actors to authenticated;
grant select, insert, update on public.actors to service_role;
create policy actors_select_own on public.actors
    for select to authenticated
    using (kind = 'human' and contributor_id = public.current_contributor_id());

-- An operator is an active human actor: an agent cannot vouch for another agent, and a revoked
-- person cannot start new agents. Who an actor is never changes, and revocation is final.
create function private.guard_actor()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    if tg_op = 'UPDATE' then
        if new.kind is distinct from old.kind
           or new.contributor_id is distinct from old.contributor_id
           or new.operator_id is distinct from old.operator_id then
            raise exception 'an actor''s identity never changes' using errcode = '23514';
        end if;
        if old.status = 'revoked' and new.status <> 'revoked' then
            raise exception 'revocation is final' using errcode = '23514';
        end if;
    end if;
    if new.operator_id is not null and not exists (
        select 1 from public.actors a
        where a.id = new.operator_id
          and a.kind = 'human'
          and (a.status = 'active' or new.status = 'revoked')
    ) then
        raise exception 'an operator must be an active human actor' using errcode = '23514';
    end if;
    return new;
end;
$$;

revoke all on function private.guard_actor() from public, anon, authenticated;

create trigger actors_guard
before insert or update of kind, contributor_id, operator_id, status on public.actors
for each row execute function private.guard_actor();

-- Revoking an operator revokes everything acting for it (I9).
create function private.revoke_operated_actors()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    update public.actors a set status = 'revoked'
    where a.operator_id = new.id and a.status <> 'revoked';
    return new;
end;
$$;

revoke all on function private.revoke_operated_actors() from public, anon, authenticated;

create trigger actors_revoke_operated
after update of status on public.actors
for each row
when (new.status = 'revoked' and old.status is distinct from 'revoked')
execute function private.revoke_operated_actors();

-- Contributors already unlinked from sign-in (accounts deleted under WP-6d) get revoked actors.
insert into public.actors (kind, contributor_id, status)
select 'human', c.id, case when c.auth_uid is null then 'revoked' else 'active' end
from public.contributors c
where not exists (
    select 1 from public.actors a where a.kind = 'human' and a.contributor_id = c.id
);

create function private.create_human_actor()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.actors (kind, contributor_id, status)
    values ('human', new.id, case when new.auth_uid is null then 'revoked' else 'active' end);
    return new;
end;
$$;

revoke all on function private.create_human_actor() from public, anon, authenticated;

create trigger contributors_create_human_actor
after insert on public.contributors
for each row execute function private.create_human_actor();

-- An account deletion unlinks the contributor from sign-in (WP-6d); its human actor, and every
-- actor it operated, is revoked with it.
create function private.revoke_unlinked_contributor()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    update public.actors a set status = 'revoked'
    where a.kind = 'human' and a.contributor_id = new.id and a.status <> 'revoked';
    return new;
end;
$$;

revoke all on function private.revoke_unlinked_contributor() from public, anon, authenticated;

create trigger contributors_revoke_unlinked
after update of auth_uid on public.contributors
for each row
when (old.auth_uid is not null and new.auth_uid is null)
execute function private.revoke_unlinked_contributor();

-- Submission provenance -------------------------------------------------------------------------

alter table public.submissions
    add column actor_id uuid references public.actors (id),
    add column ingest_path text not null default 'web' check (ingest_path in ('web', 'app')),
    add column capture_method text not null default 'unknown'
        check (capture_method in ('camera', 'file', 'unknown')),
    add column location_source text not null default 'unknown'
        check (location_source in ('device_gps', 'manual_pin', 'unknown')),
    add column client_version text
        check (client_version ~ '^[0-9A-Za-z][0-9A-Za-z.+_-]{0,63}$'),
    add column provenance_tier smallint not null default 0
        check (provenance_tier between -1 and 3);

comment on column public.submissions.ingest_path is 'Client claim (web or app). Never raises a tier.';
comment on column public.submissions.capture_method is 'Client claim. Never raises a tier.';
comment on column public.submissions.location_source is 'Client claim. Never raises a tier.';
comment on column public.submissions.client_version is
    'Client claim (I10 software version): the capture app build; null for earlier submissions.';
comment on column public.submissions.provenance_tier is
    'Derived by the database (I10): -1 synthetic, 0 unattested, 1 corroborated by both required photos, 2 attested, 3 lab-verified. Writes are ignored.';

update public.submissions s
set
    actor_id = a.id,
    provenance_tier = case when s.is_synthetic then -1 else 0 end
from public.actors a
where a.kind = 'human' and a.contributor_id = s.contributor_id;

alter table public.submissions alter column actor_id set not null;
alter table public.submissions add constraint submissions_synthetic_is_tier_minus_one
    check (is_synthetic = (provenance_tier = -1));
-- Tiers 2 (attested) and 3 (lab-verified) wait for their evidence paths; the work package that
-- adds attestation or lab pairing drops this constraint and extends the tier rules below.
alter table public.submissions add constraint submissions_reserved_tiers_unassigned
    check (provenance_tier <= 1);
create index submissions_actor_idx on public.submissions (actor_id);

-- Photos carry private evidence and their own tier (constrained and derived below).
alter table public.photos
    add column capture_evidence_private jsonb,
    add column provenance_tier smallint not null default 0
        check (provenance_tier between -1 and 3);

-- A submission's tier: -1 when synthetic, otherwise the lower of shots A and B (0 until both
-- exist). Volatile, so it reads with a fresh snapshot: called after the submission row is locked,
-- it sees every photo committed before it, and two photos finishing at once cannot leave a stale
-- tier behind.
create function private.derived_submission_tier(p_submission_id uuid, p_synthetic boolean)
returns smallint
language sql
volatile
set search_path = ''
as $$
    select (case
        when p_synthetic then -1
        else greatest(0, coalesce((
            select case
                when count(*) filter (where p.shot_type = 'A') > 0
                     and count(*) filter (where p.shot_type = 'B') > 0
                then least(
                    min(p.provenance_tier) filter (where p.shot_type = 'A'),
                    min(p.provenance_tier) filter (where p.shot_type = 'B')
                )
            end
            from public.photos p
            where p.submission_id = p_submission_id
        ), 0))
    end)::smallint
$$;

revoke all on function private.derived_submission_tier(uuid, boolean)
    from public, anon, authenticated;

-- The server, never the client, sets who acted, and the tier is always derived, whatever was
-- written. The actor defaults to the contributor's human actor; a server path that records another
-- actor (an agent, a device) must name one that is active and operated by that contributor's
-- active human actor (I9). A synthetic row can be quarantined from field data but never released
-- back into it (I11).
create function private.set_submission_provenance()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    if tg_op = 'UPDATE' and old.is_synthetic and not new.is_synthetic then
        raise exception 'a synthetic row can never become field data' using errcode = '23514';
    end if;
    if tg_op = 'INSERT' and new.actor_id is null then
        select a.id into new.actor_id
        from public.actors a
        where a.kind = 'human' and a.contributor_id = new.contributor_id;
    end if;
    if (tg_op = 'INSERT'
        or new.actor_id is distinct from old.actor_id
        or new.contributor_id is distinct from old.contributor_id)
       and not exists (
            select 1
            from public.actors a
            left join public.actors operator on operator.id = a.operator_id
            where a.id = new.actor_id
              and a.status = 'active'
              and (
                  (a.kind = 'human' and a.contributor_id = new.contributor_id)
                  or (a.kind <> 'human'
                      and operator.kind = 'human'
                      and operator.status = 'active'
                      and operator.contributor_id = new.contributor_id)
              )
       ) then
        raise exception 'the actor must be active and act for the submission''s contributor'
            using errcode = '23514';
    end if;
    new.provenance_tier := private.derived_submission_tier(new.id, new.is_synthetic);
    return new;
end;
$$;

revoke all on function private.set_submission_provenance() from public, anon, authenticated;

create trigger submissions_set_provenance
before insert or update of is_synthetic, actor_id, contributor_id, provenance_tier
on public.submissions
for each row execute function private.set_submission_provenance();

-- Clients may state their claims; actor_id and provenance_tier stay server-only.
grant insert (ingest_path, capture_method, location_source, client_version)
    on public.submissions to authenticated;

-- Photo evidence ---------------------------------------------------------------------------------

-- Exactly these keys, with booleans, whole numbers (or null) and a version string: a duration
-- and a distance can be stored, a coordinate or a timestamp cannot (I7).
alter table public.photos add constraint photos_capture_evidence_allowlist check (
    capture_evidence_private is null
    or (
        jsonb_typeof(capture_evidence_private) = 'object'
        and capture_evidence_private - array[
            'evidence_version', 'exif_time_present', 'exif_time_absolute', 'exif_time_delta_s',
            'exif_age_at_acceptance_s', 'exif_gps_present', 'exif_gps_distance_m'
        ]::text[] = '{}'::jsonb
        and capture_evidence_private ?& array[
            'evidence_version', 'exif_time_present', 'exif_time_absolute', 'exif_time_delta_s',
            'exif_age_at_acceptance_s', 'exif_gps_present', 'exif_gps_distance_m'
        ]::text[]
        and jsonb_typeof(capture_evidence_private -> 'evidence_version') = 'string'
        and jsonb_typeof(capture_evidence_private -> 'exif_time_present') = 'boolean'
        and jsonb_typeof(capture_evidence_private -> 'exif_time_absolute') = 'boolean'
        and jsonb_typeof(capture_evidence_private -> 'exif_gps_present') = 'boolean'
        and (case jsonb_typeof(capture_evidence_private -> 'exif_time_delta_s')
            when 'null' then true
            when 'number' then (capture_evidence_private ->> 'exif_time_delta_s')::numeric % 1 = 0
            else false
        end)
        and (case jsonb_typeof(capture_evidence_private -> 'exif_age_at_acceptance_s')
            when 'null' then true
            when 'number'
                then (capture_evidence_private ->> 'exif_age_at_acceptance_s')::numeric % 1 = 0
            else false
        end)
        and (case jsonb_typeof(capture_evidence_private -> 'exif_gps_distance_m')
            when 'null' then true
            when 'number'
                then (capture_evidence_private ->> 'exif_gps_distance_m')::numeric % 1 = 0
            else false
        end)
    )
);

comment on column public.photos.capture_evidence_private is
    'I7/I10: private evidence derived by QA from the original upload before stripping: booleans, whole-second time differences and a whole-metre distance. Never coordinates or timestamps.';
comment on column public.photos.provenance_tier is
    'Derived by the database from capture_evidence_private (I10): -1 synthetic, otherwise 0 or 1. Writes are ignored.';

alter table public.photos add constraint photos_reserved_tiers_unassigned
    check (provenance_tier <= 1);

update public.photos p set provenance_tier = -1
from public.submissions s
where s.id = p.submission_id and s.is_synthetic;

-- Tier 1 (corroborated, evidence version exif-v1): the photo's own capture time is absolute (it
-- carries its time zone, or is the GPS fix time), lies within 30 minutes of the claimed capture
-- time, and was taken within the hour before its person accepted the terms for the observation
-- (five minutes of clock skew allowed); and any position embedded in the photo lies within 250 m
-- of the claimed point. Capture metadata can be forged: this is corroboration, not proof.
create function private.photo_tier_from_evidence(evidence jsonb)
returns smallint
language sql
immutable
set search_path = ''
as $$
    select (case
        when evidence ->> 'evidence_version' = 'exif-v1'
         and (evidence ->> 'exif_time_absolute')::boolean
         and (evidence ->> 'exif_time_delta_s')::numeric <= 1800
         and (evidence ->> 'exif_age_at_acceptance_s')::numeric between -300 and 3600
         and (
             not (evidence ->> 'exif_gps_present')::boolean
             or (evidence ->> 'exif_gps_distance_m')::numeric <= 250
         )
        then 1
        else 0
    end)::smallint
$$;

revoke all on function private.photo_tier_from_evidence(jsonb) from public, anon, authenticated;

-- A photo's tier is always derived, whoever writes the row: -1 when its submission is synthetic,
-- otherwise from its evidence.
create function private.derive_photo_tier()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
    synthetic boolean;
begin
    select s.is_synthetic into synthetic from public.submissions s where s.id = new.submission_id;
    new.provenance_tier := case
        when synthetic then -1
        else private.photo_tier_from_evidence(new.capture_evidence_private)
    end;
    return new;
end;
$$;

revoke all on function private.derive_photo_tier() from public, anon, authenticated;

create trigger photos_derive_tier
before insert or update of provenance_tier, capture_evidence_private, submission_id
on public.photos
for each row execute function private.derive_photo_tier();

-- Quarantining a submission as synthetic takes its photos down with it.
create function private.quarantine_synthetic_photos()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    update public.photos p set provenance_tier = p.provenance_tier
    where p.submission_id = new.id;
    return null;
end;
$$;

revoke all on function private.quarantine_synthetic_photos() from public, anon, authenticated;

create trigger submissions_quarantine_synthetic_photos
after update of is_synthetic on public.submissions
for each row
when (new.is_synthetic and not old.is_synthetic)
execute function private.quarantine_synthetic_photos();

-- Any change to a photo's evidence, tier, shot or submission re-derives its submission's tier,
-- under the submission's row lock (see private.derived_submission_tier). The evidence column is
-- listed because a derived tier changed by a BEFORE trigger does not fire "update of" triggers.
create function private.refresh_submission_tier()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    update public.submissions s set provenance_tier = s.provenance_tier
    where s.id in (new.submission_id, old.submission_id);
    return null;
end;
$$;

revoke all on function private.refresh_submission_tier() from public, anon, authenticated;

create trigger photos_refresh_submission_tier
after insert or delete
    or update of provenance_tier, capture_evidence_private, shot_type, submission_id
on public.photos
for each row execute function private.refresh_submission_tier();

-- Terms versions and grants under I9 -------------------------------------------------------------

create table public.terms_versions (
    version text primary key check (char_length(version) between 1 and 64),
    published_at timestamptz not null,
    retired_at timestamptz,
    url text check (url ~ '^https://'),
    summary text check (char_length(summary) <= 500),
    constraint terms_versions_retired_after_published
        check (retired_at is null or retired_at > published_at)
);

comment on table public.terms_versions is
    'WP-6e (I9): the published contribution terms. A grant must cite a version that was published, and not retired, when it was accepted.';

alter table public.terms_versions enable row level security;
revoke all on public.terms_versions from public, anon, authenticated, service_role;
grant select on public.terms_versions to anon, authenticated;
grant select, insert, update on public.terms_versions to service_role;
create policy terms_versions_read_all on public.terms_versions
    for select to anon, authenticated using (true);

-- The in-app grant text the capture client has shipped with since July (capture stays closed until
-- counsel approves the next version).
insert into public.terms_versions (version, published_at, summary)
values (
    '2026-07-22-v1',
    '2026-07-22T00:00:00Z',
    'In-app grant: ODbL 1.0 structured data and CC BY-SA 4.0 photos (pre-launch).'
)
on conflict (version) do nothing;
-- Before WP-6e the version was free text written by the client. Any other value an existing grant
-- cites is recorded only so those immutable grants stay valid: retired at once, so no new grant
-- can cite it, with a fixed publication time that reveals nobody's acceptance time.
insert into public.terms_versions (version, published_at, retired_at, summary)
select g.terms_version, timestamptz '2026-07-22T00:00:00Z', now(),
    'Recorded from grants made before WP-6e; retired.'
from public.contribution_grants g
where g.terms_version <> '2026-07-22-v1'
group by g.terms_version
on conflict (version) do nothing;

alter table public.contribution_grants add constraint contribution_grants_terms_version_fkey
    foreign key (terms_version) references public.terms_versions (version);

-- The server records when it received each grant from now on; earlier grants, which are
-- immutable, keep an unknown (null) receipt time.
alter table public.contribution_grants add column received_at timestamptz;

create function private.record_grant_receipt()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    new.received_at := now();
    return new;
end;
$$;

revoke all on function private.record_grant_receipt() from public, anon, authenticated;

create trigger contribution_grants_record_receipt
before insert on public.contribution_grants
for each row execute function private.record_grant_receipt();

revoke insert on public.contribution_grants from authenticated;
grant insert (id, contributor_id, terms_version, accepted_at, attribution_name)
    on public.contribution_grants to authenticated;

drop policy if exists contribution_grants_insert_own on public.contribution_grants;
create policy contribution_grants_insert_own on public.contribution_grants
    for insert to authenticated
    with check (
        contributor_id = public.current_contributor_id()
        and accepted_at <= now()
        and accepted_at >= now() - interval '30 days'
        and public.capture_is_open()
        and exists (
            select 1 from public.terms_versions t
            where t.version = terms_version
              and t.published_at <= accepted_at
              and (t.retired_at is null or t.retired_at > accepted_at)
        )
    );

-- Holdout (I15) ----------------------------------------------------------------------------------

alter table public.gold_labels add column holdout boolean not null default false;

comment on column public.gold_labels.holdout is
    'I15: a sealed holdout label. Server-only; never released, prompted or exposed to agents.';

revoke select on public.gold_labels from authenticated;
grant select (
    id, submission_id, lab_name, method, property, value, unit, uncertainty,
    depth_top_cm, depth_bottom_cm, verified_by, document_ref
) on public.gold_labels to authenticated;
