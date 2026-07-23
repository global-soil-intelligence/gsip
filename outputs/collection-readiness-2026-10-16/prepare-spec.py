from pathlib import Path

root = Path('/Users/justinhart/.codex/worktrees/gsip-spec-followups/GSIP 2.0')

def replace_file(name: str, old: str, new: str) -> None:
    p = root / name
    text = p.read_text()
    assert old in text, (name, old[:100])
    p.write_text(text.replace(old, new))

replace_file('docs/SPEC.md', '# GSIP v13 —', '# GSIP v14 —')
replace_file('docs/SPEC.md', '**Version:** 13.0 proposed — 2026-10-14 (exact native prototype scope)', '''**Version:** 14.0 proposed — 2026-10-16 (owner-reviewed collection readiness)
**v14 amendment status:** Justin directed on 2026-10-16 that outside counsel must not be a prerequisite for starting soil collection. That owner policy decision is recorded here. The private-collection mode, its implementation scope and deployment plan below are proposals for review; they do not adopt draft terms, open capture or grant production authority. The recommended initial audience is invited contributors; the owner's audience decision remains pending.''')
replace_file('docs/SPEC.md', 'legal pack approved by counsel;', 'complete contribution terms, privacy notice and sampling policy adopted by Justin;')
replace_file('docs/SPEC.md', '**The legal review, not the code, sets the launch date.**', '**Justin sets the launch date after the applicable collection and release evidence is verified. Outside-counsel approval is not a collection prerequisite.**')
marker = '**Phase 1.5 — App and agent readers.**'
insert = '''### 11.1 Owner-reviewed collection readiness (v14 proposal)

Collection and publication are distinct operations. An operator may already retain private records using the offline local-node tools under §16; those tools neither enroll a hosted peer nor enable website uploads. Hosted collection still needs a reviewed implementation and an explicit production go. [COLLECTION_READINESS.md](COLLECTION_READINESS.md) defines the proposed first-collection scope and evidence.

Justin's 2026-10-16 instruction removes outside-counsel sign-off as a project prerequisite for starting collection. Justin must still adopt complete, factual contribution terms, privacy/retention/contact information, age/audience rules and sampling instructions. Contributors still accept the applicable immutable terms version and data/photo grants; an agent never accepts for them (I6/I9). This is a project-policy decision, not a conclusion about legal compliance. Existing licences and rights remain unchanged.

The recommended first hosted mode is an invited, adult, browser-only private pilot. Its audience/account method and bounded duration/capacity remain owner decisions; neither the recommendation nor this proposal authorizes enrolling accounts. The pilot would accept the existing finalized A+B photo set, sample context and optional bounded instrument-declaration JSON, returning only `stored_private_unverified`/`already_stored`. It does not ingest original instrument files or laboratory reports, verify physical pairing, extract field optical features, train field models or enable real node federation.

Before any pilot collection: review and merge the collection build/auth package; deploy the required additive schema with fresh migration-regression, counts, security and gate evidence; adopt and version the actual contributor notices; verify owner-bound sign-in, quotas, private storage/RLS, sanitization, raw-upload cleanup, withdrawal/deletion and recovery; and present the exact target/artifact/commands for Justin's separate go. Existing public self-signup and anonymous sign-in stay disabled for an invited mode. The default Pages and native builds stay closed. A separately reviewed browser collection-artifact path must bind an explicit mode and exact activation receipt, retain the protected deployment approval and refuse missing/unknown/mismatched input. Removing the present packaging refusal or flipping environment flags alone is insufficient.

The general public-launch gates above are not silently waived for a pilot. Any narrower exception to the 50-photo calibration prerequisite, prior-tile requirement or paid-tier requirement must be an explicit, bounded owner decision with its impact recorded before activation. Pilot specimens may support later QA calibration, but collection does not label them QA-passed or scientifically verified.

Pilot publication remains held: no export dispatch, Hugging Face release, public-cell refresh, photo publication, individual-spectrum release or field training. Disabled schedules alone are not a publication barrier because manual dispatch exists. The implementation must define and verify a fail-closed collection-only publication boundary before accepting real records. Existing coarse-cell enrichment and map-host disclosures remain applicable unless deliberately changed in a reviewed package. Native backup/device/store gates remain independent; browser collection makes no claim about native storage readiness.

The full public self-service path requires an additional reviewed account/abuse-control plan, including the owner's CAPTCHA/provider and hosting decisions. The existing §11 photo-publication gate and §16 scientific/fingerprinting/peer gates apply to all modes. A green build, a source merge or a private intake receipt opens none of them.

'''
replace_file('docs/SPEC.md', marker, insert + marker)
replace_file('docs/SPEC.md', '## 14. Changelog\n', '## 14. Changelog\n\n- **v14.0 proposed (2026-10-16):** records the owner decision removing outside-counsel sign-off as a collection prerequisite; proposes an independently gated private-collection path, complete owner-adopted notices, explicit collection-artifact/auth work and a publication hold. No production or implementation authority is granted.\n')
replace_file('docs/SPEC.md', 'Contribution terms require legal review before public launch.', 'Contribution terms and notices require product-owner adoption before hosted collection; outside counsel is not a collection prerequisite (§11.1).')

