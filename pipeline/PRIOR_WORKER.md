# Prior-attach worker

`prior-attach` is a JWT-protected Supabase Edge Function. Every new submission receives a durable
`prior_jobs` row from the database trigger; the capture client then invokes the function immediately.
The function verifies ownership through RLS before its service-role client can read or write anything.

It retrieves SoilGrids mean/Q05/Q95 for the native 0–5, 5–15 and 15–30 cm layers, stores the native
0–5 cm result, and computes the specified 0–30 cm profile as a thickness-weighted aggregate. In CONUS,
available major-component SSURGO horizon values are also thickness/component weighted. Open-Meteo
provides GLO-90 elevation and a recent-precipitation flag, defined as at least 1 mm total over the three
previous daily periods.

Four bounded attempts use exponential backoff. Exhaustion records `dead_letter`; rerunning is safe
because prior rows upsert on the schema's canonical composite key. CI parses recorded responses only and
makes no live API calls.
