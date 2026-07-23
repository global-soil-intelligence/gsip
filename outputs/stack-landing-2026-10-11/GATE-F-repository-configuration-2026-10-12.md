# Gate F: repository configuration — prepared only

Target repository: global-soil-intelligence/gsip. Supabase target remains toxldjgwkxtneoqsazym. No settings changed. Separate Justin go is required.

Invariants: no deploy or workflow dispatch; workers disabled; Pages still requires Justin approval without admin bypass; capture/sign-up/anonymous off; no key values printed or supplied in chat; no secret read. The existing publishable key stays intact. No new service or dependency.

Read-only preparation found exactly two variables: VITE_SUPABASE_URL (matches the target project) and VITE_SUPABASE_PUBLISHABLE_KEY (publishable format). No repository Actions secrets are present. Refreshed readback is required before mutation.

After a separate go, these are the two proposed commands, one at a time with readback:

```sh
gh variable set SUPABASE_URL --repo global-soil-intelligence/gsip --body 'https://toxldjgwkxtneoqsazym.supabase.co'
gh variable set VITE_GSIP_PUBLIC_API --repo global-soil-intelligence/gsip --body 'https://toxldjgwkxtneoqsazym.supabase.co/functions/v1/gsip-public'
```

Verify exact URLs, existing publishable key unchanged using a value hash in memory, only these two variable additions, and no workflow dispatch. Do not reset the existing key just to satisfy a set instruction.

Justin action: add SUPABASE_SERVICE_ROLE_KEY directly under repository Actions secrets. Never send it in chat. Afterwards the agent verifies its name exists; no secret value is accessible or needed for that verification. HF credentials remain separate and export stays held.

Old variable retirement is deferred until owner merges the hardening workflow update: current main's Pages/photo QA/export workflows still reference vars.VITE_SUPABASE_URL. Deleting it now would break those workflows. After the merge, freshly fetch main and prove no workflow still references that repository variable before presenting/running its separately approved removal:

```sh
gh variable delete VITE_SUPABASE_URL --repo global-soil-intelligence/gsip
```

No merge is authorized or performed. Remaining prerequisite is Justin review/merge; existing protected Pages deployment will still require his approval.

Assumptions: Gate E authorization covered its two named deployments only; this document is preparation, not execution. Retaining the old URL until consumers migrate is a sequencing requirement supported by the current main workflow contents, not a change to the final required variable names. No new decisions are needed about project, key format or API destination.