replace_file('docs/BUILD_ORDER.md', '**Version:** 13.0 proposed — 2026-10-14 (exact synthetic native scope; SPEC §15.12)', '''**Version:** 14.0 proposed — 2026-10-16 (collection readiness; SPEC §11.1)
**v14 amendment status:** records Justin's decision that outside counsel does not gate collection. WP-COLLECT-1 prepares policy/readiness; WP-COLLECT-2 remains a separate, review-gated collection build/auth/publication-boundary package. Audience, operational exceptions and every production go remain unresolved. No current packaging check is removed or weakened.''')
replace_file('docs/BUILD_ORDER.md', 'Fixes the mechanisms behind launch blocker 7; counsel still approves the text.', 'Fixes the mechanisms behind launch blocker 7; Justin adopts the complete contributor text before collection (SPEC §11.1). Outside counsel is optional for that project gate.')
replace_file('docs/BUILD_ORDER.md', 'each marked "Draft — requires counsel review"', 'each marked "Draft — awaiting product-owner adoption"')
replace_file('docs/BUILD_ORDER.md', 'its counsel-review status remains unchanged.', 'its draft/owner-adoption status remains unchanged; SPEC §11.1 removes outside-counsel sign-off as a collection prerequisite.')
replace_file('docs/BUILD_ORDER.md', 'Contributor-facing/legal copy explains individual photo withholding, private review and residual privacy limits, subject to counsel review.', 'Contributor-facing copy explains individual photo withholding, private review and residual privacy limits, subject to product-owner adoption.')
marker = '### Completed (Phase 0 and Phase 1 code)'
insert = '''### Collection readiness (SPEC §11.1; proposed, no activation authority)

**WP-COLLECT-1 — Owner-reviewed collection policy and readiness** ([issue #78](https://github.com/global-soil-intelligence/gsip/issues/78))

Record Justin's removal of the outside-counsel prerequisite. Preserve I1–I15/B1–B8, immutable grants, private data, default-closed builds and every publication/production hold. Define local storage versus hosted intake, recommend an invited adult browser pilot, and document the missing implementation, schema, operational proof and owner decisions. Contribution documents remain drafts until Justin resolves their factual inputs and adopts a version; no agent supplies acceptance or invents policy details. No code, dependency, schema, worker or configuration change.

Acceptance: coherent SPEC/runbook/document status; a concrete readiness matrix and sequencing; no assertion that merged source is deployed or that collection is already ready; independent review and document-format/processor checks.

**WP-COLLECT-2 — Bounded collection build, account flow and publication boundary (held)**

Depends on reviewed/merged v14 and the owner's audience/account decision. Implement a separately explicit browser collection-artifact path, preserving the default Pages/native closed paths, protected Pages approval and exact activation-manifest validation. Invited mode requires an existing owner-provisioned account and never falls back to anonymous account creation; public signup/anonymous mode needs its own reviewed abuse-control/CAPTCHA plan and approval. Keep existing submission/library gates, owner binding, rights/holdout/quota checks and unverified receipts. Specify an enforceable collection-only publication hold, including manual export/public-cell refresh paths, before real collection. No new paid/closed service or dependency without its own approval and audit.

Acceptance tests must fail on current behavior and prove: ordinary Pages/native paths refuse open artifacts; collection packaging rejects unknown/missing/mismatched mode/manifest and only admits the reviewed target; unauthenticated/expired/wrong-owner callers never create an anonymous account or upload; valid invited sign-in and lost-response/idempotent retries work; an absent library capability holds before mutation; real collection cannot flow to export, map refresh, photos, spectra or field training; withdrawal/deletion clears covered payloads and preserves refusals. Add a synthetic browser end-to-end rehearsal and closed rollback proof. CI/review/merge do not authorize deployment.

**Operator sequence after the source prerequisite:** refresh production inventory/counts/gates and security; run migration regression and show only the reviewed pending migration plan; obtain a separate migration go; verify closed schema/capabilities; finalize/adopt/publish the contributor notices and version; prove the required cleanup/rights/sanitization operations and the publication hold; configure only the owner-approved account/provider/tier choices; then present an exact collection artifact, target and activation/rollback commands for a separate go. Do not create accounts, dispatch workers, flip gates, deploy or migrate while preparing this package.

The independent **WP-SITE-1H** copy repair may correct the contradictory closed-page status and remove an assertion that only a legal review blocks collection. It changes no activation behavior and requires a negative regression proving the page remains closed with no upload controls. Collection readiness is tracked in [COLLECTION_READINESS.md](COLLECTION_READINESS.md).

'''
replace_file('docs/BUILD_ORDER.md', marker, insert + marker)

