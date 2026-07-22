create schema if not exists extensions;
grant usage on schema extensions to anon, authenticated, service_role;

create extension if not exists postgis with schema extensions;
create extension if not exists pgcrypto with schema extensions;
