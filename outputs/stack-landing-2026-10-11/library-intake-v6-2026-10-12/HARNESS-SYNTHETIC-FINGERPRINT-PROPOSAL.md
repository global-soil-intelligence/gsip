# One additional historical synthetic fingerprint: approval required

The full-history gitleaks 8.21.2 scan reports exactly one new finding in an immutable reviewed-stack descendant. It is the noncredential browser fixture for the fixed reserved `.test` endpoint. The fixture is being shortened, without changing what the browser tests prove. No real key, user session or production secret is involved.

Proposed difference from the existing four lines (which remain unchanged):

```diff
+bb9bd8a583231ff63ec14a7622532ddb869d7cde:scripts/e2e_server.py:generic-api-key:32
```

Only this exact historical fingerprint is proposed. No scanner configuration, detection rule, redaction, full-history coverage, workflow or future-match exemption changes. No suppression has been applied. Justin's explicit instruction requires approval for every further suppression. History rewriting is prohibited, so fixture cleanup cannot remove the historical finding. All further merges are held.