replace_file('AGENTS.md', "DNS, required `validate` status, counsel's legal approval and legal URLs, CAPTCHA,", 'DNS, required `validate` status, owner adoption/publication of contributor notices, CAPTCHA,')
replace_file('AGENTS.md', 'Supabase paid tier and opening capture are Justin\'s actions.', "Supabase paid tier and opening capture are Justin's actions. SPEC §11.1 records his\n2026-10-16 decision that outside counsel is not a collection prerequisite; complete\nnotices, contributor acceptance and all technical/production gates remain required.")

replace_file('docs/legal/README.md', '''> **Draft — requires counsel review.** None of these documents is in force. Capture stays closed
> (`service_state.capture_open = false`) until counsel approves them and the other SPEC section 11
> launch gates pass.''', '''> **Draft — awaiting product-owner adoption.** None of these documents is in force. Justin
> directed on 2026-10-16 that outside counsel must not be a prerequisite for starting collection.
> He must still resolve the applicable factual/policy inputs and adopt a complete version before
> contributors accept it. [SPEC §11.1](../SPEC.md#111-owner-reviewed-collection-readiness-v14-proposal)
> and [collection readiness](../COLLECTION_READINESS.md) preserve consent, privacy, withdrawal,
> licences, technical checks and separate production/publication gates. This decision does not
> establish legal compliance, approve placeholders or open capture.''')
replace_file('docs/legal/README.md', '## Decisions for counsel', '## Decisions for the product owner')
replace_file('docs/legal/README.md', 'Each document marks open points as **[DECISION]**. In brief:', 'Each document marks open points as **[DECISION]**. Justin resolves and adopts the applicable\nchoices; he may seek specialist advice where useful. No choice or effective notice is inferred\nfrom removing the outside-counsel prerequisite. In brief:')
for name in ['TERMS.md','PRIVACY.md','CLASSROOM_AND_MINORS.md','WITHDRAWAL_AND_DELETION.md','SAMPLING_AND_LAND_ACCESS.md']:
    replace_file('docs/legal/'+name, '**Draft — requires counsel review.**', '**Draft — awaiting product-owner adoption.**')
replace_file('docs/legal/PRIVACY.md', "need counsel's confirmation.", 'need the product owner\'s resolution before adoption.')
replace_file('docs/legal/PRIVACY.md', '## What becomes public\n', '''## What becomes public

**Current collection/release status:** public capture and hosted library uploads are closed.
The proposed first collection mode stores finalized photographs, sample context and optional
bounded instrument declarations privately and unverified. It publishes no pilot observation,
photo or spectrum and does not train a field model. Exact audience, contact, retention and
processor notices must be adopted before that mode is enabled. An instrument declaration does
not verify its source file, calibration or physical pairing. The paragraphs below describe the
later eligible public-release plan, not an automatic consequence of private collection. Photo
publication additionally waits for deployed screening and owner-approved calibration.

''')

