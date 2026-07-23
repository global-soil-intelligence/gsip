# Final independent adversarial review: iOS native-storage design V4

## Outcome

No blocking review findings remain in this **design-only** proposal. It is ready for Justin's concrete architecture/product review. This review neither approves a pull request nor grants native implementation, the TS/Python exception, device/backup acceptance, dependency adoption or production authority.

Frozen374-file manifest SHA256: `d87d1f26f18a2be15e28b4f82e4a9dde553fcd117866c912a94aa1d733659e10`.
Frozen source: `/private/tmp/gsip-ios-v12-final-m3_wxkd4`.

## Actual independent evidence

- Recomputed all374 content hashes and modes before copying, and checked the frozen source again after tests; all match. Only the new test file differs from reviewed V3; all design/header/build-order bytes remain unchanged.
- Verified372-file baseline against read-only Git commit `de9d1221b7c73e9be5c7e25ccaa24dcfa7903934`. Exactly370 previous file hashes/modes are unchanged; only SPEC and BUILD_ORDER changed and two files were added.
- Removed only the declared new headers/changelog/section additions and reconstructed complete original SPEC and BUILD_ORDER byte-for-byte. I1-I15, section11, prior15.1-15.10 and all16 remain exact; all132 old acceptance lines/states are unchanged and exactly6 new implementation criteria remain unchecked.
- Final candidate private focused suite: **93passed,0failures/errors/skips** across backup-plan, feasibility, native-design and spec-v4 contracts.
- Baseline plus final new test file: **25 expected failures,0errors/skips**.
- **13 document mutants rejected**, each with assertion failures and zero errors/skips: native exception granted; exclusion only after open; synchronousNORMAL; pending-old classification removed; ordinary legacy boot; storage error as empty; dropped libraryNamespace; checked implementation criterion; pending-old admit+anchor rollback; mismatch admit; absence proves fresh; clean admission without root checks; repeated committed mutation.

These are documentation/source-contract results. They do not exercise a native backend, actual Keychain/SQLite/Capacitor runtime, iOS lifecycle or a backup transport.

## Review finding resolved

V3's global phrase assertions let an unsafe pending-plus-old ADMIT/anchor-rollback table row survive25tests. Root strengthened an existing test to parse observation/action rows and pin the pending-old, mismatch, both-absent, clean and committed behaviors. V4 preserves the25case count and rejects the original surviving mutant plus all four additional incorrect row behaviors. The V3 survivor log/receipt remains retained, not overwritten or misreported as a pass. No design claim had the unsafe behavior; this closes the regression-test gap.

## Architecture and remaining gates

The conditional proposal is internally consistent with the no-cloud/rights contract. Exclusion precedes SQLite open/recovery; single-database six-store operations and receipts preserve original-account/generation/auth/reminder fences. DELETE/EXTRA, actual VFS/settings/scratch placement and process-kill versus power-loss scope are explicit admission evidence, not presumed functionality. The Keychain protocol is honestly separate/non-atomic and not a monotonic hardware counter; pending-old state preserves quarantined bytes with unresolved availability, rather than rolling backward. Passcode-required policy, reinstall/missing-anchor classification and destructive fresh-start UX remain pending owner decisions.

The owned host, bridge/prompt/native-route allowlists and camera capability provenance are unproved public-seam candidates that must stop for a new review if unsupported. The proposal does not invent a present native camera handle broker. Auth storage errors remain unknown; stale refresh callbacks require epochs. Isolated legacy export is frozen and bounded without normal app startup or IndexedDB creation/upgrade; verified copy precedes purge. Supported WebKit callback/readback is not physical erasure or evidence that older backups were retracted.

Primary cross-checks: [SQLite settings](https://sqlite.org/pragma.html#pragma_synchronous), [temporary files](https://sqlite.org/tempfiles.html), [atomic-commit assumptions](https://sqlite.org/atomiccommit.html), [Apple Keychain protection](https://support.apple.com/guide/security/keychain-data-protection-secb0694df1a/web). These explain public API semantics; no actual iOS runtime, persistence/flush, entitlement or backup behavior was observed here.

No actual private app data or real photos/coordinates/credentials were used or found in the four changed paths. No shared-source edit, Git/GitHub mutation, implementation, native build/device call, dependency installation, account/signing action, Supabase query, worker, Pages, production or capture action was performed by this reviewer. Full CI is root's separate evidence.
