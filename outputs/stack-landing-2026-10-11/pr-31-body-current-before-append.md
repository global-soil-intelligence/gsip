## Work package

- WP: WP-6d, contributor rights and launch paperwork (`docs/BUILD_ORDER.md` §4, Phase 1.1)
- Branch: `wp-6d-contributor-rights`
- Stacked on (if any): `wp-6c-priors-and-tiles`

## Summary

Builds the mechanisms behind launch blocker 7. Counsel still has to approve the legal text.

- **Requests** (`deletion_requests`, append-only `grant_withdrawals`).
  - Withdrawing contributions or deleting the account withdraws every grant in the same
    transaction, so the next release already leaves those observations out.
  - Nothing a request covers comes back. Grants accepted at or before a request, any grant once an
    account deletion is requested, and submissions, photo rows and uploads under a withdrawn grant
    are refused with SQLSTATE `WD001`.
  - A contributor can be created only for an auth user that exists.
- **Rights worker** (`pipeline/rights_worker.py`, hourly, 20-minute budget). It deletes rows and
  both buckets' objects, then deletes the auth user, and only then pseudonymizes the contributor
  and the attribution names on its grants. That is the only change a grant ever undergoes.
  - It is idempotent and retries after an hour.
  - A failed run opens an issue, and a request older than 25 days fails the run.
  - Every run also removes canonical objects that no photo row owns.
- **Export.** Withdrawn grants never publish, and withdrawals are re-read just before publishing.
  Photos publish only under the default pseudonym or an approved attribution, reviewed with
  `pipeline/attribution_review.py`.
- **Capture app: "Your data".**
  - Withdraw contributions, or delete the account, with typed confirmation and a status display.
  - Account deletion signs out every session.
  - Queued records carry their owner and are never sent as another or a new account. `WD001`
    records are dropped.
  - An anonymous account is upgraded in place when an e-mail is added.
  - Sampling rules and the age statement must be acknowledged before queueing.
- **Legal pack drafts** in `docs/legal/`, each marked "Draft — requires counsel review":
  - terms;
  - a privacy notice with a processor list;
  - the withdrawal and deletion procedure, including Hugging Face history;
  - the classroom and minors policy;
  - sampling and land-access rules.

## Acceptance criteria

- [x] Every criterion in BUILD_ORDER WP-6d has a test:
  - pgTAP `wp6d_rights`: 70 assertions.
  - pytest: rights worker, export, attribution review, QA compensation, and the processor scan,
    which fails if code names an external host that the privacy notice does not list.
  - vitest: Your data, the rights client, ownership and session errors, legal links, sampling
    rules.
- [x] Tests cover the changed behaviour, including every review finding below.
- [x] Local lint, typecheck, test, build and database tests pass (see Verification evidence).

## Invariant impact

- [x] I6: consent can be withdrawn, and deletion works end to end.
- [x] I7: withdrawn data leaves releases at once; residual data is disclosed.
- [x] I9: queued records stay with the account that made them.

## Business guardrails

- [x] B5: privacy is not for sale. Deletion and withdrawal are free and in-app, which both app
      stores require.

## Agent contribution

- [x] Written by Claude (Claude Opus 5.5), named in `Co-Authored-By` trailers. An independent agent
      review followed. Its findings were fixed in `18c4aba`, after the specification was amended
      first (`fe5111c` and `a35ec24` on `docs/spec-v3`).

Human of record: Justin Hart. **Sign-off pending:** an agent never certifies the DCO.

## Dependencies and deviations

None.

**Decisions for counsel**, listed in `docs/legal/README.md` and marked **[DECISION]** in each draft:

- controller details;
- minimum age and the classroom consent model;
- lawful bases;
- retention periods;
- international transfers;
- licence wording;
- Hugging Face history;
- governing law.

## Verification evidence

Run locally on `18c4aba`, 2026-10-11:

- `pnpm lint` and `pnpm typecheck` pass.
- vitest: schema 58, site 8, map 15, capture 73.
- ruff, mypy (29 files) and pytest (163) pass.
- pgTAP: prior_attempts 30/30, rls 42/42, wp6b_integrity 51/51, wp6d_rights 70/70.
- `deno check` passes.
- Playwright runs in CI on this pull request; at the stack's tip it passes 24/24 (desktop and mobile Chrome).

## Independent review and resolutions

The reviewer ran every suite plus probe scripts against a separate database. The verdict before the
fixes was "not mergeable"; all 18 findings are fixed.

| #     | Severity | Finding                                                                                                  | Resolution                                                                                                                                                                            |
| ----- | -------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | Blocker  | After an account deletion, another device recreated the contributor or re-uploaded its queue anonymously | Contributors require an existing auth user; no grant is accepted once deletion is requested; deletion signs out every session; queued records are held, never sent as another account |
| 2     | Major    | Observations accepted before a withdrawal but synced after it were published                             | Grants accepted at or before any request are refused (`WD001`), as is everything under a withdrawn grant; a cleared queue is never written back                                       |
| 3     | Major    | Withdrawals filed while the export ran were published                                                    | `honour_late_withdrawals()` re-reads before publishing, rebuilds once, and refuses to publish if more keep arriving                                                                   |
| 4     | Major    | Offline with an expired session, "Your data" said nothing was stored and wiped the queue                 | An unreadable session is a failure, never "nothing stored"                                                                                                                            |
| 5     | Major    | E-mail sign-in from an anonymous session stranded its contributions                                      | The anonymous account is upgraded in place; an e-mail already in use is reported                                                                                                      |
| 6     | Major    | Empty requests from throwaway accounts could starve the queue                                            | Requests with data are claimed first, empty withdrawals complete when filed, and the worker runs hourly within a budget                                                               |
| 7–8   | Minor    | The orphan sweep could race a new upload, and its listing did not scale                                  | `contributor_orphaned_objects()` decides orphans in one snapshot, 1,000 at a time                                                                                                     |
| 9     | Minor    | Retry timing and alerting                                                                                | Hourly schedule; failures open an issue; requests older than 25 days fail the run                                                                                                     |
| 10    | Minor    | `complete_deletion_request` could clear the auth id while the auth user still existed                    | It refuses until the auth user is gone                                                                                                                                                |
| 11    | Minor    | Residual data was undisclosed, and request rows could never be deleted                                   | The privacy notice discloses residual data; request rows can follow a retention policy                                                                                                |
| 12    | Minor    | Legal drafts overclaimed, and the processor scan was narrow                                              | Each claim corrected and Squarespace listed; the scan covers every shipped file                                                                                                       |
| 13    | Minor    | Panel accessibility                                                                                      | Focus management, always-mounted live regions, and `aria-describedby`                                                                                                                 |
| 14–18 | Nit      | Photo rows and uploads under a withdrawn grant; TRUNCATE; review CLI pagination; test gaps; link parsing | Refused by trigger and policy; TRUNCATE revoked and refused; paginated JSON round-trip; tests for every finding; links resolved like a browser                                        |

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_017nrzCzGuaW3XpYuuvMm7U1