replace_file('docs/PHASE1_DEPLOYMENT.md', 'Complete legal review of the ODbL 1.0 / CC BY-SA 4.0 contribution terms, then confirm enabling', 'Justin adopts complete ODbL 1.0 / CC BY-SA 4.0 contribution terms and contributor notices, then separately decides enabling')
replace_file('docs/PHASE1_DEPLOYMENT.md', 'When counsel approves it, publish the approved', 'When Justin adopts complete text, publish the approved')
replace_file('docs/PHASE1_DEPLOYMENT.md', 'When counsel approves new terms:', 'When Justin adopts new terms:')
replace_file('docs/PHASE1_DEPLOYMENT.md', '## Automated proof\n', '''## Collection readiness is a separate operator gate

Justin removed outside-counsel sign-off as a collection prerequisite on 2026-10-16. This does
not adopt the draft notices or enable hosted writes. Follow [COLLECTION_READINESS.md](COLLECTION_READINESS.md)
and SPEC §11.1 before a first collection release. The recommended invited browser pilot needs
a separately reviewed collection-artifact/account path and a verified publication hold; the
ordinary Pages/native packaging still refuses open flags. Present exact commands and target,
obtain each production go, and preserve all prior row-count, migration, RLS, secret and rollback
requirements. Any exception to existing calibration/tile/paid-tier launch prerequisites is a
separate bounded owner decision, not an implication of this document.

## Automated proof
''')
replace_file('docs/APP_STORE.md', 'owner or counsel.', 'owner; outside-counsel sign-off is not a collection prerequisite (SPEC §11.1).')
replace_file('docs/APP_STORE.md', '`docs/legal/PRIVACY.md`, which counsel must approve first.', '`docs/legal/PRIVACY.md`, which the product owner must complete and adopt before collection. Store submissions remain separately gated.')
replace_file('docs/APP_STORE.md', 'The independent hosted capability gate also defaults closed.', '''The independent hosted capability gate also defaults closed.

SPEC §11.1 proposes a separately reviewed browser-only collection-artifact path. It is not
implemented by this amendment and does not change the native/default Pages refusal above.
Invited browser collection makes no claim about iOS backup exclusion, native device checks,
notifications, signing or store readiness; their existing gates remain in force.''')

