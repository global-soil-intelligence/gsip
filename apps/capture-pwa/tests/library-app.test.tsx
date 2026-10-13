import 'fake-indexeddb/auto'
import { IDBFactory } from 'fake-indexeddb'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
const uuid = '00000000-0000-4000-8000-000000000001'
const instrument = {
  measurement_id: uuid,
  measurement: {
    kind: 'instrument_reflectance',
    source_sha256: 'a'.repeat(64),
    instrument_id: uuid,
    calibration_id: uuid,
    wavelength_nm: [400, 500, 600],
    reflectance: [0.1, 0.2, 0.3],
    uncertainty: [0.01, 0.01, 0.01],
  },
}
beforeEach(() => {
  vi.resetModules()
  vi.stubGlobal('indexedDB', new IDBFactory())
  vi.stubEnv('VITE_CAPTURE_LIVE', 'true')
  vi.stubEnv('VITE_LIBRARY_INTAKE_LIVE', 'true')
  vi.stubEnv('VITE_SUPABASE_URL', '')
  vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', '')
})
afterEach(() => {
  cleanup()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})
async function start() {
  const { App } = await import('../src/App')
  render(<App />)
  return import('../src/queue')
}
async function optIn() {
  fireEvent.click(
    screen.getByRole('checkbox', { name: /add a private library sample/i }),
  )
  await screen.findByLabelText('Depth top (cm)')
}
it('keeps the established form when the library build flag is absent', async () => {
  vi.stubEnv('VITE_LIBRARY_INTAKE_LIVE', 'false')
  await start()
  expect(screen.queryByText('Optional private library sample')).toBeNull()
  expect(screen.queryByLabelText('Depth top (cm)')).toBeNull()
})
it('starts with blank depths and persists declared unknown context through restart', async () => {
  const q = await start()
  await optIn()
  expect(
    (screen.getByLabelText('Depth top (cm)') as HTMLInputElement).value,
  ).toBe('')
  expect(
    (screen.getByLabelText('Depth bottom (cm)') as HTMLInputElement).value,
  ).toBe('')
  fireEvent.change(screen.getByLabelText('Depth top (cm)'), {
    target: { value: '1.5' },
  })
  fireEvent.change(screen.getByLabelText('Depth bottom (cm)'), {
    target: { value: '5' },
  })
  await waitFor(async () =>
    expect((await q.savedLibraryDraft())?.depthBottom).toBe('5'),
  )
  const first = (await q.savedLibraryDraft())!
  expect(first.depthTop).toBe('1.5')
  expect(first.condition).toBe('unknown')
  cleanup()
  vi.resetModules()
  await start()
  await waitFor(() =>
    expect(
      (screen.getByLabelText('Depth top (cm)') as HTMLInputElement).value,
    ).toBe('1.5'),
  )
  expect(
    (await (await import('../src/queue')).savedLibraryDraft())?.sampleId,
  ).toBe(first.sampleId)
})
it('imports one strict declaration privately and clears bytes with the draft', async () => {
  const q = await start()
  await optIn()
  const raw = JSON.stringify(instrument),
    file = new File([raw], 'private.json', { type: 'application/json' })
  fireEvent.change(screen.getByLabelText(/Instrument declaration JSON/), {
    target: { files: [file] },
  })
  await screen.findByText(/Declaration saved privately/)
  expect((await q.savedLibraryDraft())?.instrument).toEqual(instrument)
  expect(Array.from((await q.savedLibraryDraft())!.declarationBytes!)).toEqual(
    Array.from(new TextEncoder().encode(raw)),
  )
  fireEvent.click(
    screen.getByRole('button', {
      name: /discard draft photos and private sample/i,
    }),
  )
  await waitFor(async () => expect(await q.savedLibraryDraft()).toBeUndefined())
  expect(screen.queryByLabelText('Depth top (cm)')).toBeNull()
  expect(await q.draftPhotos()).toEqual({})
})
it('queues the same persisted sample with both restored photo bytes without inventing an instrument', async () => {
  const q = await start()
  await optIn()
  fireEvent.change(screen.getByLabelText('Depth top (cm)'), {
    target: { value: '0' },
  })
  fireEvent.change(screen.getByLabelText('Depth bottom (cm)'), {
    target: { value: '5' },
  })
  const jpeg = new File([new Uint8Array([255, 216, 255, 1])], 'soil.jpg', {
    type: 'image/jpeg',
  })
  fireEvent.change(screen.getByLabelText(/A · Context/), {
    target: { files: [jpeg] },
  })
  fireEvent.change(screen.getByLabelText(/B · Fresh face/), {
    target: { files: [jpeg] },
  })
  await waitFor(async () =>
    expect(Object.keys(await q.draftPhotos()).sort()).toEqual(['A', 'B']),
  )
  const before = (await q.savedLibraryDraft())!
  cleanup()
  vi.resetModules()
  const restored = await start()
  await screen.findByText('Photo B ready on this device')
  for (const [label, value] of [
    ['Latitude', '1'],
    ['Longitude', '1'],
    ['Land cover', 'bare'],
    ['Surface condition', 'dry'],
  ])
    fireEvent.change(screen.getByLabelText(label), { target: { value } })
  fireEvent.click(screen.getByRole('checkbox', { name: /sampling rules/i }))
  fireEvent.click(screen.getByRole('checkbox', { name: /I own these photos/i }))
  fireEvent.submit(
    screen.getByRole('button', { name: /queue observation/i }).closest('form')!,
  )
  await waitFor(async () => expect(await restored.queued()).toHaveLength(1))
  const [queued] = await restored.queued()
  expect(queued.submissionId).toBe(before.submissionId)
  expect(queued.library?.request).toMatchObject({
    intake_id: before.intakeId,
    node_id: before.nodeId,
    sample_id: before.sampleId,
    context: { depth_top_cm: 0, depth_bottom_cm: 5, condition: 'unknown' },
    instrument_declaration: null,
  })
  expect(queued.photos.map((p) => p.shotType).sort()).toEqual(['A', 'B'])
  expect(Array.from(queued.photos[1].bytes)).toEqual([255, 216, 255, 1])
  await waitFor(async () =>
    expect(await restored.savedLibraryDraft()).toBeUndefined(),
  )
})

