# Independent adversarial review: iOS native-storage proposal V3

Source manifest: bb928de44bf09547090ca51dfbe9441a9d82caea2ecde577657994d41953a948.
Root-owned frozen source: /private/tmp/gsip-ios-v12-frozen-u83ntoxd. Independently copied all 374 declared paths after recomputing mode/content hashes; no frozen/shared source edits.

## Outcome

The actual V3 architecture proposal has no blocking unsafe readiness or implementation-authority claim. It correctly leaves custom native scope, passcode-required policy, uncertain recovery UX, public host/camera seams, exact SQLite/native binding and physical-device evidence unresolved/held. This is a reviewable conditional mechanism proposal, not a storage solution, a native-code exception, a device result or deployment authority.

One documentation-test regression gap remains for root to resolve or explicitly document: replacing only the pending-plus-old state behavior with an instruction to admit the old database and roll back the anchor passes all 25 new tests. The implementation-free design itself has the correct QUARANTINE behavior. Global vocabulary checks do not pin the crucial observation-to-action mapping. Strengthen a current test to inspect the exact row and require quarantine, preservation and no anchor rollback; optionally pin mismatch and both-absent rows too.

## Independent verification actually run

- Extracted all 372 baseline files read-only from Git commit de9d1221b7c73e9be5c7e25ccaa24dcfa7903934 and independently checked all baseline hashes/modes against BASE_MANIFEST.
- Final V3 candidate: exactly two changed prior files (SPEC, BUILD_ORDER), two new files (design, regression tests), 370 prior content/mode hashes unchanged.
- Reconstructed the complete old SPEC and BUILD_ORDER by removing only declared new header/changelog/section additions: byte-exact original document SHA256s. This proves I1-I15, section11, prior15.1-15.10 and all16 content preserved. All132 original acceptance lines/states remain exact, with exactly6 new unchecked implementation criteria.
- Baseline plus new test file:25 expected assertion failures,0 errors,0skips.
- Private V3 focused suite:78passed,0failures/errors/skips.
- Eight document mutants rejected with1failure each and0errors/skips: exception grant, post-open exclusion, synchronousNORMAL, missing pending-old state classification, ordinary legacy bootstrap, unknown-is-empty, dropped libraryNamespace mapping and checked implementation criterion.
- An additional behavior mutant survived: pending-old ADMIT+anchor rollback,25passed. This is retained transparently in MUTATION_BEHAVIOR_SURVIVOR.json and associated log/XML; it has not been called passing policy proof.

## Architecture scrutiny

The proposal addresses the earlier risk memo without inventing a guarantee: bootstrap is before ordinary JS/auth; legacy exporter is isolated/frozen, known-IDB-no-create/upgrade, bounded snapshot without bridge-await inside transaction; old data remains authoritative before verified-copy/purge; supported WebKit completion is not physical erasure. Native SQLite uses one database/serialized writer, fixed operations, DELETE/EXTRA readback, scratch/hot-journal handling and per-operation receipts. Pending Keychain/DB disagreement quarantines rather than rollback; the cross-store protocol is explicitly non-atomic and availability after a pending-before-commit crash unresolved. The chosen passcode class and reinstall/absence classification are pending owner choices rather than already approved policy.

Owned host and special-file/message/prompt gates are explicitly unproved public-seam candidates. Camera output-handle provenance has no invented current SDK broker; it stops for another scope review if an enforceable seam is absent. Session errors are unknown, stale SDK writes require epochs and cookies/cache/OS-notification/temp surfaces remain separately audited. No generic TypeScript mutex, file name, post-write flag, simulator build or source test is claimed as sufficient proof.

Current primary cross-checks: [SQLite PRAGMAs](https://sqlite.org/pragma.html#pragma_synchronous), [SQLite temporary files](https://sqlite.org/tempfiles.html), [atomic-commit assumptions](https://sqlite.org/atomiccommit.html), [Apple Keychain data protection](https://support.apple.com/guide/security/keychain-data-protection-secb0694df1a/web). Apple distinguishes the passcode-required class from generic device-only classes; runtime readbacks/lifecycle/device behavior still require separate observation. No universal rollback or no-backup guarantee follows.

## Limits and authority

Only private copies, source/public documentation and synthetic document tests used. No implementation, native compilation/device run, dependency installation, application data, credentials, signing/accounts, Git/GitHub mutation, production query/change, worker, Pages or capture action. No claim about unrun full CI or native/backup readiness.

V1 mismatch was identified before certification: two candidate paths differed from the supplied V1 manifest while root was making disclosed pre-freeze corrections. No V1 test or exact-source acceptance claim was made. The review was rebound to root's separate immutable V3 before all verification above.