(root/'docs/COLLECTION_READINESS.md').write_text('''# First soil collection: readiness and owner decisions

**WP-COLLECT-1 / SPEC v14 proposal — 2026-10-16. No production authority.**

Justin directed that outside counsel must not delay starting soil collection. This records
that project-policy decision and prepares the technical path. It does not adopt incomplete
terms or claim legal compliance. Public capture and hosted library uploads remain closed.

## What can collect now

The [local library tools](SOIL_LIBRARY.md) can store private sample/measurement JSON under
the operator's control, offline. They do not register a hosted node or synchronize real peers.
For the website/phone path, LIB-4 source is merged but requires deployed schema, its separate
server gate, both app activation gates and a valid contributor account. It collects a finalized
A+B photo set, sample context and optionally a bounded instrument-declaration JSON file. It
does not accept an arbitrary node archive, original instrument file or lab report. A successful
receipt means `stored_private_unverified` or `already_stored`, not verified paired evidence.

## Proposed first hosted collection

Recommend an invited, adult, browser-only pilot, with bounded duration/capacity chosen by Justin.
Use owner-provisioned accounts and keep public signup and anonymous sign-in disabled. The app
must require a valid invited login and never auto-create an anonymous account. Existing code's
email login is not proof of that complete first-use flow; WP-COLLECT-2 must implement and test it.
Public self-service collection is an alternative requiring an explicit account/abuse-control
plan and the owner's CAPTCHA/provider/hosting decisions. The audience is not selected by this
proposal; the request for the owner's preference remains open.

Keep pilot submissions and linked records private, with ownership/RLS, quotas, provenance,
immutable grants, holdout and withdrawal controls. Photographs must have working sanitization
and raw-upload cleanup. Retain the disclosed coarse-cell ISRIC/USDA/Open-Meteo enrichment unless
a reviewed source change disables it; holding a scheduled prior worker does not stop the app's
immediate prior request. Do not promise that no external processor is called.

No pilot record is exported, published as a photo/spectrum, added to public map coverage or used
for field training. A disabled schedule does not prevent a manual export or refresh. WP-COLLECT-2
must specify and test an enforceable collection-only publication boundary covering those paths.
The existing photo-screening/calibration and individual-spectrum/fingerprinting gates remain.

## Factual contributor notice before activation

Justin must adopt the actual notice/terms/sampling text and an immutable matching terms version.
Complete the controller/contact, audience/age, retention and processor inputs; describe the
private/unverified collection scope, deletion/withdrawal path and later publication separately.
No agent accepts for a contributor, publishes placeholders as effective terms, changes a
licence or retroactively rewrites an existing grant. Counsel may be consulted, but outside
counsel sign-off is not this project's collection prerequisite.

## Readiness matrix

| Item | Current evidence / remaining work |
| --- | --- |
| Public website/map | Pages run 38895620835 deployed from 27c3d914; both activation flags false; map worker and redirects verified on 2026-10-16. |
| Hosted schema | Fresh read-only production query on 2026-10-16: ledger 28, capture false, no library tables. LIB-4 `20261013030000_wp_lib4_private_intake.sql` and WP-6fA `20261014010000_wp6fa_private_photo_privacy.sql` are source, not deployed evidence. |
| Counts only | Fresh readback: 5 contributors, 25 submissions, 25 photos, 0 auth users, 0 public cells. No contributor contents were read. |
| Collection build | Ordinary Pages workflow hardcodes false/false; packaging independently refuses an open manifest. WP-COLLECT-2 needs a separately reviewed mode/manifest/artifact path; keep default/native paths closed and protected approval effective. |
| Contributor accounts | No current auth users. Refresh provider/signup settings and select an audience; do not create accounts or enable signup during preparation. |
| Notices and grants | Drafts remain unadopted; owner must resolve inputs, adopt complete text, publish its URLs/version and verify grant acceptance/rejection behavior. |
| Cleanup, rights, QA | Source exists. Verify deployment compatibility, credentials, sanitization and processing/withdrawal/deletion using approved bounded rehearsals before real data. A stored photo is not evidence it survived quarantine cleanup. |
| Publication hold | Default-closed schedules alone are insufficient. Specify/test collection-only export/public-cell/photo/spectral holds, including manual paths. No export or release is authorized. |
| Existing launch prerequisites | 50-photo QA calibration, prior tiles, paid hosting and other §11 gates remain required for public launch. Any limited pilot exception needs its own bounded owner decision and impact record. |
| Native app | Device, backup, notification and signing/store gates remain separate. This proposal does not approve iOS/native field collection. |
| Required CI protection | `validate` passed at the deployed source but is not server-required; owner action remains outstanding. |

## Sequence and acceptance evidence

1. Review/merge the specification; Justin chooses the audience and any bounded pilot exceptions.
2. Build/review WP-COLLECT-2. Negative tests prove closed defaults, strict collection-mode
   packaging, sign-in refusal/no anonymous fallback, missing-capability refusal before writes,
   wrong-owner/race/retry/withdrawal behavior and enforceable publication holds. Rehearse only
   synthetic records in disposable/local targets; never publish those fixtures.
3. Refresh production counts, schema, auth, storage/RLS, worker holds and security findings.
   Run `scripts/db-migration-test.sh` before proposing migration on this row-bearing project.
   Show the exact pending list and exact commands for `toxldjgwkxtneoqsazym`; wait for a separate
   migration go. After migration, verify ledger, unchanged counts/security and closed gates.
4. Adopt/publish the complete notices/version, configure only the approved account/provider/tier
   choices, and prove the cleanup/rights/sanitization path and publication hold under separately
   authorized bounded operations. Report failures; do not infer readiness from a secret's name.
5. Build the exact approved collection artifact and rehearse rollback. Present its digest,
   mode, audience, database gates, deployment target and exact activation/rollback commands.
   Wait for Justin's separate go before any deployment, auth change or gate opening.
6. Verify a consenting participant's phone journey privately. Put only counts/status receipts
   in reports; no coordinates, photographs, e-mails, tokens or sample payloads in public output.
   Verify the private receipt, exact retry, sanitization, withdrawal/deletion and held publication.

No exact activation commands are executable yet: WP-COLLECT-2 and the owner's unresolved choices
determine them. This plan authorizes preparation only. Keep the established production-change
gate and stop on any preflight/readback mismatch.
''')

print('Prepared documentation-only v14 collection proposal; runtime and activation unchanged.')
