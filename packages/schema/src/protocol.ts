/**
 * The GSIP capture protocol (SPEC section 5, v1.1) as data: what the reader API serves to people
 * and agents (WP-AGENT-1). Keep it in step with SPEC section 5, the capture app and the card
 * generator (`card/design.py`); a test checks the shared values.
 */
import { SOILGRIDS_PROPERTY_MAPPING } from './prior.ts'

export const PROTOCOL_VERSION = '1.1'

const PROPERTY_DESCRIPTIONS = {
  bd: 'Bulk density',
  cec: 'Cation exchange capacity',
  clay: 'Clay content',
  n: 'Total nitrogen',
  ph: 'pH in water',
  sand: 'Sand content',
  silt: 'Silt content',
  soc: 'Soil organic carbon',
} as const

export const CAPTURE_PROTOCOL = {
  version: PROTOCOL_VERSION,
  summary:
    'Two photos of soil beside a free printed reference card, a private location and three one-tap descriptions. GSIP grades every photo, publishes only k-anonymous H3 cells, and reports estimates with uncertainty, never laboratory results.',
  card: {
    format: 'A6 (105 mm x 148 mm), colour or black-and-white edition',
    patches: [
      'dark_soil',
      'ochre',
      'clay_red',
      'sand',
      'leaf',
      'sky',
      'white',
      'black',
      'neutral_gray',
    ],
    marker: { dictionary: 'DICT_4X4_50', id: 7 },
    scale_line_mm: 20,
    optional: true,
    without_card:
      'Accepted, marked uncalibrated and down-weighted in training. GSIP never rejects a willing contributor; it grades the data instead.',
  },
  shots: [
    {
      id: 'A',
      name: 'Context',
      required: true,
      instructions:
        'Undisturbed ground from about 30 cm, with the card in frame.',
    },
    {
      id: 'B',
      name: 'Fresh face',
      required: true,
      instructions:
        'Scrape 2 to 3 cm to expose fresh soil, then photograph from about 15 cm with the card in frame. This is the primary analysis image.',
    },
    {
      id: 'C',
      name: 'Texture',
      required: false,
      instructions:
        'A moistened soil ball or ribbon in hand. Judged on its own: a failed shot C is left out of releases and never fails the observation.',
    },
  ],
  sampling_rules: [
    'Dig only where you have permission.',
    'Never sample in protected areas, on graves or archaeological sites, or near buried utilities.',
    'Replace the scraped soil.',
    'Keep people out of the photos.',
    'Classroom contributions run under a teacher of record.',
  ],
  descriptions: {
    land_cover: [
      'cropland',
      'grassland',
      'forest',
      'shrubland',
      'wetland',
      'urban',
      'bare',
    ],
    surface_condition: ['dry', 'moist', 'wet'],
    disturbed: [true, false],
  },
  recorded_privately: [
    'GPS position with its accuracy radius and source (device GPS or manual pin)',
    'Capture time of shot B as recorded by the device',
    'Device model and allowlisted, non-location camera fields',
  ],
  quality_checks: [
    'soil_region: at least 20 % of the frame remains as soil once the card is masked',
    'sharpness and exposure, measured on the soil only',
    'card_detection: records calibrated or uncalibrated; never fails a photo',
    'gps_plausibility: an accuracy radius above 250 m or a gross mismatch with soil maps goes to human review',
    'duplicate: a near-duplicate photo goes to human review, never to rejection',
  ],
  privacy: {
    published_resolutions: [8, 6, 4],
    minimum_contributors_per_cell: 3,
    statement:
      'Precise locations and original photos are never published. A cell is published only when at least 3 different contributors have observations in it; finer cells roll up to coarser ones until they qualify.',
  },
  properties: Object.values(SOILGRIDS_PROPERTY_MAPPING).map(
    ({ property, unit }) => ({
      name: property,
      unit,
      description: PROPERTY_DESCRIPTIONS[property],
    }),
  ),
  provenance_tiers: [
    {
      tier: -1,
      meaning: 'Synthetic, simulated or seeded data; never published.',
    },
    {
      tier: 0,
      meaning:
        "Field observation; the contributor's statements were recorded but not corroborated.",
    },
    {
      tier: 1,
      meaning:
        'Corroborated: both required photos carried a capture time that agreed with the stated time and the moment the terms were accepted, and any embedded position agreed with the stated location.',
    },
    { tier: 2, meaning: 'Reserved: attested capture. Not yet assigned.' },
    {
      tier: 3,
      meaning: 'Reserved: paired with a laboratory result. Not yet assigned.',
    },
  ],
} as const

export type CaptureProtocol = typeof CAPTURE_PROTOCOL
