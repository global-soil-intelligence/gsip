Implement the exact synthetic APP-2C2A scope approved in #71. Justin authorized the 21 listed Swift files, three Python/CI support files, nine disposable template edits and 21 literal copies.

Invariants: require complete file protection plus backup exclusion before storage access; preserve/quarantine uncertainty; require passcode-bound non-synchronizing default-group Keychain policy; fence owner/epoch/lease/generation/revision; keep the ordinary app free of prototype/test payloads. No new dependency, production, capture, ordinary-app adoption, device, signing or account authority.

Acceptance evidence must distinguish actual simulator storage/host behavior, injected anchor/state-machine faults and held physical-device/backup/platform-anchor proof. Preserve all existing source/check policies and verify exact native test membership with no missing/skipped cases.

The implementation PR remains subject to owner review and a separate merge go.
