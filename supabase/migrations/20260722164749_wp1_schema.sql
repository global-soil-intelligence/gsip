create table public.contributors (
    id uuid primary key default gen_random_uuid(),
    auth_uid uuid unique,
    handle text unique not null check (char_length(handle) between 3 and 32),
    reputation integer not null default 0,
    precise_location_optin boolean not null default false,
    terms_version text,
    terms_accepted_at timestamptz,
    created_at timestamptz not null default now(),
    constraint terms_recorded_together
        check ((terms_version is null) = (terms_accepted_at is null))
);

create table public.submissions (
    id uuid primary key default gen_random_uuid(),
    contributor_id uuid not null references public.contributors (id),
    geom_precise extensions.geometry (point, 4326) not null,
    h3_r8 text not null check (h3_r8 ~ '^[0-9a-f]{15}$'),
    h3_r6 text not null check (h3_r6 ~ '^[0-9a-f]{15}$'),
    captured_at timestamptz not null,
    land_cover text check (
        land_cover in ('cropland', 'grassland', 'forest', 'shrubland', 'wetland', 'urban', 'bare')
    ),
    surface_condition text check (surface_condition in ('dry', 'moist', 'wet')),
    disturbed boolean,
    device_model text,
    precip_flag boolean,
    elevation real,
    status text not null default 'pending'
        check (status in ('pending', 'qa_pass', 'qa_fail', 'flagged'))
);

create index submissions_h3_r8_idx on public.submissions (h3_r8);
create index submissions_contributor_idx on public.submissions (contributor_id);
create index submissions_status_idx on public.submissions (status);

create table public.photos (
    id uuid primary key default gen_random_uuid(),
    submission_id uuid not null references public.submissions (id) on delete cascade,
    shot_type text not null check (shot_type in ('A', 'B', 'C')),
    storage_path text not null,
    exif jsonb,
    card_detected boolean,
    card_color_correction jsonb,
    sharpness_score real
);

create index photos_submission_idx on public.photos (submission_id);

create table public.priors (
    submission_id uuid not null references public.submissions (id) on delete cascade,
    source text not null check (source in ('soilgrids', 'ssurgo', 'wosis')),
    property text not null
        check (property in ('soc', 'ph', 'clay', 'sand', 'silt', 'bd', 'cec', 'n')),
    value double precision,
    uncertainty_lo double precision,
    uncertainty_hi double precision,
    source_depth text not null,
    retrieved_at timestamptz not null default now(),
    primary key (submission_id, source, property, source_depth)
);

create table public.gold_labels (
    id uuid primary key default gen_random_uuid(),
    submission_id uuid not null references public.submissions (id) on delete cascade,
    lab_name text not null,
    method text,
    property text not null
        check (property in ('soc', 'ph', 'clay', 'sand', 'silt', 'bd', 'cec', 'n')),
    value double precision not null,
    uncertainty double precision,
    sampled_depth text,
    verified_by text,
    document_ref text
);

create index gold_labels_submission_idx on public.gold_labels (submission_id);

create table public.predictions (
    id uuid primary key default gen_random_uuid(),
    submission_id uuid not null references public.submissions (id) on delete cascade,
    model_version text not null,
    property text not null
        check (property in ('soc', 'ph', 'clay', 'sand', 'silt', 'bd', 'cec', 'n')),
    value double precision not null,
    ci_lo double precision not null,
    ci_hi double precision not null,
    basis text not null check (basis in ('image', 'prior', 'fused', 'neighbors')),
    constraint value_within_ci check (ci_lo <= value and value <= ci_hi)
);

create index predictions_submission_idx on public.predictions (submission_id);

create table public.qa_events (
    submission_id uuid not null references public.submissions (id) on delete cascade,
    check_name text not null,
    passed boolean not null,
    score double precision,
    model_version text,
    primary key (submission_id, check_name)
);

create table public.h3_cells (
    h3_index text primary key check (h3_index ~ '^[0-9a-f]{15}$'),
    n_submissions integer not null default 0,
    n_gold integer not null default 0,
    prior_uncertainty double precision,
    model_disagreement double precision,
    acquisition_score double precision,
    updated_at timestamptz not null default now()
);
