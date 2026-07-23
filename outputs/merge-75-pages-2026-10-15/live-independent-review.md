# Independent live Pages verification

Date: 2026-10-15. Reviewer: Codex independent review agent (`site_library_review`).

**Result: no open findings. The newly deployed Pages content matches the approved artifact; capture and library intake remain closed in the deployed build.**

Verification began only after the root agent reported successful deployment of approved run `38821460183`, source merge `73088050d6fc68baedf893990ab3fbe76d5e749c`. Public GET checks completed at approximately **2026-10-15 23:49 UTC**. No credentials, cookies, authenticated session, form submission, application mutation or Git/GitHub action was used.

## Independently verified live routes

Base: `https://global-soil-intelligence.github.io/gsip/`.

| Route | HTTP | Match to approved artifact |
| --- | --- | --- |
| `/gsip/` | 200 | Exact bytes of `index.html` |
| `/gsip/data/` | 200 | Exact bytes of `data/index.html` |
| `/gsip/methods/` | 200 | Exact bytes of `methods/index.html` |
| `/gsip/about/` | 200 | Exact bytes of `about/index.html` |
| `/gsip/card/` | 200 | Exact bytes of `card/index.html` |
| `/gsip/llms.txt` | 200 | Exact bytes |
| `/gsip/capture/gsip-activation.json` | 200 | Exact bytes |
| `/gsip/og-library.png` | 200 | Exact reviewed preview bytes |

The explicit five `index.html` URLs were also fetched independently: all returned HTTP 200 and exact approved bytes. SHA-256 values match `artifact-verification.json`. The activation manifest hash is `e79c9ca28c243929e0252ffd0b42c868560e17d293c225532d09410b92d04bdc`; the social preview hash is `07c99fc8d617edf3142267acf75ff9c39fcb88a5ad0f0fc06fb3824dad3785e0`.

## Content and gate checks

- Live home announces the open soil spectral library, says the whole software stack is open source, and explicitly keeps public capture/library uploads closed.
- Live data retains structured-only releases until photo screening deployment and approved calibration, and private spectra pending fingerprinting/privacy review.
- Live methods distinguishes ordinary RGB from wavelength-resolved spectra, marks the example samples/spectra synthetic, and requires actual assays for biological relationships. Card copy retains the uncalibrated RGB limitation; about retains the biological-measurement boundary.
- Live `llms.txt` exposes the same mission, closed-state copy, full-source invitation and separate documentation licence as the approved artifact.
- The live activation JSON contains exactly two boolean fields: `capture_live: false` and `library_intake_live: false`.
- The home builder-map and synthetic-demo links point to the intended public repository anchors. Every relative page link resolves to a file in the approved artifact. All five social metadata image references use the approved Pages preview URL, whose live bytes were fetched and matched.

This verifies public static HTTP content and deployed build activation, not a fresh database/auth/worker assessment or a dynamic browser session. Production database capture state, anonymous sign-in, DNS, legal approval, field-model validity and app/device readiness are not inferred from a Pages success. No additional deployment or capture authority is granted by this review.
