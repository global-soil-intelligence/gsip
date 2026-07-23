# Gate D — exact two-migration plan

Prepared for Justin's go. **Not executed.** Target `toxldjgwkxtneoqsazym` (gsip, us-east-1); CLI 2.118.0. Candidate source `19e626c8a95fae32dbd8ad0ff96bc96aba541a0f`; runbook #40 at `f5c6967a7df3f85a677bd195eff6667bc80a7162`.

Production remains at26 migrations with capture false and seven security findings. Fresh61 counts,26 ledger hashes and catalogs match the post-C baseline. Counts:5 contributors,25 submissions,25 photos,0 auth users,0 public cells. No application migration or other production change ran during preparation. The CLI dry run named exactly the two files below; its read-only preflight may initialize the temporary database login role.

| Order | Migration | SHA-256 | Effect |
| --- | --- | --- | --- |
| 1 | `20261012141828_wp6b_invoker_boundary.sql` | `afe4f698989729bd456fe763582f93042f58bf66a271704cdaa1c556eeb124d6` | Capture reads its existing column permission; guarded finalization stays private behind the unchanged public invoker signature. |
| 2 | `20261012142348_wp6d_private_rights_boundary.sql` | `27c0b1ae001351358b6a56490bc1389d1075dd62cbd6ffc4e6250943fa507260` | Guarded rights helpers stay private behind unchanged public invoker signatures; two service-only tables gain restrictive deny-all policies. |

Exact command, **only after Justin's separate go**:

```sh
GSIP_DEPLOY_SOURCE="/Users/justinhart/.codex/worktrees/gsip-coding-guidance/GSIP 2.0"
GSIP_CLI="/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/repo/node_modules/.bin/supabase"
"$GSIP_CLI" db push --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_DEPLOY_SOURCE" --skip-vault
```

Before execution, refresh source cleanliness/hash, production metadata/counts/history/security, closed capture/auth, private-schema exposure/default privileges and absence of overlapping writers. Stop on any mismatch. Apply once, no automatic retry or rollback. Read back exact ledger28 preserving all26 complete record hashes; full hosted advisor0; strict target28 catalog/ACLs/owners; unchanged61 counts except ledger+2; capturefalse; sign-up/anonymousoff; existing backfill and k-anonymity checks; private still unexposed; anonymous capture RPCfalse. No extra SQL for cache reload is included: if dispatch is stale, stop for a separate plan.

Source proofs passed299/299 pgTAP,13/13 migration assertions and33/33 independent local HTTP checks;13 new assertions fail before the fixes. Fresh28 and seeded26+2 catalogs/counts match. All26 previously deployed SQL files, existing public function caller ACLs, table/column/schema/storage grants and guarded business logic remain unchanged. The only new private EXECUTE privileges are the narrow dispatcher permissions for already-authorized public callers. Source specification was committed first. The three relevant official rules produce7→0 locally; hosted0 is still a post-migration requirement.

All13 PRs have fresh current-head green checks. APK and simulator artifacts exist for the new #34 and #39 runs. Whole-stack Gitleaks8.21.2 reports0 leaks using exactly the three approved historical entries; detector rules, redaction and full-history scanning remain intact.

Assumptions: verified postgres owner/defaults and private-schema exclusion remain unchanged; no concurrent writer; hosted PostgreSQL17 supports bound SQL-standard bodies (tested local17/CI16). Disposable stand-ins and loopback HTTP are not hosted security proof. This gate authorizes only these two migrations when Justin says go; no merges/approvals, capture/auth changes, function deployments, workers, exports or publication.
