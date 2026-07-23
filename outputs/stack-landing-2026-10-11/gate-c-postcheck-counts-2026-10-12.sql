-- LOCAL PREPARED READ-ONLY POST-GATE-C QUERIES; NOT EXECUTED BY PREPARER.
-- Target toxldjgwkxtneoqsazym; reviewed operational source f9e1ac2.
-- Return only counts, booleans, or migration identity metadata. No contents, IDs, coordinates, or SQL bodies.
-- Do not invoke settlement, refresh, rights, prior-attempt, or other mutation RPCs.

select table_name, row_count from (
select 'auth.audit_log_entries'::text as table_name, count(*)::bigint as row_count from auth.audit_log_entries
union all
select 'auth.custom_oauth_providers'::text as table_name, count(*)::bigint as row_count from auth.custom_oauth_providers
union all
select 'auth.flow_state'::text as table_name, count(*)::bigint as row_count from auth.flow_state
union all
select 'auth.identities'::text as table_name, count(*)::bigint as row_count from auth.identities
union all
select 'auth.instances'::text as table_name, count(*)::bigint as row_count from auth.instances
union all
select 'auth.mfa_amr_claims'::text as table_name, count(*)::bigint as row_count from auth.mfa_amr_claims
union all
select 'auth.mfa_challenges'::text as table_name, count(*)::bigint as row_count from auth.mfa_challenges
union all
select 'auth.mfa_factors'::text as table_name, count(*)::bigint as row_count from auth.mfa_factors
union all
select 'auth.mfa_recovery_code_sets'::text as table_name, count(*)::bigint as row_count from auth.mfa_recovery_code_sets
union all
select 'auth.mfa_recovery_codes'::text as table_name, count(*)::bigint as row_count from auth.mfa_recovery_codes
union all
select 'auth.oauth_authorizations'::text as table_name, count(*)::bigint as row_count from auth.oauth_authorizations
union all
select 'auth.oauth_client_states'::text as table_name, count(*)::bigint as row_count from auth.oauth_client_states
union all
select 'auth.oauth_clients'::text as table_name, count(*)::bigint as row_count from auth.oauth_clients
union all
select 'auth.oauth_consents'::text as table_name, count(*)::bigint as row_count from auth.oauth_consents
union all
select 'auth.one_time_tokens'::text as table_name, count(*)::bigint as row_count from auth.one_time_tokens
union all
select 'auth.refresh_tokens'::text as table_name, count(*)::bigint as row_count from auth.refresh_tokens
union all
select 'auth.saml_providers'::text as table_name, count(*)::bigint as row_count from auth.saml_providers
union all
select 'auth.saml_relay_states'::text as table_name, count(*)::bigint as row_count from auth.saml_relay_states
union all
select 'auth.schema_migrations'::text as table_name, count(*)::bigint as row_count from auth.schema_migrations
union all
select 'auth.scim_tokens'::text as table_name, count(*)::bigint as row_count from auth.scim_tokens
union all
select 'auth.scim_users'::text as table_name, count(*)::bigint as row_count from auth.scim_users
union all
select 'auth.sessions'::text as table_name, count(*)::bigint as row_count from auth.sessions
union all
select 'auth.sso_domains'::text as table_name, count(*)::bigint as row_count from auth.sso_domains
union all
select 'auth.sso_providers'::text as table_name, count(*)::bigint as row_count from auth.sso_providers
union all
select 'auth.users'::text as table_name, count(*)::bigint as row_count from auth.users
union all
select 'auth.webauthn_challenges'::text as table_name, count(*)::bigint as row_count from auth.webauthn_challenges
union all
select 'auth.webauthn_credentials'::text as table_name, count(*)::bigint as row_count from auth.webauthn_credentials
union all
select 'extensions.spatial_ref_sys'::text as table_name, count(*)::bigint as row_count from extensions.spatial_ref_sys
union all
select 'public.actors'::text as table_name, count(*)::bigint as row_count from public.actors
union all
select 'public.attribution_reviews'::text as table_name, count(*)::bigint as row_count from public.attribution_reviews
union all
select 'public.contribution_grants'::text as table_name, count(*)::bigint as row_count from public.contribution_grants
union all
select 'public.contributors'::text as table_name, count(*)::bigint as row_count from public.contributors
union all
select 'public.dataset_releases'::text as table_name, count(*)::bigint as row_count from public.dataset_releases
union all
select 'public.deletion_requests'::text as table_name, count(*)::bigint as row_count from public.deletion_requests
union all
select 'public.gold_labels'::text as table_name, count(*)::bigint as row_count from public.gold_labels
union all
select 'public.grant_withdrawals'::text as table_name, count(*)::bigint as row_count from public.grant_withdrawals
union all
select 'public.h3_cells'::text as table_name, count(*)::bigint as row_count from public.h3_cells
union all
select 'public.photos'::text as table_name, count(*)::bigint as row_count from public.photos
union all
select 'public.predictions'::text as table_name, count(*)::bigint as row_count from public.predictions
union all
select 'public.prior_cell_cache'::text as table_name, count(*)::bigint as row_count from public.prior_cell_cache
union all
select 'public.prior_jobs'::text as table_name, count(*)::bigint as row_count from public.prior_jobs
union all
select 'public.priors'::text as table_name, count(*)::bigint as row_count from public.priors
union all
select 'public.qa_events'::text as table_name, count(*)::bigint as row_count from public.qa_events
union all
select 'public.qa_jobs'::text as table_name, count(*)::bigint as row_count from public.qa_jobs
union all
select 'public.service_state'::text as table_name, count(*)::bigint as row_count from public.service_state
union all
select 'public.submissions'::text as table_name, count(*)::bigint as row_count from public.submissions
union all
select 'public.terms_versions'::text as table_name, count(*)::bigint as row_count from public.terms_versions
union all
select 'public.upstream_buckets'::text as table_name, count(*)::bigint as row_count from public.upstream_buckets
union all
select 'realtime.messages'::text as table_name, count(*)::bigint as row_count from realtime.messages
union all
select 'realtime.schema_migrations'::text as table_name, count(*)::bigint as row_count from realtime.schema_migrations
union all
select 'realtime.subscription'::text as table_name, count(*)::bigint as row_count from realtime.subscription
union all
select 'storage.buckets'::text as table_name, count(*)::bigint as row_count from storage.buckets
union all
select 'storage.buckets_analytics'::text as table_name, count(*)::bigint as row_count from storage.buckets_analytics
union all
select 'storage.buckets_vectors'::text as table_name, count(*)::bigint as row_count from storage.buckets_vectors
union all
select 'storage.migrations'::text as table_name, count(*)::bigint as row_count from storage.migrations
union all
select 'storage.objects'::text as table_name, count(*)::bigint as row_count from storage.objects
union all
select 'storage.s3_multipart_uploads'::text as table_name, count(*)::bigint as row_count from storage.s3_multipart_uploads
union all
select 'storage.s3_multipart_uploads_parts'::text as table_name, count(*)::bigint as row_count from storage.s3_multipart_uploads_parts
union all
select 'storage.vector_indexes'::text as table_name, count(*)::bigint as row_count from storage.vector_indexes
union all
select 'supabase_migrations.schema_migrations'::text as table_name, count(*)::bigint as row_count from supabase_migrations.schema_migrations
union all
select 'vault.secrets'::text as table_name, count(*)::bigint as row_count from vault.secrets
) totals order by table_name;
