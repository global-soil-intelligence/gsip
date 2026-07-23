# Independent replacement Pages artifact review

Date: 2026-10-15. Reviewer: Codex independent review agent (`site_library_review`).

**Result: no open artifact findings. The artifact remains closed; this review grants no deployment approval.**

## Exact identity and scope

- Workflow run: `38821460183`; artifact ID: `12013740607`, `github-pages`.
- Artifact metadata identifies main merge `73088050d6fc68baedf893990ab3fbe76d5e749c`.
- Independently resolved both that merge and reviewed head `d13abfb1bace8ba84e6091ce0033f104b53edf78` to the same Git tree: `43c74ca13b889a561e0e23463b9706c064cf48a8`.
- Read `github-pages.zip`, `artifact-metadata.json`, `artifact-verification.json`, and the original builder-clarification Pages receipt and tarball. Archive inspection was in memory, without extracting or executing archive contents.

## Verified checks

- ZIP size is 3,750,774 bytes. Computed ZIP SHA-256 is `2bc0829549d98331c7a8dc5e451b6e5457125fd5863f166e63ce1ea90a4cde33`, exactly matching GitHub artifact metadata.
- The ZIP contains only `artifact.tar`. Computed tar SHA-256 is `8d8bdb97140bfe65840db693ff6417c638381daa9e234c95c18574d37e8481f9`, matching the root receipt.
- Tar layout contains regular files/directories only, no absolute/traversal paths, symlinks, hardlinks, devices or duplicate normalized file paths. Its 38 files total **6,080,760 bytes**; every file path/size/SHA-256 matches `artifact-verification.json`.
- `capture/gsip-activation.json` has exactly the two expected boolean fields: `capture_live: false` and `library_intake_live: false`.
- All five prerendered pages contain exactly one expected headline and Organization JSON-LD. Home and data Dataset JSON-LD identify development/gated status, omit invented coverage/downloads, distinguish RGB from measured spectra, preserve structured-only photo limits and keep individual spectra private.
- Home contains the open soil spectral library mission, whole-stack builder invitation and closed public capture/library status. Data preserves photo-screening/calibration and spectral fingerprinting/privacy boundaries. `llms.txt` contains the same mission, limitations and whole-source/licence invitation.
- The actual public site content, map files, reference-card PDFs, social preview and activation receipt are byte-identical to the reviewed local Pages artifact where their names are unchanged, except for the explained capture entrypoint/service-worker references below. The reviewed social preview's SHA-256 is `07c99fc8d617edf3142267acf75ff9c39fcb88a5ad0f0fc06fb3824dad3785e0`.
- No reserved `supabase.test`, `127.0.0.1`, `e2e-fixture` or `GSIP_E2E` marker appears. Two generic localhost literals remain in the existing capture/map dependency bundles with unchanged counts; the map bundle is byte-identical to local, and the capture bundle normalizes exactly as described below. These are not a copied loopback synthetic fixture or a new connection configuration.

## Explained eight-byte local-versus-CI difference

The original local tarball independently matches every hash in its 38-file, **6,080,752-byte** receipt. Compared with CI, 31 files retain identical path/size/hash. Five capture JavaScript chunks have different content-derived filenames; the capture HTML and service worker consequently change references.

After consistently normalizing those five paired hashed filenames, four JavaScript chunks are byte-identical. The remaining capture entrypoint is byte-identical after removing only CI's expected **`+7308805`** client-version suffix. That suffix has exactly eight bytes and corresponds to the merge SHA recorded by the build's existing `GITHUB_SHA` version mechanism. No other entrypoint byte differs under that normalization.

Capture HTML is byte-identical after normalizing its entrypoint filename. The two service workers have the same normalized 15-entry precache set; the changed entrypoint HTML has its expected content revision, and ordering follows the changed hashed filenames. The service-worker program is identical after abstracting the precache entries. Thus the size delta is fully explained by normal CI build provenance and derived asset references, not a changed activation flag or unexpected application behavior. No key or bundle configuration value was emitted during comparison.

This audit verifies the downloaded artifact and reviewed source identity only. Current workflow/environment waiting state, CI completion and Justin's separate Pages approval are recorded by the root agent. No Git/GitHub, production, browser or deployment state was changed by this review.
