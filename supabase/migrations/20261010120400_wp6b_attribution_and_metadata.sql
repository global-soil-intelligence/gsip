-- WP-6b: attribution names are published free text (dataset rows and the dataset card), so they
-- are an abuse and prompt-injection channel. New grants reject control and format characters,
-- markup characters, e-mail addresses and URLs. NOT VALID leaves existing immutable grants untouched.

alter table public.contribution_grants add constraint contribution_grants_attribution_safe check (
    attribution_name = btrim(attribution_name)
    and attribution_name !~ '[[:cntrl:]]'
    -- Unicode format characters (soft hyphen, zero-width and bidirectional controls) can spoof
    -- or visually reorder published text; [[:cntrl:]] does not cover them.
    and attribution_name !~ '[\u00ad\u061c\u180e\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]'
    and attribution_name !~ '[<>{}\[\]\\`|^~$*=#@]'
    and attribution_name !~* '([a-z][a-z0-9+.-]*://|www\.)'
) not valid;

comment on constraint contribution_grants_attribution_safe on public.contribution_grants is
    'WP-6b: published attribution names carry no markup, control or format characters, e-mail addresses or URLs.';

-- Ingest now converts embedded colour profiles to sRGB before stripping them and records only the
-- source colour-space class, privately.
alter table public.photos drop constraint photos_camera_metadata_allowlist;
alter table public.photos add constraint photos_camera_metadata_allowlist check (
    camera_metadata_private is null
    or (
        jsonb_typeof(camera_metadata_private) = 'object'
        and camera_metadata_private - array[
            'make', 'model', 'focal_length_mm', 'exposure_time_s', 'f_number', 'iso', 'color_space'
        ]::text[] = '{}'::jsonb
        and (
            camera_metadata_private ->> 'color_space' is null
            or camera_metadata_private ->> 'color_space' in ('srgb', 'display_p3', 'other', 'none')
        )
    )
);

alter table public.qa_events alter column model_version set default 'deterministic-v2';
