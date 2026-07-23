set pgrst.db_schemas = 'public';
select coalesce(json_agg(row_to_json(lint)), '[]'::json) from (
(
select
    'rls_enabled_no_policy' as name,
    'RLS Enabled No Policy' as title,
    'INFO' as level,
    'EXTERNAL' as facing,
    array['SECURITY'] as categories,
    'Detects cases where row level security (RLS) has been enabled on a table but no RLS policies have been created.' as description,
    format(
        'Table \`%s.%s\` has RLS enabled, but no policies exist',
        n.nspname,
        c.relname
    ) as detail,
    'https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy' as remediation,
    jsonb_build_object(
        'schema', n.nspname,
        'name', c.relname,
        'type', 'table'
    ) as metadata,
    format(
        'rls_enabled_no_policy_%s_%s',
        n.nspname,
        c.relname
    ) as cache_key
from
    pg_catalog.pg_class c
    left join pg_catalog.pg_policy p
        on p.polrelid = c.oid
    join pg_catalog.pg_namespace n
        on c.relnamespace = n.oid
    left join pg_catalog.pg_depend dep
        on c.oid = dep.objid
        and dep.deptype = 'e'
        and dep.classid = 'pg_catalog.pg_class'::regclass
where
    c.relkind = 'r' -- regular tables
    and n.nspname not in (
        '_timescaledb_cache', '_timescaledb_catalog', '_timescaledb_config', '_timescaledb_internal', 'auth', 'cron', 'extensions', 'graphql', 'graphql_public', 'information_schema', 'net', 'pgmq', 'pgroonga', 'pgsodium', 'pgsodium_masks', 'pgtle', 'pgbouncer', 'pg_catalog', 'realtime', 'repack', 'storage', 'supabase_functions', 'supabase_migrations', 'tiger', 'topology', 'vault'
    )
    -- RLS is enabled
    and c.relrowsecurity
    and p.polname is null
    and dep.objid is null -- exclude tables owned by extensions
group by
    n.nspname,
    c.relname)
union all
(
-- Detects SECURITY DEFINER functions that the `anon` role has EXECUTE
-- on. SECURITY DEFINER functions run with the privileges of their
-- owner (typically a superuser-equivalent role) rather than the
-- caller, so they bypass RLS on every table they read or write.
-- Granting EXECUTE to `anon` therefore lets any holder of the public
-- anon key invoke a privileged operation through PostgREST
-- `/rest/v1/rpc/<name>`, and through `/graphql/v1` Query/Mutation
-- fields when pg_graphql is installed and the return type is
-- supported.
--
-- See lint 0029 for the equivalent check against the `authenticated`
-- role. Together with 0026/0027 they cover the four direct
-- exposure paths: anon-vs-authenticated × table-vs-function.
--
-- This lint deliberately does not gate on pg_graphql being installed:
-- PostgREST exposes `/rest/v1/rpc` independently and is the more
-- commonly deployed surface for the same risk.
select
    'anon_security_definer_function_executable' as name,
    'Public Can Execute SECURITY DEFINER Function' as title,
    'WARN' as level,
    'EXTERNAL' as facing,
    array['SECURITY'] as categories,
    'Detects `SECURITY DEFINER` functions that are callable without signing in. Revoke `EXECUTE`, switch the function to `SECURITY INVOKER`, or move it out of your exposed API schema if it is not meant to be public.' as description,
    format(
        'Function `%s.%s(%s)` can be executed by the `anon` role as a `SECURITY DEFINER` function via `/rest/v1/rpc/%s`. Revoke `EXECUTE` or switch it to `SECURITY INVOKER` if that is not intentional.',
        schema_name,
        function_name,
        function_args,
        function_name
    ) as detail,
    'https://supabase.com/docs/guides/database/database-linter?lint=0028_anon_security_definer_function_executable' as remediation,
    jsonb_build_object(
        'schema', schema_name,
        'name', function_name,
        'arguments', function_args,
        'language', function_language,
        'security_definer', true
    ) as metadata,
    format(
        'anon_security_definer_function_executable_%s_%s_%s',
        schema_name,
        function_name,
        function_args
    ) as cache_key
from
    (
        select
            n.nspname as schema_name,
            p.proname as function_name,
            pg_catalog.pg_get_function_identity_arguments(p.oid) as function_args,
            l.lanname as function_language
        from
            pg_catalog.pg_proc p
            join pg_catalog.pg_namespace n
                on p.pronamespace = n.oid
            join pg_catalog.pg_language l
                on p.prolang = l.oid
        where
            p.prosecdef = true
            and pg_catalog.has_function_privilege('anon', p.oid, 'EXECUTE')
            and n.nspname = any(array(select trim(unnest(string_to_array(coalesce(current_setting('pgrst.db_schemas', 't'), 'public'), ',')))))
            and n.nspname not in (
                '_timescaledb_cache', '_timescaledb_catalog', '_timescaledb_config', '_timescaledb_internal', 'auth', 'cron', 'extensions', 'graphql', 'graphql_public', 'information_schema', 'net', 'pgmq', 'pgroonga', 'pgsodium', 'pgsodium_masks', 'pgtle', 'pgbouncer', 'pg_catalog', 'realtime', 'repack', 'storage', 'supabase_functions', 'supabase_migrations', 'tiger', 'topology', 'vault'
            )
    ) exposed_functions
order by
    schema_name,
    function_name,
    function_args)
union all
(
-- Detects SECURITY DEFINER functions that the `authenticated` role
-- has EXECUTE on. SECURITY DEFINER functions run with the privileges
-- of their owner (typically a superuser-equivalent role) rather than
-- the caller, so they bypass RLS on every table they read or write.
-- Granting EXECUTE to `authenticated` therefore lets any signed-up
-- user invoke a privileged operation through PostgREST
-- `/rest/v1/rpc/<name>`, and through `/graphql/v1` Query/Mutation
-- fields when pg_graphql is installed and the return type is
-- supported. Under open or auto-confirm signup, "authenticated" is in
-- practice anyone with a throwaway email.
--
-- See lint 0028 for the equivalent check against the `anon` role.
-- Together with 0026/0027 they cover the four direct exposure paths:
-- anon-vs-authenticated × table-vs-function.
--
-- This lint deliberately does not gate on pg_graphql being installed:
-- PostgREST exposes `/rest/v1/rpc` independently and is the more
-- commonly deployed surface for the same risk.
select
    'authenticated_security_definer_function_executable' as name,
    'Signed-In Users Can Execute SECURITY DEFINER Function' as title,
    'WARN' as level,
    'EXTERNAL' as facing,
    array['SECURITY'] as categories,
    'Detects `SECURITY DEFINER` functions that are callable by signed-in users. Revoke `EXECUTE`, switch the function to `SECURITY INVOKER`, or move it out of your exposed API schema if signed-in users should not call it.' as description,
    format(
        'Function `%s.%s(%s)` can be executed by the `authenticated` role as a `SECURITY DEFINER` function via `/rest/v1/rpc/%s`. Revoke `EXECUTE` or switch it to `SECURITY INVOKER` if that is not intentional.',
        schema_name,
        function_name,
        function_args,
        function_name
    ) as detail,
    'https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable' as remediation,
    jsonb_build_object(
        'schema', schema_name,
        'name', function_name,
        'arguments', function_args,
        'language', function_language,
        'security_definer', true
    ) as metadata,
    format(
        'authenticated_security_definer_function_executable_%s_%s_%s',
        schema_name,
        function_name,
        function_args
    ) as cache_key
from
    (
        select
            n.nspname as schema_name,
            p.proname as function_name,
            pg_catalog.pg_get_function_identity_arguments(p.oid) as function_args,
            l.lanname as function_language
        from
            pg_catalog.pg_proc p
            join pg_catalog.pg_namespace n
                on p.pronamespace = n.oid
            join pg_catalog.pg_language l
                on p.prolang = l.oid
        where
            p.prosecdef = true
            and pg_catalog.has_function_privilege('authenticated', p.oid, 'EXECUTE')
            and n.nspname = any(array(select trim(unnest(string_to_array(coalesce(current_setting('pgrst.db_schemas', 't'), 'public'), ',')))))
            and n.nspname not in (
                '_timescaledb_cache', '_timescaledb_catalog', '_timescaledb_config', '_timescaledb_internal', 'auth', 'cron', 'extensions', 'graphql', 'graphql_public', 'information_schema', 'net', 'pgmq', 'pgroonga', 'pgsodium', 'pgsodium_masks', 'pgtle', 'pgbouncer', 'pg_catalog', 'realtime', 'repack', 'storage', 'supabase_functions', 'supabase_migrations', 'tiger', 'topology', 'vault'
            )
    ) exposed_functions
order by
    schema_name,
    function_name,
    function_args)
) lint;
