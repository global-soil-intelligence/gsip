-- WP-AGENT-1 (I12): the anonymous role, which every agent interface uses, reads the public
-- surfaces and nothing else; dataset releases are public, append-only records.
begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;

select no_plan();

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
       and p.oid not in ('public.capture_is_open()'::regprocedure,
           'public.library_intake_capabilities()'::regprocedure,
           'private.library_intake_capabilities()'::regprocedure,
           'public.collection_pilot_capabilities()'::regprocedure,
           'private.collection_pilot_capabilities()'::regprocedure)),
    0::bigint,
    'anonymous execution is limited to exact capture/library/pilot capability signatures'
);

select results_eq(
    $$select key from jsonb_object_keys(public.library_intake_capabilities()) key order by key$$,
    $$values ('available'::text), ('version'::text)$$,
    'anonymous library capabilities expose only availability and contract version'
);
select ok(
    not has_function_privilege('anon', 'public.record_library_intake(jsonb)', 'execute')
    and not has_function_privilege('anon', 'public.my_library_intake_receipt(uuid)', 'execute')
    and not has_function_privilege('anon', 'public.set_library_intake_open(boolean)', 'execute'),
    'anonymous capability read grants no intake, receipt or activation authority'
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
-- Transaction-local shape clone preserves unique/version/revision constraint regression.
create temporary table release_shape (like public.dataset_releases including all);
insert into release_shape(version,rows,photos,hf_revision)
values('2026-10-11',120,236,'0123456789abcdef0123456789abcdef01234567');
select throws_ok($$insert into release_shape(version,rows,photos,hf_revision) values('2026-10-11',120,236,'0123456789abcdef0123456789abcdef01234567')$$,'23505',null,'release shape still refuses duplicate exact commits');
insert into release_shape(version,rows,photos) values('2026-10-10',5,9) on conflict(version,hf_revision) do nothing;
insert into release_shape(version,rows,photos) values('2026-10-10',5,9) on conflict(version,hf_revision) do nothing;
select is((select count(*) from release_shape where version='2026-10-10'),1::bigint,'release shape retry without revision remains idempotent');
select throws_ok($$insert into release_shape(version,rows,photos,hf_revision) values('2026-10-11',1,1,'main')$$,'23514',null,'release shape requires exact revision');
select throws_ok($$insert into release_shape(version,rows,photos) values('latest',1,1)$$,'23514',null,'release shape requires a dated version');
set local role service_role;
select throws_ok($$insert into public.dataset_releases(version,rows,photos,hf_revision) values('2026-10-11',120,236,'0123456789abcdef0123456789abcdef01234567')$$,'CP001',null,'even a valid service-role public release is held');
reset role;
set local role anon;
set local "request.jwt.claims" = '{"role":"anon"}';
select is((select count(*) from public.dataset_releases),0::bigint,'anonymous readers see no new held release');
select throws_ok(
    $$select geom_precise from public.submissions$$,
    '42501',
    null,
    'and still nothing private'
);
reset role;

select * from finish();
rollback;
