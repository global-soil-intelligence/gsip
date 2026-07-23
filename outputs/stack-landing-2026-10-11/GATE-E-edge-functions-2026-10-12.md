# Gate E — prior-attach and gsip-public

**Prepared only. Waiting for Justin’s separate go. No deployment, merge or capture opening has run.**

Target: **gsip — toxldjgwkxtneoqsazym, us-east-1**. Exact clean source: `19e626c8a95fae32dbd8ad0ff96bc96aba541a0f`. Supabase CLI: **2.118.0**, unchanged. This gate covers two named functions in sequence, with verification between them.

## Invariants and scope

Ledger stays 28, all existing full-record hashes, catalogs, public/private grants and all 61 table counts stay unchanged. Hosted security findings stay zero. Capture, new-user sign-up and anonymous sign-in stay off. Private schemas stay unexposed, and workers stay held. `prior-attach` retains JWT verification **on**; `gsip-public` uses JWT verification **off** and reads only as the anonymous role through its publishable key. No runtime user session or service-role key is used by the public API.

Preparation readbacks: only prior-attach v3 ACTIVE/JWT on exists; gsip-public is absent. Ledger28/security0/captureclosed; contributors5/submissions25/photos25/authusers0/publiccells0/datasetreleases0. All13PRs remain open and green at their current heads. Actual current-head CI Deno step is successful. Local Deno is unavailable. No dependency, licence or source change is included.

## Refresh before execution

After go, require exact source/head/clean status and every frozen manifest hash; CLI version unchanged; current green CI; fresh exact28 ledger hashes, strict target28 metadata/complete ACLs, all61 counts and fulladvisor0; closed capture/Auth and private excluded; disabled prior/QA/export schedules/no active writer. Function inventory must still equal the single prior-attach v3 baseline. Stop on any mismatch. The platform’s standard function environment must remain available; do not retrieve or print any secret.

## Exact commands after go only

```sh
GSIP_EDGE_SOURCE="/Users/justinhart/.codex/worktrees/gsip-coding-guidance/GSIP 2.0"
GSIP_CLI="/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/repo/node_modules/.bin/supabase"
GSIP_EDGE_SMOKE="/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/gate-e-edge-smoke-2026-10-12.py"
```

**1. Deploy prior-attach once:**

```sh
"$GSIP_CLI" functions deploy prior-attach \
  --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_EDGE_SOURCE" \
  --import-map "$GSIP_EDGE_SOURCE/supabase/functions/deno.json" --use-api
```

JWT stays on via the hash-pinned `[functions.prior-attach] verify_jwt = true`. The negative JWT flag is absent from this command. Read back after this command, before deploying public:

```sh
"$GSIP_CLI" functions list --project-ref toxldjgwkxtneoqsazym \
  --workdir "$GSIP_EDGE_SOURCE" --output json
python3 "$GSIP_EDGE_SMOKE" --phase prior
```

Require only prior-attach, same function id, ACTIVE, a new version greater than3, JWTtrue and importmaptrue. Record its bundle hash and safe command output. The anonymous empty POST must be401. Refresh database invariants; any mismatch stops before step2. A401 alone cannot prove gateway JWT enforcement, so the metadata check is required.

**2. Deploy gsip-public once, only if step1 verifies:**

```sh
"$GSIP_CLI" functions deploy gsip-public \
  --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_EDGE_SOURCE" \
  --import-map "$GSIP_EDGE_SOURCE/supabase/functions/deno.json" --use-api --no-verify-jwt
```

JWT is explicitly off by the flag and the matching hash-pinned function configuration. `--use-api` bundles on Supabase; it needs no local Docker bundler. No deploy command was invoked during preparation: this CLI has no deployment dry-run flag.

**3. Read back and run all anonymous smoke checks:**

```sh
"$GSIP_CLI" functions list --project-ref toxldjgwkxtneoqsazym \
  --workdir "$GSIP_EDGE_SOURCE" --output json
python3 "$GSIP_EDGE_SMOKE" --phase all
```

Require exactly two ACTIVE function slugs: prior-attach JWTtrue and gsip-public JWTfalse, both importmaptrue. Prior complete metadata must equal step1’s readback; record public’s positive version and bundle digest.

## Smoke contracts

Public base: `https://toxldjgwkxtneoqsazym.supabase.co/functions/v1/gsip-public`. Every request is anonymous, uses no key/user session/cookie, uses fixed synthetic H3 fixtures already used by the runbook, has bounded response size and a30second timeout, rejects redirects, and prints only check names/status/body hashes. No raw body, private record or location is printed.

| Check | Required result |
| --- | --- |
| prior-attach empty anonymous POST | 401; no submission id/job |
| GET /v1/protocol | 200, nonempty protocol, exact licence fields and citation text/BibTeX |
| GET /v1/cells/892a8ab5863ffff (synthetic resolution9) | 400, resolution8 limit refusal |
| POST /mcp tools/list | 200; exactly4 tools, all read-only and nondestructive |
| GET synthetic resolution8 cell | 200, no_published_observations/publishednull/containing[] |
| GET cells within fixture, limit1 | 200, cells[]/nextnull |
| GET /v1/releases/latest | 200, release null |
| POST /v1/protocol empty JSON | 405 |

MCP uses matching headers/body:

