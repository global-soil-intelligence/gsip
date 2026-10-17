# Phone-first soil observations

WP-COLLECT-3 implements SPEC §5.1. Justin authorized pushing these source updates after the 2026-10-16 card-overlay research. This source proposal does not authorize a merge, deployment, contributor invitation or opening capture/library uploads.

## What stays true

- A context photo (A) and fresh-face close-up (B) remain required; texture photo C remains optional. Sampling requires permission and the existing safety/rights acknowledgments.
- Missing a physical card alone does not fail QA. Sharpness, exposure, privacy, admission and all other gates still apply. Cardless photos stay uncalibrated RGB source evidence, not automatically extracted `camera_rgb` summary records. Extraction still follows SPEC §16.3 and is not added here. Neither kind becomes measured spectra or a verified biological/laboratory result.
- An ordinary observation does not automatically register a library sample or enroll a federation peer. Sample registration is explicit, with real declared depth. Never infer or default missing depth to zero.
- Preserve I1–I15, L1–L7, B1–B8, exact photo evidence, strict instrument declarations, queue ownership, withdrawal, private pilot admission and publication holds. Keep both activation flags false in default Pages/native builds.
- No new dependency, service, licence, native code, permission, schema or camera API is selected.

## What changes in COLLECT-3

Make “no printed card needed” visible before capture and in public protocol/site/builder instructions. Keep the free reference card as an optional physical aid, with accurate printing instructions for people choosing it. Static framing illustrations describe the requested photos; they are not live camera overlays.

Use today's camera/picker, retain both required photos, collect the existing context and personally accepted rights, then use the existing private queue/receipt flow. Keep the library sample checkbox optional. Reveal advanced instrument JSON only when requested, without changing its validation, persistence or deletion. Generated identifiers stay out of the normal form.

The explicit rights view may restore existing-account authentication for withdrawal/recovery while intake is closed. Ordinary closed/default/native landing still starts no camera, authentication or upload. No camera guide or default library registration is introduced by this wording/disclosure package.

## Why an overlay cannot calibrate a photo

An SVG guide can help framing over an app-controlled camera preview. It cannot measure the illumination, camera response or material reflectance seen by a physical target. Never composite a reference marker or colour patches into submitted pixels: those would be drawn UI rather than observed scene evidence. Even the printed GSIP card uses digital sRGB targets and is not certified reflectance calibration (CARD_SPEC.md and SPEC L3).

The image-formation model and a qualified smartphone method using prior physical-target device calibration are described by [Nixon et al. (2020)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0230561). This is evidence for the measurement distinction, not proof of soil accuracy on arbitrary phones. [Li et al. (2025)](https://www.mdpi.com/2571-8789/9/3/93) evaluate physical soil reference plates; reduced variation does not guarantee removal of measurement bias. RGB-to-spectrum reconstruction remains an inference requiring validation, as discussed by [Huo et al.](https://arxiv.org/html/2304.02162v2).

## Future live-guide design

COLLECT-4 must first review a bounded browser design: explicit video-only permission; guides outside saved image bytes; orientation, crop and resolution behavior; cancellation/background/account/admission/late-response cleanup; and a usable camera/gallery fallback. The existing system camera cannot inherit a page overlay. [Media Capture](https://www.w3.org/TR/mediacapture-streams/), [Image Capture](https://www.w3.org/TR/image-capture/) and [Capacitor Camera](https://capacitorjs.com/docs/apis/camera) define the relevant interfaces; support and controls must be feature-detected.

No RAW, exposure, flash, universal-browser or native WebView behavior is assumed. No physical-phone, soil-reference or scientific accuracy experiment ran for this research. Actual devices and controlled paired specimens are separate qualification steps. Default node registration with unknown depth likewise needs a reviewed schema/protocol decision before implementation.

## Acceptance evidence

Tests must fail before the optional-card wording and advanced-disclosure changes. Preserve missing-A/B refusal, optional C, ordinary-observation opt-out, blank sample depth, strict declaration import/clear and draft recovery. Reuse the existing cardless/uncalibrated QA tests; retain closed/rights/pilot/native/artifact checks. Independent review and required CI precede the owner's merge decision. Source or CI completion does not establish production readiness or opening authority.
