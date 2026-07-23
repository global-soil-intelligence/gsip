-- Read-only aggregate post-C backfill verification; toxldjgwkxtneoqsazym, f9e1ac2. No private row fields returned.
with required as (
    select s.id, s.status, s.finalized_at, (s.h3_r8 is not null and s.h3_r6 is not null) as has_cells,
           count(distinct p.shot_type) filter (where p.shot_type in ('A', 'B')) as required_shot_count,
           max(p.qa_status) filter (where p.shot_type = 'A') as shot_a,
           max(p.qa_status) filter (where p.shot_type = 'B') as shot_b
    from public.submissions s left join public.photos p on p.submission_id = s.id
    group by s.id, s.status, s.finalized_at, s.h3_r8, s.h3_r6
), expected_status as (
    select status, case when finalized_at is null then 'pending'
                       when shot_a is null or shot_b is null then 'pending'
                       when shot_a = 'fail' or shot_b = 'fail' then 'qa_fail'
                       when shot_a in ('flagged', 'error') or shot_b in ('flagged', 'error') then 'flagged'
                       when not has_cells then 'pending'
                       else 'qa_pass' end as expected_status
    from required
), expected_photo_qa as (
    select p.qa_status,
        case when exists(select 1 from public.qa_jobs j where j.photo_id = p.id and j.status = 'completed') then
            case when exists(select 1 from public.qa_events e where e.submission_id = p.submission_id and not e.passed and e.check_name in ('sharpness_' || p.shot_type, 'exposure_' || p.shot_type, 'is_soil_' || p.shot_type)) then 'fail'
                 when exists(select 1 from public.qa_events e where e.submission_id = p.submission_id and not e.passed and e.check_name in ('gps_plausibility_' || p.shot_type, 'duplicate_' || p.shot_type)) then 'flagged'
                 else 'pass' end
             when exists(select 1 from public.qa_jobs j where j.photo_id = p.id and j.status = 'dead_letter') then 'error'
             else null end as expected_status
    from public.photos p
)
select jsonb_build_object(
    'contributor_count', (select count(*) from public.contributors),
    'actor_count', (select count(*) from public.actors),
    'human_actor_missing_or_duplicated_count', (select count(*) from public.contributors c where (select count(*) from public.actors a where a.kind = 'human' and a.contributor_id = c.id) <> 1),
    'actor_backfill_status_mismatch_count', (select count(*) from public.actors a join public.contributors c on c.id = a.contributor_id where a.kind <> 'human' or a.operator_id is not null or a.status is distinct from case when c.auth_uid is null then 'revoked' else 'active' end),
    'unexpected_actor_kind_or_orphan_count', (select count(*) from public.actors a where a.kind <> 'human' or not exists(select 1 from public.contributors c where c.id = a.contributor_id)),
    'submission_count', (select count(*) from public.submissions),
    'submission_actor_binding_mismatch_count', (select count(*) from public.submissions s left join public.actors a on a.id = s.actor_id where a.id is null or a.kind <> 'human' or a.contributor_id is distinct from s.contributor_id),
    'submission_tier_backfill_mismatch_count', (select count(*) from public.submissions s where s.provenance_tier is distinct from case when s.is_synthetic then -1 else 0 end),
    'submission_legacy_claim_mismatch_count', (select count(*) from public.submissions s where s.ingest_path <> 'web' or s.capture_method <> 'unknown' or s.location_source <> 'unknown' or s.client_version is not null),
    'synthetic_submission_count', (select count(*) from public.submissions where is_synthetic),
    'nonsynthetic_submission_count', (select count(*) from public.submissions where not is_synthetic),
    'invented_submission_tier_one_or_higher_count', (select count(*) from public.submissions where provenance_tier >= 1),
    'photo_count', (select count(*) from public.photos),
    'photo_tier_backfill_mismatch_count', (select count(*) from public.photos p join public.submissions s on s.id = p.submission_id where p.provenance_tier is distinct from case when s.is_synthetic then -1 else 0 end),
    'legacy_photo_evidence_nonnull_count', (select count(*) from public.photos where capture_evidence_private is not null),
    'grant_count', (select count(*) from public.contribution_grants),
    'legacy_grant_receipt_nonnull_count', (select count(*) from public.contribution_grants where received_at is not null),
    'legacy_grant_terms_missing_count', (select count(*) from public.contribution_grants g where not exists(select 1 from public.terms_versions t where t.version = g.terms_version)),
    'terms_total_count', (select count(*) from public.terms_versions),
    'terms_expected_count', (select 1 + count(distinct terms_version) from public.contribution_grants where terms_version <> '2026-07-22-v1'),
    'terms_july_published_unretired_count', (select count(*) from public.terms_versions where version = '2026-07-22-v1' and published_at <= now() and retired_at is null),
    'terms_other_retired_count', (select count(*) from public.terms_versions where version <> '2026-07-22-v1' and retired_at is not null),
    'terms_active_version_mismatch_count', (select count(*) from public.terms_versions where (version = '2026-07-22-v1') is distinct from (retired_at is null)),
    'gold_label_count', (select count(*) from public.gold_labels),
    'legacy_holdout_true_count', (select count(*) from public.gold_labels where holdout),
    'complete_ab_count', (select count(*) from required where required_shot_count = 2),
    'finalized_count', (select count(*) from required where finalized_at is not null),
    'finalization_mismatch_count', (select count(*) from required where (required_shot_count = 2) is distinct from (finalized_at is not null)),
    'photo_qa_backfill_mismatch_count', (select count(*) from expected_photo_qa where qa_status is distinct from expected_status),
    'settlement_mismatch_count', (select count(*) from expected_status where status is distinct from expected_status)
) as aggregate_backfill_counts;