```http
Content-Type: application/json
Accept: application/json, text/event-stream
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/list
```

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28"}}}
```

Expected tool names: get_protocol, get_cell, list_cells, get_release; annotations readOnlyHint=true/destructiveHint=false. Public reader checks are necessary because protocol and tool discovery alone do not query PostgREST. Current public cells/releases are zero, so these checks disclose no contributor data.

## Final readbacks and stop policy

Require unchanged exact28 ledger hashes, all61 counts and source-bound catalogs/complete ACLs; fulladvisor0; capture singletonfalse; sign-up/anonymousoff; private unexposed; same held workers and no extra function. Save immutable coordinate-free receipts for each command, function inventory, HTTP checks and database/Auth evidence. Stop on any mismatch, CLI failure or partial deployment. No automatic retry, rollback, changed secret, dependency/source fix, JWT weakening or cache SQL belongs in this go. If prior succeeds and public fails, report that exact partial state and stop.

The only authorised future mutations would be the two named function deployments. Local auth config is for development; no `config push` occurs. Repository variables, rights/QA/export workers, Hugging Face, tiles, Pages, source merges, signing, legal/DNS and capture remain separate owner gates.

## Evidence, assumptions and limits

The source manifest binds four prior source modules, sixteen public source modules, config, import map and Deno lock; every local byte matches the reviewed commit. Both direct npm imports and map entries are already pinned. The local verifier passed13/13 deliberate wrong-response tests. The currently deployed v3 prior endpoint returned401 to an unauthenticated empty POST. **Live public/post-deployment smoke results are not claimed.** Server bundling and runtime success remain to be verified after go. The successful owner/service prior path and upstream requests are not invoked against production; CI covers their logic.

No new secret is needed under the platform’s standard environment. If public cannot obtain an acceptable publishable/legacy-anonymous key, it fails closed503; stop rather than supply a privileged key. Optional HF/rate-limit/base-URL settings are left unchanged. API docs link to main, while reviewed source remains unmerged; owner merges and Pages discovery updates are separate. Auth/private-exposure and worker snapshots from GateD must be refreshed after go; preparation is not a persistent lock against an external operator.

Official references: [function configuration/deployment](https://supabase.com/docs/guides/functions/deploy), [CLI flags](https://supabase.com/docs/reference/cli/supabase-functions-deploy), [function authentication](https://supabase.com/docs/guides/functions/auth). The current TLS changelog removes old CBC ciphers no earlier than November10; no TLS workaround is included.

- [gate-d-completion-receipt-2026-10-12.json](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/gate-d-completion-receipt-2026-10-12.json>), SHA-256 `258c5c8f47fcb439af08acf9c07e788036d3816e649b91d4d6ff965ec4d021db`.
- [gate-e-preparation-production-readback-2026-10-12.json](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/gate-e-preparation-production-readback-2026-10-12.json>), SHA-256 `de0a537bb7fd4ff15beac4e8f12b7d87e16edcc48308e6d93e5e86f2851531de`.
- [gate-e-cli-inventory-command-verification-2026-10-12.json](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/gate-e-cli-inventory-command-verification-2026-10-12.json>), SHA-256 `dc49c150a6666c948f1546963203711e7c06c61caf1d20643ac28870efae2ce3`.
- [gate-e-reviewed-source-manifest-2026-10-12.json](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/gate-e-reviewed-source-manifest-2026-10-12.json>), SHA-256 `75aca5a667f59ac75767f19480ac4257f4d2407a39e4b6e10f34a7e0846a39e6`.
- [security-fix-all-pr-ci-20261012T193832Z.json](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/security-fix-all-pr-ci-20261012T193832Z.json>), SHA-256 `1c52e7e73534c2300bbca248df0d0fd5213514214c9a12fb73d5bec73e5f7f60`.
- [gate-e-ci-deno-step-verification-2026-10-12.json](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/gate-e-ci-deno-step-verification-2026-10-12.json>), SHA-256 `78babaa4303df0c60e22d1e9ae884a8acd41b7ace3b056fbd2dec2a9e0013d97`.
- [gate-e-smoke-verifier-self-tests-2026-10-12.json](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/gate-e-smoke-verifier-self-tests-2026-10-12.json>), SHA-256 `45629af041e8f2f8f45a4b2802dbf03a5428ffbe457e9a1365d52de39b43d2aa`.
- [gate-e-http-prior-20261012T194213385506Z.json](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/gate-e-http-prior-20261012T194213385506Z.json>), SHA-256 `7c3a3790caba7c704d8e2ea9c9e0d16a395ee8fad17dffa7ac3f5a0336a7cdec`.
- [gate-d-auth-api-pages-postcheck-verified-20261012T1926Z.json](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/gate-d-auth-api-pages-postcheck-verified-20261012T1926Z.json>), SHA-256 `596dea745bf567269a4184138fca09e201bec52167cdba1d05bed68c59720bcb`.
- [gate-d-worker-native-readiness-20261012T192235Z.json](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/gate-d-worker-native-readiness-20261012T192235Z.json>), SHA-256 `af09b233e063133fdf677a24096dd2ba86a4f828ca2381c7b4c5ac8b8fef6d4b`.
- [Machine-readable exact plan](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/gate-e-edge-functions-plan-2026-10-12.json>), SHA-256 `e039f322cb1d35a5fc53b20f69b40deb51c2df878f4ff31f39d4cbdbd6bd4ac8`.
