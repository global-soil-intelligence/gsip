The approved policy excludes private queue records, draft photos, library context and sessions from iCloud backups while preserving offline durability. Exact source inspection found that the existing filesystem API does not establish exclusion readback/error propagation or crash-safe replacement. No backend is selected and iOS backup protection remains blocked/unverified.

Proposed sequence: specification v11; APP-2C1 source/capability feasibility; held APP-2C2 migration only after a concrete supported mechanism is approved; APP-2C3 separately authorized synthetic physical-device backup/restore proof. Existing production, capture, notification-device, photo-publication and store/legal gates remain intact.

Options:
- Recommended now: keep iOS release held and complete source-only feasibility; audit a suitable upstream open solution against the full contract.
- If upstream capabilities are insufficient: submit an exact native bootstrap/storage/lifecycle design. Custom native code requires Justin's explicit exception to the TypeScript/Python-only rule before implementation.
- No policy relaxation, fallback into WebKit, or new dependency is authorized by this issue.

Assumptions: the no-cloud policy remains binding; existing pinned sources are evidence of limitations, not device outcomes; observed generated native resolution is not a repository-native lock. No real contributor data or device/backup inspection is needed for feasibility.

Done when: the specification is reviewed, a concrete mechanism has independently verified capabilities or a documented blocked outcome, and any owner decision is explicit. Simulator/artifact builds do not close physical-device proof.
