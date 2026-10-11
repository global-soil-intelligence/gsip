# GSIP legal pack

> **Draft — requires counsel review.** None of these documents is in force. Capture stays closed
> (`service_state.capture_open = false`) until counsel approves them and the other SPEC section 11
> launch gates pass.

| Document                                                | Covers                                                                                    |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| [Contribution terms](TERMS.md)                          | Accounts, ownership, the ODbL 1.0 and CC BY-SA 4.0 grants, attribution, acceptable use.   |
| [Privacy notice](PRIVACY.md)                            | What GSIP collects and publishes, why, for how long, and every processor and host.        |
| [Withdrawal and deletion](WITHDRAWAL_AND_DELETION.md)   | How a contributor withdraws contributions or deletes an account, and what happens when.   |
| [Classroom and minors](CLASSROOM_AND_MINORS.md)         | The age policy and how classes contribute under a teacher of record.                      |
| [Sampling and land access](SAMPLING_AND_LAND_ACCESS.md) | Where and how contributors may dig; contributors acknowledge these before every queueing. |

## Decisions for counsel

Each document marks open points as **[DECISION]**. In brief:

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

The mechanisms these documents describe are implemented and tested: the capture gate (WP-6b),
withdrawal, deletion and attribution review (WP-6d). `tests/test_processors.py` fails if the code
calls an external host that the privacy notice does not list.
