# Actual Pages artifact independent review

Verified 2026-10-16 11:50:22 UTC. **No unresolved findings or unexplained material differences. This is not deployment approval.**

Live read-only GitHub metadata binds [Pages run 38895620835](https://github.com/global-soil-intelligence/gsip/actions/runs/38895620835), attempt 1, to `main` commit `27c3d9143ff78dce65fa4d2e88e1660c79574232`. The commit tree is `d49fa2ef6b31a0042db64d74e78b8a12df5b758b`, exactly the previously reviewed PR #77 tree. Local Git tree and empty whole-tree diff readback confirm it. The build succeeded; the deploy job remains waiting for Justin.

Artifact `12043617713` has official ZIP digest `d818ff8663588d7eb12bdf691b92127ee6ca61495c4e6ab9c08eae1c596fbc0b`, independently matched to the downloaded 3,901,961-byte ZIP. Its embedded TAR digest is `bc5ab24a2ff6ca54c92cf09db589ac98a5233c7c101013fc1886c09e1605d769`. All 40 safe file names, sizes and hashes match the saved artifact manifest and actual preview; no links or path escapes occur. Content totals 6,623,136 bytes.

All map files match the reviewed preview exactly. The whole map is **2,422,310 / 5,242,880 bytes**. Worker: 509,702 bytes, SHA-256 `096f3b4deeeaa7ed1372a96978bea3495b78250041df835fada34f12320e11d2`. Full notice: 32,566 bytes, SHA-256 `9aa4807394e33c6a38be8c590001a791203e703d9afefa0e7c2f47b1655a1dce`; exact pinned MapLibre licence text is present, preserving resolution of the earlier P2 finding. Capture activation is strictly `{"capture_live":false,"library_intake_live":false}`.

33/40 files match the premerge local artifact byte-for-byte. The remaining seven are fully explained:

- The capture entry changes from `index-CMcpQaOK.js` to `index-DEdswBKo.js` and adds exactly eight bytes: existing build configuration injects `GITHUB_SHA` into client provenance, changing `0.1.0` to `0.1.0+27c3d91`. After that one suffix and generated filename references are normalized, entry contents match exactly.
- Four renamed capture chunks (`web` plus three `esm` chunks) match exactly after normalizing the generated import filenames; their byte counts are unchanged.
- Capture HTML only changes its generated entry filename.
- The service worker contains the same 15 precache entries after mapping generated names and the correct HTML content revision. The remaining changes are entry ordering and an equivalent local-variable rename; the normalized service-worker shell matches exactly.

This is a concrete metadata/hash cascade, with no unexplained OS/minifier-content difference and no change to upload gates or worker behavior. The precise seven filename pairs and checks are in `pages-run-38895620835-independent-review-receipt.json`. No configuration key value was printed.

The reviewer used read-only archive inspection, source reads and GitHub reads. No new build, server, approval, merge, deployment or protection change was performed. Justin's separate Pages go and subsequent live destination verification remain outstanding.
