# Withdrawal and deletion procedure

> **Draft — requires counsel review.** Not in force. The mechanisms are implemented (WP-6d); the
> Hugging Face history policy is a **[DECISION]** point.

## What a contributor can ask for

| Request                       | Covers                                                                                                                                 |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Withdraw my contributions** | Every observation made under the grants the contributor holds when they ask. The account stays, and later observations are new grants. |
| **Delete my account**         | Every observation, the account itself, and the attribution names on the contributor's grants.                                          |

Both are made from **Your data** in the capture app and need explicit confirmation. A contributor
has at most one open request. Requests made in writing are filed by the steward after the person
proves control of the account by signing in.

## What happens, and when

1. **At once**, in the same database transaction as the request, every grant the contributor holds
   is withdrawn (`grant_withdrawals`, append-only). The nightly export leaves withdrawn grants out,
   so the next release no longer contains those observations. A withdrawn grant can never gain a new
   observation. The app also discards observations still queued on the device.
2. **Within a day** (the daily rights workflow; in any case within 30 days):
   - every observation under a withdrawn grant is deleted with its photo records, soil-map values,
     quality checks, jobs and any laboratory labels;
   - every photo object under the contributor's storage folder that no remaining observation owns is
     deleted from both private buckets;
   - for an account deletion, any grant created after the request is withdrawn too, the sign-in
     account is deleted, the contributor record is pseudonymized and unlinked from sign-in, attribution
     reviews are removed, and the attribution names on the contributor's grants are replaced with the
     default pseudonym.
3. **Kept as records:** each grant's identifier, terms version, acceptance date and licences, each
   withdrawal, and the request's kind and dates. They contain no observation, photograph or name.

Every step is idempotent. A failed step returns the request to the queue (retried after an hour)
with the step and error recorded for the operator, and the workflow run fails so the steward is
alerted. A canonical photo object that loses its record through any race is found and deleted on the
next run.

## Public releases and the map

- The next nightly release excludes the observations, and the public map cells are recomputed from
  it; a cell that falls below three contributors is withheld.
- Earlier releases remain in the dataset repository's history on Hugging Face. **[DECISION:]** the
  steward squashes that history (so earlier revisions are no longer served by GSIP) either monthly
  or within 30 days of a request.
- Copies others already downloaded under ODbL 1.0 and CC BY-SA 4.0 cannot be recalled.

## Operator checklist

1. The `Contributor rights requests` workflow runs daily. If it fails, read `last_error` on open
   `deletion_requests` (service role). Errors name the failed step (`apply`, `storage`, `auth` or
   `complete`) and HTTP status.
2. Fix the cause and re-run the workflow; never edit grants or withdrawals by hand (the database
   refuses it).
3. Requests older than 25 days are escalated to the steward.
