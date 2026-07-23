begin read only;
select jsonb_build_object(
  'capture_open', (select capture_open from public.service_state where singleton),
  'migration_count', (select count(*) from supabase_migrations.schema_migrations),
  'migrations', (select jsonb_agg(jsonb_build_object('version', version, 'name', name) order by version) from supabase_migrations.schema_migrations),
  'counts', jsonb_build_object(
    'contributors', (select count(*) from public.contributors),
    'submissions', (select count(*) from public.submissions),
    'photos', (select count(*) from public.photos),
    'auth_users', (select count(*) from auth.users),
    'public_cells', (select count(*) from public.h3_cells)
  ),
  'library_columns', (select coalesce(jsonb_agg(jsonb_build_object('schema',table_schema,'table',table_name,'column',column_name,'type',data_type) order by table_schema,table_name,ordinal_position),'[]'::jsonb) from information_schema.columns where table_schema in ('public','private') and table_name like '%library%')
) as readiness;
commit;
