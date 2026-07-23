Prepare WP-COLLECT-4's optional live browser framing guide design after source merges #86/#87. Design and review only; implementation remains held.

Recommended first version: invited existing-account browser mode, one video-only stream, separate SVG framing, full-frame JPEG snapshot/review, current camera/gallery fallback, and no fabricated calibration or spectra. New guide photos stay in RAM until the existing owner-bound queue format is committed through a narrow atomic empty-draft/revision/context check. No mixing with unowned picker drafts or automatic restart recovery.

Specify owner/auth/shot/observation/revision fences, late permission/encoding disposal, active-only bounded admission freshness, lifecycle cleanup, explicit fallback/discard tradeoff, resource/geometry limits, exact future file scope and negative-first tests. Preserve A+B/C, optional sample with real depth, rights/privacy/provenance, native permissions and closed artifacts. No dependency, native code, database version/store, Supabase schema, service or licence change.

The design PR grants no implementation, merge, actual camera/device use, migration, deployment, worker, account/invitation or capture/library opening. Physical-phone qualification remains a separate operator gate.
