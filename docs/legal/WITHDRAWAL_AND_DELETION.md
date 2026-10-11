# Withdrawal and deletion procedure

> **Draft — requires counsel review.** Not in force. The mechanisms are implemented (WP-6d); the
> Hugging Face history policy is a **[DECISION]** point.

## What a contributor can ask for

| Request                       | Covers                                                                                                                                                       |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Withdraw my contributions** | Every observation the contributor accepted the terms for up to the moment they ask, including observations still queued on their devices. The account stays. |
| **Delete my account**         | Every observation, whenever made, the sign-in account, and the attribution names on the contributor's grants.                                                |

Both are made from **Your data** in the capture app and need the confirmation word typed. A
contributor has at most one open request. Requests made in writing are filed by the steward after
the person proves control of the account by signing in. Anonymous contributors who later add an
e-mail address keep the same account, so they can make the request from any device; a person who
signs in to a different account must withdraw the anonymous contributions from the device that made
them.

## What happens, and when

1. **At once**, in the same database transaction as the request:
   - every grant the contributor holds is withdrawn (`grant_withdrawals`, append-only);
   - from then on the database refuses any grant accepted at or before the request (an observation
     queued on another device that syncs later), any grant at all once an account deletion is
     requested, and any new observation, photo record or upload under a withdrawn grant. The app
     drops refused observations from that device's queue;
   - the filing device discards the observations still queued on it, and after an account deletion
     every session of the account is revoked, so other devices stop sending within the hour.
     Observations queued on another device under the deleted account are kept there, unsent,
     until the person discards them.
2. **Releases:** the export leaves withdrawn grants out, and just before publishing it reads the
   withdrawals again and rebuilds without any that arrived while it ran (or refuses to publish if
   they keep arriving). A release built after the request therefore never contains the
   observations.
3. **Within the hour** (the hourly rights workflow; in any case within 30 days):
   - every observation under a withdrawn grant is deleted with its photo records, soil-map values,
     quality checks, jobs and any laboratory labels;
   - every photo object in either private bucket under the contributor's storage folder that no
     remaining observation owns is deleted;
   - for an account deletion, any remaining grant is withdrawn, the sign-in account is deleted, and
     only then is the contributor record pseudonymized and unlinked from sign-in, attribution reviews
     removed, and the attribution names on the contributor's grants replaced with the default
     pseudonym.
4. **Kept as records:** each grant's identifier, terms version, acceptance date and licences, each
   withdrawal, the pseudonymized contributor record (a random identifier), and the request's kind and
   dates (which may be deleted under the retention policy without touching the withdrawals). None of
   them holds an observation, a photograph or a name. Outside GSIP's control: Supabase's backups and
   sign-in audit log for their retention periods, and copies others have downloaded.

Every step is idempotent. A failed step returns the request to the queue, to be retried after an
hour, with the step and error recorded for the operator; the run fails and opens (or comments on) an
issue titled "Contributor rights worker is failing". Requests with data are processed before empty
ones, so a flood of empty requests cannot delay a real one. Any canonical photo object that loses
its record through a race is found and deleted on the next run.

## Public releases and the map

- Releases built after the request exclude the observations, and the public map cells are
  recomputed from each release; a cell that falls below three contributors is withheld.
- Earlier releases remain in the dataset repository's history on Hugging Face. **[DECISION:]** the
  steward squashes that history (so earlier revisions are no longer served by GSIP) either monthly
  or within 30 days of a request.
- Copies others already downloaded under ODbL 1.0 and CC BY-SA 4.0 cannot be recalled.

## Operator checklist

1. The `Contributor rights requests` workflow runs hourly. When it fails, read `last_error` on open
   `deletion_requests` (service role). Errors name the failed step (`apply`, `storage`, `auth` or
   `complete`) and the HTTP status.
2. Fix the cause and re-run the workflow; never edit grants or withdrawals by hand (the database
   refuses it).
3. The run also fails when any request is older than 25 days: escalate it to the steward at once.
4. GitHub disables scheduled workflows in a public repository after 60 days without activity. Check
   monthly that the workflow is enabled.
