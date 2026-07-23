## Proposed amendment

Schedules the account-free WP-APP-2A build and backup work, WP-APP-2B local notifications, and WP-6f screening of every publishable photo. Records Justin's chosen policies: exclude private cloud backups; allow cleanly separated Android direct transfer; withhold only flagged photos for private human review; no automatic blur.

The reviewed v3.0 header/status and SPEC sections 1–13 remain intact. Section 15 is a pending v4.0 proposal. Notification architecture and detector screening remain unimplemented. **WP-6f may start only after Justin approves and merges this specification PR.** Already-authorized APP-2A preparation can proceed on this commit, with its merge following this specification.

## Invariants

I1–I15 and B1–B8, MIT/ODbL 1.0/CC BY-SA 4.0, TypeScript/Python, public anonymous agent reads and strong RLS continue to hold. Capture and production anonymous sign-in remain closed. No dependency, model, migration, service, signing material or production setting is added. Every production command still needs its exact-target go. Justin reviews and merges.

## Review evidence

- Existing language guard and whitespace check passed using the bundled supported Node runtime.
- Seven local document links/anchors resolve; scoped formatting checks pass.
- Compared SPEC sections 1–13 with the reviewed base: unchanged.
- Dependency comparison cites primary sources and distinguishes code licenses from model-weight licenses; records maintenance and payload size without claiming runtime size or GSIP recall.

## Assumptions and unresolved gates

- Local notifications are a proposed MIT plugin, requiring a fresh pinned/transitive audit, measured artifact impact, inexact scheduling and unchanged-strength Android dependency/permission checks in the implementation PR.
- Public coverage alone does not establish land access or absence of withheld observations; nearby suggestions stay disabled unless eligibility inputs support them.
- Current WebKit IndexedDB/localStorage iOS backup exclusion is unproven. A separate storage design or approved native-language exception and synthetic physical-device backup/restore evidence are required.
- Open face/text candidates are for private benchmarking; no complete calibrated detector set is selected. Plate-weight licensing, global category coverage, high-recall calibration and runtime size remain gates.
- Owner policy choices are not deployment approval or approval of an unreviewed screening implementation. No real contributor data is used.
