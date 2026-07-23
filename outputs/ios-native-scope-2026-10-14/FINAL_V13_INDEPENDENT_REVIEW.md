# Final independent review: v13 exact native prototype scope V4

## Outcome

**No blocking scope-review findings remain.** The proposal is concrete enough for Justin's exact native-code/file/effect decision. This review does not approve a PR or grant implementation/native-language authority. The accepted passcode-required and preserve-quarantine/no-automatic-reset choices remain accepted; they are not reopened or treated as private-data/device access permission.

Frozen manifest SHA256: `06710bba4738a0a4cebfea27b4c5d34ea282ad21fd40e80a5670e47970364402`.
Frozen source: `/private/tmp/gsip-ios-v13-v4-32n530rl`.

## Exact binding and preservation

- Independently verified377 declared content hashes/modes before copying and again after all tests. Baseline374-file bytes/modes were extracted read-only from main `6a652f94b220be7eeff49508283883c502baa527` and checked against BASE_MANIFEST.
- Exactly371 prior files are unchanged. Three prior docs change only declared proposal/status additions; three new files are scope prose, finite JSON snapshot and document-contract tests. No prospective native/support implementation file exists in this source tree.
- Independently reconstructed complete prior SPEC and BUILD_ORDER byte-for-byte after removing only declared v13 additions/header/history labels. Independently reconstructed the prior native design after reversing only owner-status/history changes. Final V4 hashes of these three documents equal the verified V2 hashes, so their preservation receipt remains exact.
- All138 previous BUILD_ORDER acceptance lines/states remain exact; exactly2 new criteria are unchecked. All old normative SPEC1-13, previous15 and entire16 content remains unchanged. Existing runtime, workflow, dependency, permission, scanner and Android behavior is untouched.

## Tests actually run in independent private copies

- Final focused suite: **131passed;0failures/errors/skips** (backup plan, feasibility, native design, spec-v4 and native scope).
- Baseline plus final new test: **38 expected failures;0errors/skips**.
- New tests include34 unsafe JSON variants, strict source bindings, exact roles/import/effect ceilings, duplicate-field handling, finite copy map and current owner-policy preservation; these are scope tests, never native behavior acceptance.
- **21 external mutants rejected;0errors/skips:** wildcard path; Security import in the wrong otherwise allowed file; wrong role; wrong allowed effect; ordinary-app wiring; weaker Keychain class; automatic reset; altered source binding; extra generated AppDelegate edit; real notification operation; ordinary core-test identity; removed private-data prohibition; copy into wrong root; missing copy; aliased copy destination; accepted policy relabelled pending; SecItemDelete grant; URLSession grant; missing constructor controls; notification disable after construction; caller-SQL grant.

No full CI, native compile, system Keychain/SQLite execution, physical-device result, power-loss, backup, migration or production behavior is claimed by these checks.

## Findings resolved

1. V2's exact JSON tags did not protect prose API restrictions: both SecItemDelete and URLSession positive-grant mutants survived all36 prior new tests. V3 added section-scoped API prohibitions and constructor ordering/readback assertions. V4 rejects both original survivors plus missing/late constructor controls and caller-SQL broadening. The V2 survivor logs/XML/receipt remain retained transparently.
2. V3's core-copy destination was unnamed and its21 copied source outputs were insufficiently distinguished from9 template-patch targets. V4 names the literal `GSIPPrivateStorePrototype/` sibling of `App/`, enumerates all21 source-to-destination pairs in JSON, and separately bounds9 generated-template patches. Independent wrong-root, missing and alias mutants all fail. No scope expansion or wildcard is inferred.

## Scope assessment and remaining gates

The proposal has finite21 Swift paths, imports and responsibilities, exactly3 prospective new Python/CI support files, explicit21 hash-preserving source copies and9 generated-template targets. Imports grant only named API effects. It permits no arbitrary filesystem/SQL/Keychain search, native networking, reset, existing private data, real camera/picker/location, ordinary app registration, legacy export/migration, dependency/core fork, signing/device/account or production action. Simulator tests use isolated fresh identities/root and must hold unsupported passcode semantics rather than weaken the class or label mocks as platform proof.

The future harness is disposable and separate from ordinary App/Android builds. Core/host/test membership and actual compile/link/bundle exclusion are required; DEBUG alone is not accepted. Core routing and NotificationRouter constructor limits are explicit, with descriptor/JSON controls before configuration/bridge construction and no real notification operations. Public host/loader/target/template seams remain assumptions that must stop for another review if unworkable. Device/residual/backup/store/production gates remain separate. All38 tests merely protect that conditional scope and its wording/manifest relationships.

No shared source edits, Git/GitHub mutation, generated/native implementation, dependency installation, simulator/device/native API call, application/Keychain/personal data, signing/account input, production query/change, Pages, worker or capture action was performed by this reviewer. All outputs are private copies and synthetic document checks.
