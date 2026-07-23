# Next source build: phone-first observations without a print requirement

Proposal only. No implementation, new PR, permission change, migration, deployment or activation is authorized by this file.

## Invariants

Preserve I1–I15, L1–L7 and B1–B8, A+B finalization, existing quality/privacy gates, truthful provenance, personally accepted grants, withdrawal, sealed partitions and public-only agent access. Keep all default/native manifests closed, invited membership enforcement and fixed publication refusal. Preserve TypeScript/Python, licences and the existing dependency/permission/secret checks.

A camera photograph stays uncalibrated camera evidence. A drawn UI guide supplies no observed marker, physical scale, reflectance calibration, measured spectrum or verified sample pairing. Display guides must never be composited into submitted image pixels.

## A. Clarify optional-card capture using the current camera paths

First clarify SPEC §5: physical card “if available” in A/B instructions, with its existing explicit cardless acceptance visible before capture. Register one bounded package in BUILD_ORDER and use its own wp branch/PR. No new measurement tier or schema is necessary for this package.

Recommended product flow:

1. Explain that a phone and permission to observe/sample the location are enough to start; the printed reference is optional.
2. Take photo A (ground/context), then photo B (fresh-face close-up where sampling is permitted). Preserve C as optional.
3. Enter existing context and privately review the selected photographs. Continue without a card or show optional physical-card instructions.
4. Optionally register the sample with real declared depth; hide generated UUIDs and advanced instrument JSON until requested.
5. Personally accept the presented grant, then use the current private admission/queue/receipt flow. Do not show a hosted receipt for an offline/local draft.

Negative regressions before source changes:

- Default wording does not say a physical card or printing is required. The optional card download remains reachable.
- A/B still required; C remains optional. Existing source fixtures confirm missing-card QA is uncalibrated and otherwise judged normally.
- No caller assertion or UI branch turns missing/digital-card photos into verified calibration or an instrument record.
- Existing depth values are not defaulted or inferred. Skipping the sample form yields an observation, without pretending library intake occurred.
- Ordinary closed/default/native landing starts no camera, authentication or upload. The explicit rights view may restore existing-account authentication and rights reads/actions for withdrawal or recovery; it must not start the camera, drain the observation queue or upload intake. Existing account, revocation, queue, idempotence and cleanup tests stay effective.

No new SDK, library or service is proposed.

## B. Optional live browser framing guide

Specify and review separately after A. Browser-only; retain existing native/plugin and picker paths unchanged.

Use an explicitly started, video-only in-page camera preview with a plain SVG framing outline and accessible shutter/retake/cancel. Feature-probe still-photo capture and optional controls. Keep the current camera/gallery fallback usable when permission, device, format or API support is absent. Never require flash, torch, RAW or a precise device fingerprint.

Regression acceptance:

- The preview shows the outline; captured/queued JPEG evidence contains only camera imagery. No guide marker/patch pixels appear in the saved image.
- Stop every track after cancel, completed capture, route/background/account/admission changes and late permission responses for obsolete requests.
- Orientation, mirroring and crop geometry match preview to output. Preserve size/format validation, stale-result fences and existing private cleanup.
- No audio request, frame streaming, new analytics or diagnostic output containing images, coordinates, sessions or capability fingerprints.
- Refusal/fallback tests cover unsupported APIs, rejected constraints, camera busy/denied and oversized/unsupported images.
- Default/native activation and Android’s current no-CAMERA/no-microphone policy remain intact. Embedded native preview or custom Swift/Kotlin is a future separately approved scope.
- CI browser mocks prove code behavior; physical phones separately qualify actual camera, JPEG/HEIC, orientation and memory behavior. No public “works on every smartphone” claim from emulation alone.

## C. Keep one library policy choice explicit

Current private sample registration requires declared depth. Recommendation: finish A using today’s ordinary observation plus optional library-sample paths.

If the owner wants every capture automatically registered in the library with unknown depth, first design a versioned observation-only or unknown-context contract. Define the distinction from a physical sampled interval, its pairing/training eligibility and rights behavior; then add TS/Python corpus, SQL/RPC/queue and populated migration tests. Never invent a depth of zero. This choice does not block A.

## Evidence and held work

The research memo and camera capability audit contain primary sources and exact repository anchors. No physical-phone or scientific experiment ran here. A measurement study should compare the same specimens across phones, lighting, conditions and reference measurements, with specimen/device/site holdouts and predeclared metrics.

Actual accounts/invitations, owner-adopted notices/contact, cohort bounds, fresh production preflight, migrations, workers, canonical artifact preparation, deployment, capture/library opening, field training, public publication and real federation remain separately held. Changes to these gates are not effects of a UI merge.

