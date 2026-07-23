do $test$
declare checks integer:=0;
begin
if (select count(*) from public.contributors)<>2 then raise exception 'contributors changed'; end if; checks:=checks+1;
if (select count(*) from public.contribution_grants)<>2 then raise exception 'grants changed'; end if; checks:=checks+1;
if (select count(*) from public.submissions where is_synthetic and provenance_tier=-1 and actor_id is not null)<>2 then raise exception 'synthetic submission provenance failed'; end if; checks:=checks+1;
if (select count(*) from public.photos where provenance_tier=-1 and qa_status='pass')<>4 then raise exception 'photo backfill failed'; end if; checks:=checks+1;
if (select count(*) from public.submissions where finalized_at is not null)<>2 then raise exception 'legacy finalization failed'; end if; checks:=checks+1;
if (select count(*) from public.actors where kind='human' and status='active' and operator_id is null)<>2 then raise exception 'actor backfill failed'; end if; checks:=checks+1;
if (select count(*) from public.service_state where not capture_open)<>1 then raise exception 'capture gate not closed'; end if; checks:=checks+1;
if (select count(*) from public.contribution_grants where received_at is null)<>2 then raise exception 'legacy receipts rewritten'; end if; checks:=checks+1;
if checks<>8 then raise exception 'post-migration assertion count mismatch'; end if;
raise notice 'POST_PROOF %',checks;
end;
$test$;
