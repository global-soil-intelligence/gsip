drop policy gold_labels_select_own on public.gold_labels;
create policy gold_labels_select_own on public.gold_labels for select to authenticated using ((submission_id IN ( SELECT s.id
   FROM public.submissions s
  WHERE (s.contributor_id = public.current_contributor_id()))));
drop policy photos_insert_own on public.photos;
create policy photos_insert_own on public.photos for insert to authenticated with check ((submission_id IN ( SELECT s.id
   FROM public.submissions s
  WHERE (s.contributor_id = public.current_contributor_id()))));
drop policy photos_select_own on public.photos;
create policy photos_select_own on public.photos for select to authenticated using ((submission_id IN ( SELECT s.id
   FROM public.submissions s
  WHERE (s.contributor_id = public.current_contributor_id()))));
drop policy predictions_select_own on public.predictions;
create policy predictions_select_own on public.predictions for select to authenticated using ((submission_id IN ( SELECT s.id
   FROM public.submissions s
  WHERE (s.contributor_id = public.current_contributor_id()))));
drop policy priors_select_own on public.priors;
create policy priors_select_own on public.priors for select to authenticated using ((submission_id IN ( SELECT s.id
   FROM public.submissions s
  WHERE (s.contributor_id = public.current_contributor_id()))));
drop policy qa_events_select_own on public.qa_events;
create policy qa_events_select_own on public.qa_events for select to authenticated using ((submission_id IN ( SELECT s.id
   FROM public.submissions s
  WHERE (s.contributor_id = public.current_contributor_id()))));
