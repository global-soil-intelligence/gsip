update public.qa_events
set model_version = 'deterministic-v1'
where model_version is null;

alter table public.qa_events alter column model_version set default 'deterministic-v1';
alter table public.qa_events alter column model_version set not null;
alter table public.qa_events add constraint qa_events_model_version_length
    check (char_length(model_version) between 1 and 80);

comment on column public.qa_events.model_version is
    'Deterministic QA implementation that produced this event.';
