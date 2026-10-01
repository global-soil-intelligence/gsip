# Prior-attach worker

`prior-attach` is a JWT-protected Supabase Edge Function. Every new submission receives a durable
`prior_jobs` row from the database trigger; the capture client then invokes the function immediately.
The function verifies ownership through RLS before its service-role client can read or write anything.
A five-minute service-role drain also retries pending and dead-letter jobs, so enrichment does not depend
on the capture tab staying open or the best-effort client invocation succeeding.

It retrieves SoilGrids mean/Q05/Q95 for the native 0–5, 5–15 and 15–30 cm layers, stores the native
0–5 cm result, and computes the specified 0–30 cm profile as a thickness-weighted aggregate. In CONUS,
available major-component SSURGO horizon values are also thickness/component weighted. Open-Meteo
provides GLO-90 elevation and a recent-precipitation flag, defined as at least 1 mm total over the three
previous daily periods.

Four bounded upstream attempts use exponential backoff. Each source is fetched and stored independently,
so a SoilGrids outage does not discard successful elevation, precipitation, or SSURGO results. A partial
run records the failed source names as `dead_letter`; the scheduled drain retries up to the durable job's
32-run cap. Rerunning is safe because prior rows upsert on the schema's canonical composite key. CI parses
recorded responses only and makes no live API calls.
