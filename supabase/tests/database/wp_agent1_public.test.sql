-- WP-AGENT-1 (I12): the anonymous role, which every agent interface uses, reads the public
-- surfaces and nothing else; dataset releases are public, append-only records.
begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;

select plan(11);

-- Every table and view in the public schema that the anonymous role can read, at table or column
-- level. A new table readable by anon fails here until it is reviewed and listed.
select results_eq(
    $$select c.relname::text collate "default"
      from pg_class c join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'public' and c.relkind in ('r', 'v', 'm', 'p', 'f')
        and (
            has_table_privilege('anon', c.oid, 'select')
            or exists (
                select 1 from pg_attribute a
                where a.attrelid = c.oid and a.attnum > 0 and not a.attisdropped
                  and has_column_privilege('anon', c.oid, a.attnum, 'select')
            )
        )
      order by 1$$,
    $$values ('dataset_releases'::text), ('h3_cells'::text), ('service_state'::text), ('terms_versions'::text)$$,
    'the anonymous role reads only releases, published cells, the capture switch and terms versions'
);
select ok(
    not has_table_privilege('anon', 'public.service_state', 'select')
    and (select array_agg(a.attname::text collate "default" order by a.attname)
         from pg_attribute a
         where a.attrelid = 'public.service_state'::regclass and a.attnum > 0 and not a.attisdropped
           and has_column_privilege('anon', 'public.service_state', a.attname, 'select'))
        = array['capture_open', 'updated_at'],
    'of the capture switch, only whether capture is open and when it changed'
);
select is(
    (select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
     where n.nspname in ('public', 'private')
       and has_function_privilege('anon', p.oid, 'execute')
       and p.proname <> 'capture_is_open'),
    0::bigint,
    'the anonymous role executes no GSIP function except capture_is_open'
);

-- Releases.
select ok(
    not has_table_privilege('anon', 'public.dataset_releases', 'insert')
    and not has_table_privilege('authenticated', 'public.dataset_releases', 'insert')
    and not has_table_privilege('service_role', 'public.dataset_releases', 'update')
    and not has_table_privilege('service_role', 'public.dataset_releases', 'delete')
    and not has_table_privilege('service_role', 'public.dataset_releases', 'truncate'),
    'only the server records a release, and nobody rewrites one'
);
set local role service_role;
select lives_ok(
    $$insert into public.dataset_releases (version, rows, photos, hf_revision)
      values ('2026-10-11', 120, 236, '0123456789abcdef0123456789abcdef01234567')$$,
    'the export records a release'
);
insert into public.dataset_releases (version, rows, photos, hf_revision)
values ('2026-10-11', 120, 236, '0123456789abcdef0123456789abcdef01234567')
on conflict (version, hf_revision) do nothing;
select is(
    (select count(*) from public.dataset_releases),
    1::bigint,
    'retrying the record of the same push adds nothing'
);
select throws_ok(
    $$insert into public.dataset_releases (version, rows, photos, hf_revision)
      values ('2026-10-11', 120, 236, '0123456789abcdef0123456789abcdef01234567')$$,
    '23505',
    null,
    'a pushed commit is recorded once'
);
select throws_ok(
    $$insert into public.dataset_releases (version, rows, photos, hf_revision)
      values ('2026-10-11', 1, 1, 'main')$$,
    '23514',
    null,
    'a release names an exact Hugging Face commit'
);
select throws_ok(
    $$insert into public.dataset_releases (version, rows, photos) values ('latest', 1, 1)$$,
    '23514',
    null,
    'a release version is its export date'
);
reset role;
set local role anon;
set local "request.jwt.claims" = '{"role":"anon"}';
select results_eq(
    $$select version, rows, photos, hf_revision from public.dataset_releases$$,
    $$values ('2026-10-11'::text, 120, 236, '0123456789abcdef0123456789abcdef01234567'::text)$$,
    'anyone reads the releases'
);
select throws_ok(
    $$select geom_precise from public.submissions$$,
    '42501',
    null,
    'and still nothing private'
);
reset role;

select * from finish();
rollback;
