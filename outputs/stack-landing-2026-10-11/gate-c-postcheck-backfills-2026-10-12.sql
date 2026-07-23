-- LOCAL PREPARED READ-ONLY POST-GATE-C QUERIES; NOT EXECUTED BY PREPARER.
-- Target toxldjgwkxtneoqsazym; reviewed operational source f9e1ac2.
-- Return only counts, booleans, or migration identity metadata. No contents, IDs, coordinates, or SQL bodies.
-- Do not invoke settlement, refresh, rights, prior-attempt, or other mutation RPCs.


-- Every anomaly below must be 0. Snapshot is valid only while no worker/writer overlaps.
select 'capture_rows' as check_name, count(*)::bigint as result from public.service_state
union all select 'capture_open_rows', count(*) from public.service_state where capture_open
union all select 'human_actor_missing_or_duplicated', count(*) from public.contributors c
    where (select count(*) from public.actors a where a.kind = 'human' and a.contributor_id = c.id) <> 1
union all select 'actor_backfill_status_mismatch', count(*) from public.actors a join public.contributors c on c.id = a.contributor_id
    where a.kind <> 'human' or a.operator_id is not null
       or a.status is distinct from case when c.auth_uid is null then 'revoked' else 'active' end
union all select 'unexpected_actor_kind_or_orphan', count(*) from public.actors a
    where a.kind <> 'human' or not exists(select 1 from public.contributors c where c.id = a.contributor_id)
union all select 'submission_actor_binding_mismatch', count(*) from public.submissions s left join public.actors a on a.id = s.actor_id
    where a.id is null or a.kind <> 'human' or a.contributor_id is distinct from s.contributor_id
union all select 'submission_tier_backfill_mismatch', count(*) from public.submissions s
    where s.provenance_tier is distinct from case when s.is_synthetic then -1 else 0 end
union all select 'submission_legacy_claim_mismatch', count(*) from public.submissions s
    where s.ingest_path <> 'web' or s.capture_method <> 'unknown' or s.location_source <> 'unknown' or s.client_version is not null
union all select 'photo_tier_backfill_mismatch', count(*) from public.photos p join public.submissions s on s.id = p.submission_id
    where p.provenance_tier is distinct from case when s.is_synthetic then -1 else 0 end
union all select 'legacy_photo_evidence_nonnull', count(*) from public.photos where capture_evidence_private is not null
union all select 'legacy_grant_receipt_nonnull', count(*) from public.contribution_grants where received_at is not null
union all select 'legacy_grant_terms_missing', count(*) from public.contribution_grants g
    where not exists(select 1 from public.terms_versions t where t.version = g.terms_version)
union all select 'terms_active_version_mismatch', count(*) from public.terms_versions
    where (version = '2026-07-22-v1') is distinct from (retired_at is null)
union all select 'terms_count_mismatch', abs((select count(*) from public.terms_versions) -
    (1 + (select count(distinct terms_version) from public.contribution_grants where terms_version <> '2026-07-22-v1')))
union all select 'prior_empty_sources_nonempty', count(*) from public.prior_jobs where cardinality(empty_sources) <> 0
union all select 'legacy_holdout_true', count(*) from public.gold_labels where holdout
union all select 'public_cells_k_anonymity_violations', count(*) from public.h3_cells
    where resolution is null or resolution not in (4, 6, 8) or n_contributors is null or n_contributors < 3
       or n_submissions is null or n_submissions < n_contributors
       or h3_index is null or h3_index !~ ('^8' || to_hex(resolution::integer) || '[0-9a-f]{13}$')
union all select 'public_base_tables_without_rls', count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity;

-- Counts only; compare the synthetic total to a fresh pre-C aggregate, never recategorize flags.
select count(*) as submission_count,
       count(*) filter (where is_synthetic) as synthetic_count,
       count(*) filter (where not is_synthetic) as nonsynthetic_count
from public.submissions;

-- One capture row, false helper, 20 public base tables, zero old claim RPC, one new begin RPC.
select public.capture_is_open() as capture_is_open,
       (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'public' and c.relkind = 'r') as public_base_table_count,
       (select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace where n.nspname = 'public' and p.proname = 'claim_prior_job_attempt') as obsolete_prior_claim_rpc_count,
       (select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace where n.nspname = 'public' and p.proname = 'begin_prior_attempt') as atomic_prior_begin_rpc_count;

-- Complete A/B sets match finalization; optional C cannot affect settlement.
with required as (
    select s.id, s.finalized_at,
           count(distinct p.shot_type) filter (where p.shot_type in ('A', 'B')) as required_shot_count
    from public.submissions s left join public.photos p on p.submission_id = s.id
    group by s.id, s.finalized_at
)
select count(*) filter (where required_shot_count = 2) as complete_ab_count,
       count(*) filter (where finalized_at is not null) as finalized_count,
       count(*) filter (where (required_shot_count = 2) is distinct from (finalized_at is not null)) as finalization_mismatch_count
from required;

-- Re-derive expected photo QA verdicts through SELECT only; completed jobs take precedence.
with expected as (
    select p.qa_status,
        case when exists(select 1 from public.qa_jobs j where j.photo_id = p.id and j.status = 'completed') then
            case when exists(select 1 from public.qa_events e where e.submission_id = p.submission_id and not e.passed and e.check_name in ('sharpness_' || p.shot_type, 'exposure_' || p.shot_type, 'is_soil_' || p.shot_type)) then 'fail'
                 when exists(select 1 from public.qa_events e where e.submission_id = p.submission_id and not e.passed and e.check_name in ('gps_plausibility_' || p.shot_type, 'duplicate_' || p.shot_type)) then 'flagged'
                 else 'pass' end
             when exists(select 1 from public.qa_jobs j where j.photo_id = p.id and j.status = 'dead_letter') then 'error'
             else null end as expected_status
    from public.photos p
)
select count(*) as photo_count, count(*) filter (where qa_status is distinct from expected_status) as qa_backfill_mismatch_count from expected;

-- Re-derive the reviewed status table without invoking any settlement function or outputting H3 cells.
with required as (
    select s.status, s.finalized_at, (s.h3_r8 is not null and s.h3_r6 is not null) as has_cells,
           max(p.qa_status) filter (where p.shot_type = 'A') as shot_a,
           max(p.qa_status) filter (where p.shot_type = 'B') as shot_b
    from public.submissions s left join public.photos p on p.submission_id = s.id
    group by s.id, s.status, s.finalized_at, s.h3_r8, s.h3_r6
), expected as (
    select status, case when finalized_at is null then 'pending'
                       when shot_a is null or shot_b is null then 'pending'
                       when shot_a = 'fail' or shot_b = 'fail' then 'qa_fail'
                       when shot_a in ('flagged', 'error') or shot_b in ('flagged', 'error') then 'flagged'
                       when not has_cells then 'pending'
                       else 'qa_pass' end as expected_status
    from required
)
select count(*) as submission_count, count(*) filter (where status is distinct from expected_status) as settlement_mismatch_count from expected;
