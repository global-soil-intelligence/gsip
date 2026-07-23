select jsonb_build_object(
'observed_at_utc',to_char(clock_timestamp() at time zone 'UTC','YYYY-MM-DD HH24:MI:SS.US') || ' UTC',
'public_cells', (select count(*) from public.h3_cells),
'k_anonymity_violations',(select count(*) from public.h3_cells where n_contributors is null or n_contributors < 3 or n_submissions is null or n_submissions < n_contributors or resolution is null or resolution not in (4,6,8) or h3_index is null or h3_index !~ ('^8' || to_hex(resolution::integer) || '[0-9a-f]{13}$')),
'prior_cache_rows',(select count(*) from public.prior_cell_cache),
'prior_jobs_nonempty_new_empty_sources',(select count(*) from public.prior_jobs where empty_sources is distinct from '{}'::text[]),
'upstream_bucket_rows',(select count(*) from public.upstream_buckets),
'upstream_bucket_config_mismatch',(select count(*) from public.upstream_buckets b full join (values ('soilgrids',1,5::numeric,1::numeric),('ssurgo',30,30::numeric,30::numeric),('open_meteo',60,60::numeric,60::numeric)) e(source,capacity,refill_per_minute,tokens) on b.source=e.source where b.source is null or e.source is null or b.capacity is distinct from e.capacity or b.refill_per_minute is distinct from e.refill_per_minute or b.tokens is distinct from e.tokens)
) as checks;
