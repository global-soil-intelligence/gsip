import 'fake-indexeddb/auto'
import { IDBFactory } from 'fake-indexeddb'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { CaptureAcquisitionSchema, partitionByCalibration } from '@gsip/schema'
import { useState } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CaptureChecklist } from '../src/CaptureChecklist'
import {
  buildAcquisition,
  type CaptureChecklistState,
  type CardDetector,
  EMPTY_CHECKLIST,
  osFamily,
  stubCardDetector,
} from '../src/captureStandard'
import supabaseSource from '../src/supabase.ts?raw'
import syncSource from '../src/sync.ts?raw'

// WP-COLLECT-6. Synthetic bytes and fictional values only; no camera, phone or card was used.
const photo = new Uint8Array([255, 216, 255, 2])
const base = {
  appVersion: '0.1.0',
  capturedAt: '2026-01-01T12:00:00.000Z',
  now: Date.parse('2026-01-01T12:05:00Z'),
  photo,
}
const full: CaptureChecklistState = {
  procedure: 'prepared_sample',
  lighting: 'overcast',
  whiteBalanceLocked: true,
  exposureLocked: true,
  hdrOff: true,
  filtersOff: true,
  flashOff: true,
  cameraSquare: true,
  distanceCm: '30',
  fieldOfViewCm: '25',
  replicateCount: '3',
  shareArea: false,
}

