select 'auth.audit_log_entries' as table_name,count(*)::bigint as row_count from "auth"."audit_log_entries"
union all
select 'auth.custom_oauth_providers' as table_name,count(*)::bigint as row_count from "auth"."custom_oauth_providers"
union all
select 'auth.flow_state' as table_name,count(*)::bigint as row_count from "auth"."flow_state"
union all
select 'auth.identities' as table_name,count(*)::bigint as row_count from "auth"."identities"
union all
select 'auth.instances' as table_name,count(*)::bigint as row_count from "auth"."instances"
union all
select 'auth.mfa_amr_claims' as table_name,count(*)::bigint as row_count from "auth"."mfa_amr_claims"
union all
select 'auth.mfa_challenges' as table_name,count(*)::bigint as row_count from "auth"."mfa_challenges"
union all
select 'auth.mfa_factors' as table_name,count(*)::bigint as row_count from "auth"."mfa_factors"
union all
select 'auth.mfa_recovery_code_sets' as table_name,count(*)::bigint as row_count from "auth"."mfa_recovery_code_sets"
union all
select 'auth.mfa_recovery_codes' as table_name,count(*)::bigint as row_count from "auth"."mfa_recovery_codes"
union all
select 'auth.oauth_authorizations' as table_name,count(*)::bigint as row_count from "auth"."oauth_authorizations"
union all
select 'auth.oauth_client_states' as table_name,count(*)::bigint as row_count from "auth"."oauth_client_states"
union all
select 'auth.oauth_clients' as table_name,count(*)::bigint as row_count from "auth"."oauth_clients"
union all
select 'auth.oauth_consents' as table_name,count(*)::bigint as row_count from "auth"."oauth_consents"
union all
select 'auth.one_time_tokens' as table_name,count(*)::bigint as row_count from "auth"."one_time_tokens"
union all
select 'auth.refresh_tokens' as table_name,count(*)::bigint as row_count from "auth"."refresh_tokens"
union all
select 'auth.saml_providers' as table_name,count(*)::bigint as row_count from "auth"."saml_providers"
union all
select 'auth.saml_relay_states' as table_name,count(*)::bigint as row_count from "auth"."saml_relay_states"
union all
select 'auth.schema_migrations' as table_name,count(*)::bigint as row_count from "auth"."schema_migrations"
union all
select 'auth.scim_tokens' as table_name,count(*)::bigint as row_count from "auth"."scim_tokens"
union all
select 'auth.scim_users' as table_name,count(*)::bigint as row_count from "auth"."scim_users"
union all
select 'auth.sessions' as table_name,count(*)::bigint as row_count from "auth"."sessions"
union all
select 'auth.sso_domains' as table_name,count(*)::bigint as row_count from "auth"."sso_domains"
union all
select 'auth.sso_providers' as table_name,count(*)::bigint as row_count from "auth"."sso_providers"
union all
select 'auth.users' as table_name,count(*)::bigint as row_count from "auth"."users"
union all
select 'auth.webauthn_challenges' as table_name,count(*)::bigint as row_count from "auth"."webauthn_challenges"
union all
select 'auth.webauthn_credentials' as table_name,count(*)::bigint as row_count from "auth"."webauthn_credentials"
union all
select 'extensions.spatial_ref_sys' as table_name,count(*)::bigint as row_count from "extensions"."spatial_ref_sys"
union all
select 'public.actors' as table_name,count(*)::bigint as row_count from "public"."actors"
union all
select 'public.attribution_reviews' as table_name,count(*)::bigint as row_count from "public"."attribution_reviews"
union all
select 'public.contribution_grants' as table_name,count(*)::bigint as row_count from "public"."contribution_grants"
union all
select 'public.contributors' as table_name,count(*)::bigint as row_count from "public"."contributors"
union all
select 'public.dataset_releases' as table_name,count(*)::bigint as row_count from "public"."dataset_releases"
union all
select 'public.deletion_requests' as table_name,count(*)::bigint as row_count from "public"."deletion_requests"
union all
select 'public.gold_labels' as table_name,count(*)::bigint as row_count from "public"."gold_labels"
union all
select 'public.grant_withdrawals' as table_name,count(*)::bigint as row_count from "public"."grant_withdrawals"
union all
select 'public.h3_cells' as table_name,count(*)::bigint as row_count from "public"."h3_cells"
union all
select 'public.photos' as table_name,count(*)::bigint as row_count from "public"."photos"
union all
select 'public.predictions' as table_name,count(*)::bigint as row_count from "public"."predictions"
union all
select 'public.prior_cell_cache' as table_name,count(*)::bigint as row_count from "public"."prior_cell_cache"
union all
select 'public.prior_jobs' as table_name,count(*)::bigint as row_count from "public"."prior_jobs"
union all
select 'public.priors' as table_name,count(*)::bigint as row_count from "public"."priors"
union all
select 'public.qa_events' as table_name,count(*)::bigint as row_count from "public"."qa_events"
union all
select 'public.qa_jobs' as table_name,count(*)::bigint as row_count from "public"."qa_jobs"
union all
select 'public.service_state' as table_name,count(*)::bigint as row_count from "public"."service_state"
union all
select 'public.submissions' as table_name,count(*)::bigint as row_count from "public"."submissions"
union all
select 'public.terms_versions' as table_name,count(*)::bigint as row_count from "public"."terms_versions"
union all
select 'public.upstream_buckets' as table_name,count(*)::bigint as row_count from "public"."upstream_buckets"
union all
select 'realtime.messages' as table_name,count(*)::bigint as row_count from "realtime"."messages"
union all
select 'realtime.schema_migrations' as table_name,count(*)::bigint as row_count from "realtime"."schema_migrations"
union all
select 'realtime.subscription' as table_name,count(*)::bigint as row_count from "realtime"."subscription"
union all
select 'storage.buckets' as table_name,count(*)::bigint as row_count from "storage"."buckets"
union all
select 'storage.buckets_analytics' as table_name,count(*)::bigint as row_count from "storage"."buckets_analytics"
union all
select 'storage.buckets_vectors' as table_name,count(*)::bigint as row_count from "storage"."buckets_vectors"
union all
select 'storage.migrations' as table_name,count(*)::bigint as row_count from "storage"."migrations"
union all
select 'storage.objects' as table_name,count(*)::bigint as row_count from "storage"."objects"
union all
select 'storage.s3_multipart_uploads' as table_name,count(*)::bigint as row_count from "storage"."s3_multipart_uploads"
union all
select 'storage.s3_multipart_uploads_parts' as table_name,count(*)::bigint as row_count from "storage"."s3_multipart_uploads_parts"
union all
select 'storage.vector_indexes' as table_name,count(*)::bigint as row_count from "storage"."vector_indexes"
union all
select 'supabase_migrations.schema_migrations' as table_name,count(*)::bigint as row_count from "supabase_migrations"."schema_migrations"
union all
select 'vault.secrets' as table_name,count(*)::bigint as row_count from "vault"."secrets"
order by table_name;
