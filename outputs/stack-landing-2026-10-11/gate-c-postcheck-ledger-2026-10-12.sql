-- LOCAL PREPARED READ-ONLY POST-GATE-C QUERIES; NOT EXECUTED BY PREPARER.
-- Target toxldjgwkxtneoqsazym; reviewed operational source f9e1ac2.
-- Return only counts, booleans, or migration identity metadata. No contents, IDs, coordinates, or SQL bodies.
-- Do not invoke settlement, refresh, rights, prior-attempt, or other mutation RPCs.

with expected(version, name) as (values
    ('20260722164727', 'wp1_extensions'),
    ('20260722164749', 'wp1_schema'),
    ('20260722164806', 'wp1_rls'),
    ('20260722170020', 'wp1_review_hardening'),
    ('20260722181500', 'wp1_v22_privacy_and_grants'),
    ('20260722183000', 'wp1_performance_indexes'),
    ('20260722190000', 'wp4_prior_jobs'),
    ('20260722190500', 'wp4_prior_jobs_hardening'),
    ('20260722193000', 'wp4b_photo_qa'),
    ('20260722200000', 'wp6_export_guardrails'),
    ('20260723002255', 'phase1_actor_hardening'),
    ('20260723004439', 'qa_event_provenance'),
    ('20260723005752', 'public_h3_aggregates'),
    ('20260723010313', 'atomic_public_h3_refresh'),
    ('20260723044745', 'atomic_prior_attempt_claim'),
    ('20260723045317', 'document_authenticated_h3_role'),
    ('20260723045606', 'remove_public_submission_residue'),
    ('20261010120000', 'wp6b_capture_gate'),
    ('20261010120100', 'wp6b_path_binding'),
    ('20261010120200', 'wp6b_finalize_and_settle'),
    ('20261010120300', 'wp6b_k_anonymous_cells'),
    ('20261010120400', 'wp6b_attribution_and_metadata'),
    ('20261010130000', 'wp6c_priors'),
    ('20261010140000', 'wp6d_contributor_rights'),
    ('20261010150000', 'wp6e_provenance'),
    ('20261011090000', 'wp_agent1_releases')), actual as (
    select version, name from supabase_migrations.schema_migrations
), unexpected as (
    select version, name from actual except select version, name from expected
), missing as (
    select version, name from expected except select version, name from actual
)
select json_build_object(
    'actual_identity_count', (select count(*) from actual),
    'expected_identity_count', (select count(*) from expected),
    'unexpected_identity_count', (select count(*) from unexpected),
    'missing_identity_count', (select count(*) from missing),
    'duplicate_version_count', (select count(*) from (select version from actual group by version having count(*) <> 1) duplicates)
) as ledger_identity_counts;