it('synthetic form-to-private-receipt-to-exact-retry-to-withdrawal lifecycle', async () => {
  const { service } = await import('./libraryFixtures')
  const { submitQueued } = await import('../src/supabase')
  const { drainQueue } = await import('../src/sync')
  const q = await start()
  await optIn()
  fireEvent.change(screen.getByLabelText('Depth top (cm)'), {
    target: { value: '0' },
  })
  fireEvent.change(screen.getByLabelText('Depth bottom (cm)'), {
    target: { value: '5' },
  })
  const file = new File([JSON.stringify(instrument)], 'synthetic.json', {
    type: 'application/json',
  })
  fireEvent.change(screen.getByLabelText(/Instrument declaration JSON/), {
    target: { files: [file] },
  })
  await screen.findByText(/Declaration saved privately/)
  const jpeg = new File([new Uint8Array([255, 216, 255, 1])], 'synthetic.jpg', {
    type: 'image/jpeg',
  })
  for (const shot of ['A', 'B'])
    fireEvent.change(
      screen.getByLabelText(shot === 'A' ? /A · Context/ : /B · Fresh face/),
      { target: { files: [jpeg] } },
    )
  await waitFor(async () =>
    expect(Object.keys(await q.draftPhotos()).sort()).toEqual(['A', 'B']),
  )
  for (const [label, value] of [
    ['Latitude', '1'],
    ['Longitude', '1'],
    ['Land cover', 'bare'],
    ['Surface condition', 'dry'],
  ])
    fireEvent.change(screen.getByLabelText(label), { target: { value } })
  fireEvent.click(screen.getByRole('checkbox', { name: /sampling rules/i }))
  fireEvent.click(screen.getByRole('checkbox', { name: /I own these photos/i }))
  expect((await q.savedLibraryDraft())?.depthTop).toBe('0')
  expect((await q.savedLibraryDraft())?.depthBottom).toBe('5')
  expect((await q.savedLibraryDraft())?.deviceRevision).toBe(
    await q.queueRevision(),
  )
  const { queueLibraryDraft } = await import('../src/library')
  queueLibraryDraft((await q.savedLibraryDraft())!)
  fireEvent.submit(
    screen.getByRole('button', { name: /queue observation/i }).closest('form')!,
  )
  await waitFor(async () => expect(await q.queued()).toHaveLength(1))
  const [record] = await q.queued(),
    s = service()
  const request = structuredClone(record.library!.request),
    bytes = Array.from(record.library!.declarationBytes!)
  const result = await drainQueue(q.indexedDbQueue, (r, save) =>
    submitQueued(s.client, r, save),
  )
  expect(result.synced).toBe(1)
  expect(await q.queued()).toEqual([])
  expect(s.receipts).toEqual(['stored_private_unverified'])
  await submitQueued(s.client, record)
  expect(s.intakes).toEqual([request, request])
  expect(s.receipts).toEqual(['stored_private_unverified', 'already_stored'])
  expect(Array.from(record.library!.declarationBytes!)).toEqual(bytes)
  // A disconnected device still holding this covered record receives the canonical refusal.
  await q.enqueue(record)
  s.state.failure = 'WD001'
  expect(
    (
      await drainQueue(q.indexedDbQueue, (r, save) =>
        submitQueued(s.client, r, save),
      )
    ).discarded,
  ).toBe(1)
  await q.clearQueue()
  expect(await q.queued()).toEqual([])
  expect(await q.savedLibraryDraft()).toBeUndefined()
  expect(await q.draftPhotos()).toEqual({})
  expect(
    s.receipts.every((status) =>
      ['stored_private_unverified', 'already_stored'].includes(status),
    ),
  ).toBe(true)
})
