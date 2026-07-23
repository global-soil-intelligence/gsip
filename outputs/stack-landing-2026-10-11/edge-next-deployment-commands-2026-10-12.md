Prepared, not executed. Target: `toxldjgwkxtneoqsazym` (`gsip`); source `f9e1ac2f8a88671f99b959e476499392297bd30f`; Supabase CLI2.118.0. Separate Justin go required after database postchecks.

```sh
'/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/repo/node_modules/.bin/supabase' functions deploy prior-attach --project-ref toxldjgwkxtneoqsazym --import-map '/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/repo/supabase/functions/deno.json' --use-api --workdir '/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/repo'
'/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/repo/node_modules/.bin/supabase' functions deploy gsip-public --project-ref toxldjgwkxtneoqsazym --import-map '/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/repo/supabase/functions/deno.json' --use-api --workdir '/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/repo' --no-verify-jwt
```

Read-only post-deploy verification:

```sh
'/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/repo/node_modules/.bin/supabase' functions list --project-ref toxldjgwkxtneoqsazym --workdir '/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/repo' --output json
python3 '/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/edge-next-readonly-smoke-2026-10-12.py'
```

JWT metadata must show `prior-attach=true`, `gsip-public=false`. Smoke acceptance:401/200/400/4tools. No credential values, signup/capture changes, worker dispatch or Pages deployment.
