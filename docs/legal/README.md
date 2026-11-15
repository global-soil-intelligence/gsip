# GSIP legal pack

> **Draft — awaiting product-owner adoption.** None of these documents is in force. Justin
> directed on 2026-10-16 that outside counsel must not be a prerequisite for starting collection.
> He must still resolve the applicable factual/policy inputs and adopt a complete version before
> contributors accept it. [SPEC §11.1](../SPEC.md#111-owner-reviewed-collection-readiness-v14-proposal)
> and [collection readiness](../COLLECTION_READINESS.md) preserve consent, privacy, withdrawal,
> licences, technical checks and separate production/publication gates. This decision does not
> establish legal compliance, approve placeholders or open capture.

| Document                                                | Covers                                                                                    |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| [Contribution terms](TERMS.md)                          | Accounts, ownership, the ODbL 1.0 and CC BY-SA 4.0 grants, attribution, acceptable use.   |
| [Privacy notice](PRIVACY.md)                            | What GSIP collects and publishes, why, for how long, and every processor and host.        |
| [Withdrawal and deletion](WITHDRAWAL_AND_DELETION.md)   | How a contributor withdraws contributions or deletes an account, and what happens when.   |
| [Classroom and minors](CLASSROOM_AND_MINORS.md)         | The age policy and how classes contribute under a teacher of record.                      |
| [Sampling and land access](SAMPLING_AND_LAND_ACCESS.md) | Where and how contributors may dig; contributors acknowledge these before every queueing. |

## Proposed choices for the invited pilot (WP-COLLECT-5, WP-COLLECT-5B)

On 14 November 2026 Justin asked for the open points to be filled in. The documents now carry a
proposed choice at each point, except the contact and the Montana company's registered name, which
only Justin can supply. The proposals
were prepared by an agent, are not legal advice, and are not in force. No choice or effective
notice is inferred from removing the outside-counsel prerequisite. Justin adopts them, changes
them, or takes advice first.

Adoption is a separate set of owner steps, each under its own go: remove the draft banners; change
`TERMS_VERSION` in `apps/capture-pwa/src/terms.ts` (now `2026-07-22-v1`) to the adopted label in a
separately reviewed source change and rebuild; publish that label in `terms_versions`; record
the notice addresses; and resolve or remove every agent caveat inside the notices (the working company name, the repository-recorded Supabase region, the candidate
e-mail provider, the Squarespace observation, the unenforced retention periods and the unverified
hosting periods).

**Open before adoption (WP-COLLECT-5B):** asked which company is the controller, Justin answered
"Montana" on 14 November 2026. [GOVERNANCE](../../GOVERNANCE.md), the SPEC, TRADEMARKS.md, AGENTS.md
and the public site name Viridis LLC as the steward that runs the hosted service. The notices now
name two companies. Which one holds the Supabase project, the accounts and the data, and whether
the governance text should change, is not settled by this proposal and is a question for an
adviser. No governance, specification, trademark or site text was changed.

| Point                       | Proposed choice                                                                                                                                                                    | Basis and what is still needed                                                                                                                                                                                 |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Controller and contact      | The Montana company (working name Viridis North) for the invited pilot. Viridis LLC remains the project steward. The contact mailbox and postal address are left as an owner input | Justin answered "Montana" on 14 November 2026. **Owner input:** the company's registered name, and a mailbox that will be read. See the open point above this table                                            |
| Audience and minimum age    | Invited adults aged 18 or over who live in the United States; no anonymous accounts; no classroom contributions                                                                    | The invited mode already asks contributors to confirm they are at least 18. The organizer confirms residence; the app does not ask                                                                             |
| EU or UK representative     | None appointed; decide again before offering GSIP there                                                                                                                            | Follows from a United States-only pilot                                                                                                                                                                        |
| Lawful bases                | The draft table, unchanged                                                                                                                                                         | No reason found to change it                                                                                                                                                                                   |
| Retention                   | Failed-quality observations: until withdrawal or account deletion, and at most 24 months. Rights-request records: 3 years. Provider logs and backups: the provider's periods       | Proposed periods. No automated job enforces the two numbers yet. **Owner input:** the hosting plan and its retention periods, which the agent did not verify                                                   |
| International transfers     | No transfer mechanism chosen; decide before offering GSIP outside the United States                                                                                                | [AGENTS.md](../../AGENTS.md) records the Supabase project region as `us-east-1`. **Owner input:** confirm the live project's region; it was not verified in this package                                       |
| Licence wording             | The grant text, unchanged. A pilot note says the grant is not used to publish and pilot records cannot be promoted                                                                 | The invited mode records the same grant; [the pilot design](../COLLECTION_PILOT_DESIGN.md) forbids promoting a pilot row                                                                                       |
| Hugging Face history        | Squash within 30 days of a request                                                                                                                                                 | The pilot publishes nothing, so this has no effect during it                                                                                                                                                   |
| Liability and governing law | No liability for indirect loss or reliance on estimates, as far as the law allows, with consumer rights preserved; Montana law and courts                                          | Proposed wording. **This is the part most worth a lawyer's reading.** Montana is the agent's inference from the owner's choice of controller; Justin did not choose the governing law or the courts separately |
| Terms version               | `2026-11-14-v1`, in the existing label format                                                                                                                                      | Needs the source change and the `terms_versions` row described above                                                                                                                                           |
| Sign-in e-mail delivery     | No provider selected. Resend is named as one candidate                                                                                                                             | A closed, possibly billed service: BUILD_ORDER section 2 requires the owner's approval and an audit before any provider is configured                                                                          |
| Classroom points            | Left open and marked as not needed for the pilot                                                                                                                                   | Classroom use is outside the pilot                                                                                                                                                                             |

Implemented and tested: the capture gate (WP-6b); withdrawal, deletion, the refusal of anything a
request covers, attribution review and the age confirmation at submission (WP-6d); the public read
interface for people and agents, which serves only published cells and release records
(WP-AGENT-1); and the phone app, a second way to contribute with the same data and rights as the
website, whose store answers are in [`docs/APP_STORE.md`](../APP_STORE.md) (WP-APP-1). Not built
yet: agent interfaces that act for a contributor or suggest sampling targets, and their routing
rules (later work packages), and any in-app data export (copies are answered by the privacy
contact). `tests/test_processors.py` fails if the code names an
external host that the privacy notice does not list.
