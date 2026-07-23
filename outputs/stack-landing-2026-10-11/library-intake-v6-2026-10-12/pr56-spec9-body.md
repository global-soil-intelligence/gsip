GSIP has a private library node format and hosted phone intake, but it has no reviewed node-exchange contract. This v9 draft specifies bounded private exchange and separates a pure contract (LIB-5A), a synthetic local rights simulator (LIB-5B), and real peer authority/transport (LIB-5C, held for owner decisions). Architecture approval precedes implementation; this PR contains only SPEC and BUILD_ORDER changes.

## Invariants

- I1–I15, L1–L7 and B1–B8 remain binding. Phone RGB observations remain uncalibrated optical evidence; instrument wavelength spectra, physical pairing, laboratory measurements and field training keep their separate verification gates.
- Scientific arrays remain private. No images, precise coordinates, exact time, serials, personal identifiers, private paths, credentials or arbitrary source URLs enter the proposed exchange.
- Public agent REST/MCP stays anonymous and read-only. A node namespace is not peer identity or a delegated contributor credential.
- Withdrawal and retirement restrict monotonically. Authenticated retirement fences a known scope before payload erasure and does not wait for sequence gaps; acknowledgments remain pending until covered payload is absent.
- Capture, photo publication, production migration/deployment and actual peer sharing remain separately gated. This draft permits none of them.

## Proposed contract and sequencing

The proposed strict UTF-8 `gsip-node-exchange-v1` contract has declare/retire events, exact-byte retry digests, immutable event/sequence bindings and contiguous validated stream heads. Same-owner lineage aliases remain distinct from physical pairing and cross-contributor linkage. The local simulator uses private files, bounded atomic admission and reserved scope fences, priority cleanup and honest pending acknowledgments. Aggregate storage/queue limits are proposals, not measured capacity.

LIB-5C stays held for recipient-specific purpose/consent/retention, counsel/privacy review, peer admission, an exact revocable credential and cleanup mechanism, real digest/lineage retention, and cross-contributor policy. No credential scheme, real transport or data export is implemented.

## Changes after review

- Defined source/destination/scope stream identity, immutable slots, contiguous head advancement and immediate retirement fencing; the initial independent review found sequence gaps could otherwise leave retirement ambiguous.
- Added aggregate admission/cleanup/byte bounds and reserved durable scope fences; the initial review found per-human limits alone did not bound total storage. Capacity exhaustion holds use rather than evicting refusals or inventing a reset.
- Clarified synthetic private event-digest retention and its distinct real-data privacy/legal hold. Hashes are not treated as anonymity or proof of remote erasure.

## Verification

- Independent final prose review: no remaining findings; eight static identity/preservation checks passed. Both initial P2 findings are closed in the exact two-document candidate.
- Final source: `db3a37062008c291b6e8aa491b99eab3e752fe16`; SPEC SHA256 `f50f56da1fb25c4a15f5496e6455811c82e40fe2e5cb9ed931de28b01df3c0ae`, BUILD_ORDER SHA256 `eff2434d700ee83669136d03efeaf973426b2452740301bbca357cc75734f0b2`.
- Final independent receipt SHA256 `66efbe14646a689c62badc6f44970fe68268799bf89dc91e4debde4afc2219dc`.
- Both documents pass formatting; diff whitespace check passes; their pinned gitleaks 8.21.2 authored-file scan reports zero findings. No runtime behavior, capacity, field-science or production claim follows from prose checks.
- CI is to be read back at this exact head. Whole-stack scanning is held by the separately reported historical noncredential browser-fixture fingerprint. The original three approved ignores are unchanged; no further suppression or scan weakening has been applied.

## Assumptions and owner decisions

- This is an unapproved architectural proposal stacked on WP-6fC, not current governing permission to implement LIB-5A/5B or share real data.
- The finite quotas and version-one scope holds are conservative engineering proposals; practical sizing/recovery needs later evidence and a reviewed contract change where applicable.
- Original-owner scoped lineage is weaker than physical pairing; no cross-contributor similarity, global hash index or public membership is authorized.
- No new dependency, paid/closed service or licence change is introduced. MIT code, ODbL 1.0 data and CC BY-SA 4.0 photos remain unchanged.
- Owner policy, calibration, production, launch, signing and real-device verification remain separate gates. No GitHub approving review or DCO certification is performed by an agent.


## Changes after review — description clarification

The opening reference to hosted phone intake means hosted phone-intake **code**, not deployed production intake. The earlier broad phrase “retirement fences a known scope” is clarified: authenticated retirement applies sample refusal before payload erasure and does not wait for sequence gaps; storage saturation uses the reserved scope fence. Acknowledgments remain pending until covered payload is absent. SPEC §16.10–16.12 already states this distinction; no specification or runtime change is needed.


## Verification — exact-head CI readback

The [validate run](https://github.com/global-soil-intelligence/gsip/actions/runs/38355333489) completed successfully at `db3a37062008c291b6e8aa491b99eab3e752fe16`: 779 Python tests with GDAL, 424 TypeScript tests, 593 database assertions, 45 populated migration assertions, six library and 31 photo two-connection cases, 12 browser tests and configured static/Deno/build checks. These verify the existing stacked runtime at this documentation head; no LIB-5 implementation or operational capacity was tested. The final independent commit/body binding closed the description finding (receipt SHA256 `48a9e2fa807f92b187eaea26a6a9154bfdbe3b650851b61221f25e63add3c07e`). Full-history gitleaks is still red on the single historical fixture match; no further ignore or scan weakening was applied. Architectural approval and all real-sharing/production gates remain separate.
