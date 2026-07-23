# Production table counts before reconciliation

Target: toxldjgwkxtneoqsazym (gsip, us-east-1). Observed: 2026-10-12 02:37:04 UTC.

Counts only; no row contents or seed-provenance classification. No repair, migration, deletion or deployment has run.

| Table | Rows |
| --- | ---: |
| auth.audit_log_entries | 0 |
| auth.custom_oauth_providers | 0 |
| auth.flow_state | 0 |
| auth.identities | 0 |
| auth.instances | 0 |
| auth.mfa_amr_claims | 0 |
| auth.mfa_challenges | 0 |
| auth.mfa_factors | 0 |
| auth.mfa_recovery_code_sets | 0 |
| auth.mfa_recovery_codes | 0 |
| auth.oauth_authorizations | 0 |
| auth.oauth_client_states | 0 |
| auth.oauth_clients | 0 |
| auth.oauth_consents | 0 |
| auth.one_time_tokens | 0 |
| auth.refresh_tokens | 0 |
| auth.saml_providers | 0 |
| auth.saml_relay_states | 0 |
| auth.schema_migrations | 82 |
| auth.scim_tokens | 0 |
| auth.scim_users | 0 |
| auth.sessions | 0 |
| auth.sso_domains | 0 |
| auth.sso_providers | 0 |
| auth.users | 0 |
| auth.webauthn_challenges | 0 |
| auth.webauthn_credentials | 0 |
| extensions.spatial_ref_sys | 8500 |
| public.contribution_grants | 5 |
| public.contributors | 5 |
| public.gold_labels | 0 |
| public.h3_cells | 0 |
| public.photos | 25 |
| public.predictions | 0 |
| public.prior_jobs | 25 |
| public.priors | 0 |
| public.qa_events | 0 |
| public.qa_jobs | 25 |
| public.submissions | 25 |
| realtime.messages | 0 |
| realtime.schema_migrations | 81 |
| realtime.subscription | 0 |
| storage.buckets | 2 |
| storage.buckets_analytics | 0 |
| storage.buckets_vectors | 0 |
| storage.migrations | 73 |
| storage.objects | 0 |
| storage.s3_multipart_uploads | 0 |
| storage.s3_multipart_uploads_parts | 0 |
| storage.vector_indexes | 0 |
| supabase_migrations.schema_migrations | 18 |
| vault.secrets | 0 |

Source receipt: production-preapproval-refresh.json, SHA-256 fed89943b3e3e6f1366707234b95e270ad44ee3acef83c765a1f51bb52d5bc2c. All counts and table identities match the earlier bound readback.
