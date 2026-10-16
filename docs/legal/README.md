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

## Decisions for the product owner

Each document marks open points as **[DECISION]**. Justin resolves and adopts the applicable
choices; he may seek specialist advice where useful. No choice or effective notice is inferred
from removing the outside-counsel prerequisite. In brief:

1. **Controller details.** Viridis LLC's registered address and privacy contact, and whether an EU
   or UK representative is needed (Art. 27 GDPR / UK GDPR) if the app is offered there.
2. **Minimum age** for independent accounts (draft: 16, or the local age of digital consent if
   higher), and the consent model for classroom use (draft: teacher of record, no student accounts).
3. **Lawful bases** per purpose (draft: contract for the service; consent for publishing a typed
   attribution name; legitimate interests for QA, abuse prevention and security).
4. **Retention periods** (draft table in the privacy notice).
5. **International transfers** and the mechanism for each processor (Supabase region, GitHub,
   Hugging Face, Open-Meteo, ISRIC, USDA).
6. **Licence wording**, including the honest statement that copies already released under ODbL 1.0
   and CC BY-SA 4.0 cannot be recalled.
7. **Hugging Face history**: whether the steward squashes dataset history on a schedule or only on
   request.
8. **Governing law and venue**, warranty disclaimer and liability cap.

Implemented and tested: the capture gate (WP-6b); withdrawal, deletion, the refusal of anything a
request covers, attribution review and the age confirmation at submission (WP-6d); the public read
interface for people and agents, which serves only published cells and release records
(WP-AGENT-1); and the phone app, a second way to contribute with the same data and rights as the
website, whose store answers are in [`docs/APP_STORE.md`](../APP_STORE.md) (WP-APP-1). Not built
yet: agent interfaces that act for a contributor or suggest sampling targets, and their routing
rules (later work packages), and any in-app data export (copies are answered by the privacy
contact). `tests/test_processors.py` fails if the code names an
external host that the privacy notice does not list.