beforeEach(() => {
  vi.resetModules()
  vi.stubGlobal('indexedDB', new IDBFactory())
  vi.stubEnv('VITE_CAPTURE_LIVE', 'true')
  // The saved-picker path keeps draft photos only in builds with the library section.
  vi.stubEnv('VITE_LIBRARY_INTAKE_LIVE', 'true')
  vi.stubEnv('VITE_SUPABASE_URL', '')
  vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', '')
})
afterEach(() => {
  cleanup()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('acquisition block built at capture', () => {
  it('S2: is complete and valid with nothing stated, every unknown written out', () => {
    const made = buildAcquisition({ ...base, checklist: EMPTY_CHECKLIST })
    expect(CaptureAcquisitionSchema.parse(made)).toEqual(made)
    expect(made).toEqual({
      schema_version: 'gsip-capture-acquisition-v1',
      standard_version: 'gsip-capture-standard-v1',
      observation_kind: 'rgb_photo',
      procedure: 'unspecified',
      device: {
        make: null,
        model: null,
        os_name: null,
        os_version: null,
        app_version: '0.1.0',
      },
      camera: {
        exposure_time_s: null,
        iso: null,
        exposure: 'unknown',
        white_balance: 'unknown',
        hdr: 'unknown',
        filters: 'unknown',
        flash: 'unknown',
        angle: 'unknown',
        distance_cm: null,
        field_of_view_cm: null,
      },
      lighting: 'unknown',
      reference_card: {
        detection: 'not_run',
        card_id: null,
        card_version: null,
      },
      calibration_status: 'uncalibrated',
      replicate_count: null,
      captured_at: '2026-01-01T12:00:00.000Z',
      location: { consent: false, h3_r9: null },
    })
  })

  it('S2: records what the person stated, and an unticked box is unknown, never "on"', () => {
    const made = buildAcquisition({
      ...base,
      checklist: full,
      userAgent: 'Mozilla/5.0 (Linux; Android 16; Pixel) Mobile',
    })
    expect(made.procedure).toBe('prepared_sample')
    expect(made.lighting).toBe('overcast')
    expect(made.device.os_name).toBe('Android')
    expect(made.camera).toMatchObject({
      exposure: 'locked',
      white_balance: 'locked',
      hdr: 'off',
      filters: 'off',
      flash: 'off',
      angle: 'nadir',
      distance_cm: 30,
      field_of_view_cm: 25,
    })
    expect(made.replicate_count).toBe(3)
    const partly = buildAcquisition({
      ...base,
      checklist: { ...full, hdrOff: false, flashOff: false },
    })
    expect(partly.camera.hdr).toBe('unknown')
    expect(partly.camera.flash).toBe('unknown')
    // The app reads no camera settings.
    expect(made.camera.exposure_time_s).toBeNull()
    expect(made.camera.iso).toBeNull()
  })

  it('S2: keeps a place only with consent, and only as an approximate cell', () => {
    const without = buildAcquisition({
      ...base,
      checklist: full,
      latitude: 10.1234,
      longitude: 20.5678,
    })
    expect(without.location).toEqual({ consent: false, h3_r9: null })
    const withArea = buildAcquisition({
      ...base,
      checklist: { ...full, shareArea: true },
      latitude: 10.1234,
      longitude: 20.5678,
    })
    expect(withArea.location.consent).toBe(true)
    expect(withArea.location.h3_r9).toMatch(/^89[0-9a-f]{8}[37bf]ffff$/)
    expect(JSON.stringify(withArea)).not.toContain('10.12')
    expect(JSON.stringify(withArea)).not.toContain('20.56')
    const noFix = buildAcquisition({
      ...base,
      checklist: { ...full, shareArea: true },
      latitude: Number.NaN,
      longitude: 0,
    })
    expect(noFix.location).toEqual({ consent: true, h3_r9: null })
  })

  it('S2: never fails on bad input, so an observation is never lost to its checklist', () => {
    const made = buildAcquisition({
      appVersion: 'not a version!',
      capturedAt: 'yesterday',
      now: base.now,
      photo,
      checklist: {
        ...full,
        procedure: 'nonsense' as never,
        lighting: 'sunny' as never,
        distanceCm: '-4',
        fieldOfViewCm: '1e9',
        replicateCount: '2.5',
      },
    })
    expect(CaptureAcquisitionSchema.safeParse(made).success).toBe(true)
    expect(made.procedure).toBe('unspecified')
    expect(made.lighting).toBe('unknown')
    expect(made.camera.distance_cm).toBeNull()
    expect(made.camera.field_of_view_cm).toBeNull()
    expect(made.replicate_count).toBeNull()
    expect(made.captured_at).toBe('2026-01-01T12:05:00.000Z')
    expect(made.calibration_status).toBe('uncalibrated')
  })

  it('S2: never throws, whatever it is handed', () => {
    const hostile: Array<Record<string, unknown>> = [
      { capturedAt: '+010000-01-01T00:00:00.000Z' },
      { capturedAt: '0000-01-01T00:00:00.000Z' },
      { now: Number.NaN, capturedAt: 'never' },
      { detector: { name: 'null', detect: () => null } },
      { checklist: { ...full, shareArea: 'yes' } },
      { checklist: { ...full, distanceCm: undefined } },
      { checklist: null },
      { appVersion: undefined },
      { userAgent: 42 },
      { photo: undefined },
    ]
    for (const override of hostile) {
      const made = buildAcquisition({
        ...base,
        checklist: full,
        ...override,
      } as never)
      expect(CaptureAcquisitionSchema.safeParse(made).success).toBe(true)
      expect(made.calibration_status).toBe('uncalibrated')
      expect(made.location.h3_r9).toBeNull()
    }
    // A statement that is not exactly "ticked" is never read as consent.
    expect(
      buildAcquisition({
        ...base,
        checklist: { ...full, shareArea: 'yes' as never },
        latitude: 10.1234,
        longitude: 20.5678,
      }).location,
    ).toEqual({ consent: false, h3_r9: null })
  })

  it('S3: the stub detector looks at nothing, so the app marks every capture uncalibrated', () => {
    expect(stubCardDetector.name).toBe('stub-not-run')
    expect(stubCardDetector.detect(photo)).toEqual({ detection: 'not_run' })
    const made = buildAcquisition({ ...base, checklist: full })
    expect(made.calibration_status).toBe('uncalibrated')
    expect(made.reference_card).toEqual({
      detection: 'not_run',
      card_id: null,
      card_version: null,
    })
  })

  it('S3: the gate follows the detector and nothing the person ticks', () => {
    const detector = (finding: ReturnType<CardDetector['detect']>) => ({
      name: 'test',
      detect: () => finding,
    })
    const one = buildAcquisition({
      ...base,
      checklist: EMPTY_CHECKLIST,
      detector: detector({
        detection: 'one',
        cardId: 'gsip-node',
        cardVersion: 'v1',
      }),
    })
    expect(one.calibration_status).toBe('calibrated')
    expect(one.reference_card.card_id).toBe('gsip-node')
    for (const finding of [
      { detection: 'none' },
      { detection: 'multiple' },
      { detection: 'one' },
      { detection: 'none', cardId: 'gsip-node', cardVersion: 'v1' },
      { detection: 'one', cardId: 'totally-made-up', cardVersion: 'x9' },
      { detection: 'one', cardId: 'gsip-node', cardVersion: 'v2' },
    ] as const)
      expect(
        buildAcquisition({
          ...base,
          checklist: full,
          detector: detector(finding),
        }).calibration_status,
      ).toBe('uncalibrated')
    const broken = buildAcquisition({
      ...base,
      checklist: full,
      detector: {
        name: 'throws',
        detect: () => {
          throw new Error('no detector')
        },
      },
    })
    expect(broken.calibration_status).toBe('uncalibrated')
    expect(broken.reference_card.detection).toBe('not_run')
    const parts = partitionByCalibration([
      { acquisition: one },
      { acquisition: broken },
      {},
    ])
    expect(parts.calibrated).toHaveLength(1)
    expect(parts.uncalibrated).toHaveLength(2)
  })

  it('names only an operating-system family', () => {
    expect(osFamily('Mozilla/5.0 (iPhone; CPU iPhone OS 19_0)')).toBe('iOS')
    expect(osFamily('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15)')).toBe(
      'macOS',
    )
    expect(osFamily('')).toBeNull()
  })
})

describe('capture checklist', () => {
  function Harness() {
    const [value, setValue] = useState(EMPTY_CHECKLIST)
    return (
      <>
        <CaptureChecklist value={value} onChange={setValue} />
        <output data-testid="state">{JSON.stringify(value)}</output>
      </>
    )
  }
  const state = () =>
    JSON.parse(
      screen.getByTestId('state').textContent ?? '{}',
    ) as CaptureChecklistState

  it('is optional and collapsed, and lists every item of the procedure', () => {
    render(<Harness />)
    const details = screen
      .getByText(/Standard capture checklist \(optional\)/)
      .closest('details')!
    expect(details.open).toBe(false)
    expect(details.textContent).toMatch(/0 of 10 stated/)
    for (const label of [
      'White balance is locked',
      'Exposure is locked',
      'HDR is off',
      /Filters, scene and portrait modes are off/,
      'Flash is off',
      /points straight at the soil/,
    ])
      expect((screen.getByLabelText(label) as HTMLInputElement).checked).toBe(
        false,
      )
    expect(screen.getByLabelText('Light')).toBeDefined()
    expect(screen.getByLabelText('Procedure')).toBeDefined()
    expect(screen.getByLabelText(/Distance from lens to soil/)).toBeDefined()
    expect(
      screen.getByLabelText(/Photos taken of this same sample/),
    ).toBeDefined()
  })

  it('records statements, warns about direct sun and says the card is not detected', () => {
    render(<Harness />)
    fireEvent.click(screen.getByLabelText('HDR is off'))
    fireEvent.change(screen.getByLabelText('Light'), {
      target: { value: 'direct_sun' },
    })
    fireEvent.change(screen.getByLabelText(/Distance from lens to soil/), {
      target: { value: '30' },
    })
    expect(state()).toMatchObject({
      hdrOff: true,
      lighting: 'direct_sun',
      distanceCm: '30',
      shareArea: false,
    })
    expect(screen.getByText(/Direct sun gives/).textContent).toMatch(
      /hard shadows and glare/,
    )
    expect(screen.getByText(/3 of 10 stated/)).toBeDefined()
    const status = document.querySelector('[data-calibration]')!
    expect(status.getAttribute('data-calibration')).toBe('uncalibrated')
    expect(status.textContent).toMatch(/does not detect the card yet/)
    expect(status.textContent).toMatch(/RGB\s+observation, not a spectrum/)
    expect(status.textContent).toMatch(/no estimate of\s+any soil property/)
    expect(document.body.textContent?.toLowerCase()).not.toContain('soil test')
  })
})

describe('the capture app', () => {
  async function start() {
    const { App } = await import('../src/App')
    render(<App />)
    await waitFor(() =>
      expect(
        (screen.getByLabelText(/A · Context/) as HTMLInputElement).disabled,
      ).toBe(false),
    )
    return import('../src/queue')
  }
  async function chooseShots(q: Awaited<ReturnType<typeof start>>) {
    for (const shot of ['A', 'B'])
      fireEvent.change(screen.getByLabelText(new RegExp(`${shot} ·`)), {
        target: {
          files: [
            new File(
              [new Uint8Array([255, 216, 255, shot === 'A' ? 1 : 2])],
              `synthetic-${shot}.jpg`,
              { type: 'image/jpeg' },
            ),
          ],
        },
      })
    await waitFor(async () =>
      expect(Object.keys(await q.draftPhotos()).sort()).toEqual(['A', 'B']),
    )
  }
  function fillAndSubmit() {
    for (const [label, value] of [
      ['Latitude', '1'],
      ['Longitude', '1'],
      ['Land cover', 'bare'],
      ['Surface condition', 'dry'],
    ])
      fireEvent.change(screen.getByLabelText(label), { target: { value } })
    fireEvent.click(screen.getByRole('checkbox', { name: /sampling rules/i }))
    fireEvent.click(
      screen.getByRole('checkbox', { name: /I own these photos/i }),
    )
    fireEvent.submit(
      screen
        .getByRole('button', { name: /queue observation/i })
        .closest('form')!,
    )
  }

  it('S2 and S3: every queued observation carries a valid block, marked uncalibrated', async () => {
    const q = await start()
    await chooseShots(q)
    fillAndSubmit()
    await waitFor(async () => expect(await q.queued()).toHaveLength(1))
    const [record] = await q.queued()
    const block = CaptureAcquisitionSchema.parse(record.acquisition)
    expect(block.calibration_status).toBe('uncalibrated')
    expect(block.reference_card.detection).toBe('not_run')
    expect(block.observation_kind).toBe('rgb_photo')
    expect(block.location).toEqual({ consent: false, h3_r9: null })
    expect(block.captured_at).toBe(record.capturedAt)
    expect(block.device.app_version).toBe(record.claims?.clientVersion)
  })

  it('S2: carries what the person stated in the checklist', async () => {
    const q = await start()
    await chooseShots(q)
    fireEvent.click(screen.getByLabelText('White balance is locked'))
    fireEvent.click(screen.getByLabelText('Flash is off'))
    fireEvent.change(screen.getByLabelText('Light'), {
      target: { value: 'shade' },
    })
    fireEvent.change(screen.getByLabelText('Procedure'), {
      target: { value: 'field_profile' },
    })
    fireEvent.click(screen.getByLabelText(/Keep an approximate area/))
    fillAndSubmit()
    await waitFor(async () => expect(await q.queued()).toHaveLength(1))
    const block = CaptureAcquisitionSchema.parse(
      (await q.queued())[0]!.acquisition,
    )
    expect(block).toMatchObject({
      procedure: 'field_profile',
      lighting: 'shade',
      calibration_status: 'uncalibrated',
      camera: { white_balance: 'locked', flash: 'off', hdr: 'unknown' },
    })
    expect(block.location.consent).toBe(true)
    expect(block.location.h3_r9).toMatch(/^89[0-9a-f]{8}[37bf]ffff$/)
  })

  it('S2: statements and area consent do not carry over to the next observation', async () => {
    const q = await start()
    await chooseShots(q)
    fireEvent.click(screen.getByLabelText('Flash is off'))
    fireEvent.change(screen.getByLabelText('Light'), {
      target: { value: 'shade' },
    })
    fireEvent.click(screen.getByLabelText(/Keep an approximate area/))
    expect(screen.getByText(/approximate area kept/)).toBeDefined()
    fillAndSubmit()
    await waitFor(async () => expect(await q.queued()).toHaveLength(1))
    await waitFor(() =>
      expect(
        (screen.getByLabelText(/Keep an approximate area/) as HTMLInputElement)
          .checked,
      ).toBe(false),
    )
    expect(
      (screen.getByLabelText('Flash is off') as HTMLInputElement).checked,
    ).toBe(false)
    expect((screen.getByLabelText('Light') as HTMLSelectElement).value).toBe(
      'unknown',
    )
    expect(screen.queryByText(/approximate area kept/)).toBeNull()
    // The app is still clearing the first observation's draft photos; wait until it is done,
    // or the second pair would be dropped with them.
    await waitFor(async () => {
      expect(Object.keys(await q.draftPhotos())).toEqual([])
      expect(
        (screen.getByLabelText(/A · Context/) as HTMLInputElement).disabled,
      ).toBe(false)
      expect(screen.queryByText('Photo B ready on this device')).toBeNull()
    })
    await chooseShots(q)
    fillAndSubmit()
    await waitFor(async () => expect(await q.queued()).toHaveLength(2))
    const blocks = (await q.queued()).map((record) =>
      CaptureAcquisitionSchema.parse(record.acquisition),
    )
    expect(blocks.filter((block) => block.location.consent)).toHaveLength(1)
    expect(blocks.filter((block) => block.camera.flash === 'off')).toHaveLength(
      1,
    )
    expect(blocks.filter((block) => block.lighting === 'shade')).toHaveLength(1)
  })

  it('S5: nothing sends the block, so the service contract is unchanged', () => {
    expect(supabaseSource).not.toMatch(/acquisition/i)
    expect(syncSource).not.toMatch(/acquisition/i)
  })
})
