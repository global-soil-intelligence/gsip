do $test$
    declare
      uid uuid; own_submission uuid; foreign_submission uuid;
      object text; visible integer; expected integer; checks integer := 0;
    begin
      for owner in 1..2 loop
        uid := ('ee000000-0000-4000-8000-00000000000' || owner)::uuid;
        own_submission := ('bb000000-0000-4000-8000-00000000000' || owner)::uuid;
        foreign_submission := ('bb000000-0000-4000-8000-00000000000' || (3-owner))::uuid;
        execute 'set local role authenticated';
        perform set_config('request.jwt.claim.sub',uid::text,true);
        foreach object in array array['photos','priors','gold_labels','predictions','qa_events'] loop
          execute format('select count(*) from public.%I',object) into visible;
          expected := case when object='photos' then 2 else 1 end;
          if visible <> expected then raise exception 'synthetic own-row visibility failed for %',object; end if;
          checks := checks+1;
        end loop;
        -- The artificial exception rolls back the successful own insert and its QA job.
        begin
          insert into public.photos(submission_id,shot_type,storage_path)
          values(own_submission,'C','synthetic-local-proof-own-insert');
          checks := checks+1;
          raise exception 'rollback synthetic own insert' using errcode='P9999';
        exception when sqlstate 'P9999' then null;
        end;
        begin
          insert into public.photos(submission_id,shot_type,storage_path)
          values(foreign_submission,'C','synthetic-local-proof-foreign-insert');
          raise exception 'foreign photo insert unexpectedly succeeded';
        exception when insufficient_privilege then checks := checks+1;
        end;
        execute 'reset role';
      end loop;
      execute 'set local role authenticated';
      perform set_config('request.jwt.claim.sub','ee000000-0000-4000-8000-000000000009',true);
      select count(*) into visible from public.photos;
      if visible <> 0 then raise exception 'unlinked synthetic actor sees private rows'; end if;
      checks := checks+1;
      begin
        update public.photos set camera_metadata_private='{}'::jsonb;
        raise exception 'client metadata write unexpectedly succeeded';
      exception when insufficient_privilege then checks := checks+1;
      end;
      foreach object in array array['prior_jobs','qa_jobs'] loop
        begin
          execute format('select count(*) from public.%I',object) into visible;
          raise exception 'client queue read unexpectedly succeeded';
        exception when insufficient_privilege then checks := checks+1;
        end;
      end loop;
      execute 'reset role';
      execute 'set local role anon';
      begin
        select count(*) into visible from public.photos;
        raise exception 'anonymous photo read unexpectedly succeeded';
      exception when insufficient_privilege then checks := checks+1;
      end;
      begin
        perform geom_precise from public.submissions;
        raise exception 'anonymous geometry read unexpectedly succeeded';
      exception when insufficient_privilege then checks := checks+1;
      end;
      execute 'reset role';
      if checks <> 20 then raise exception 'unexpected RLS assertion count %',checks; end if;
      raise notice 'RLS_PROOF canonical %',checks;
    end;
    $test$;
