import 'fake-indexeddb/auto'
import { IDBFactory } from 'fake-indexeddb'
import {
  act,
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
  vi.restoreAllMocks()
})
async function start(waitForRestore = true) {
  const { App } = await import('../src/App')
  render(<App />)
  if (waitForRestore) {
    await waitFor(() =>
      expect(
        (screen.getByLabelText(/A · Context/) as HTMLInputElement).disabled,
      ).toBe(false),
    )
    const checkbox = screen.queryByRole('checkbox', {
      name: /add a private library sample/i,
    })
    if (checkbox)
      await waitFor(() =>
        expect(
          (checkbox.closest('fieldset') as HTMLFieldSetElement).disabled,
        ).toBe(false),
      )
  }
  return import('../src/queue')
}
async function optIn() {
  await waitFor(() => {
    const checkbox = screen.getByRole('checkbox', {
      name: /add a private library sample/i,
    }) as HTMLInputElement
    expect(checkbox.disabled).toBe(false)
    expect((checkbox.closest('fieldset') as HTMLFieldSetElement).disabled).toBe(
      false,
    )
    expect(checkbox.checked).toBe(false)
  })
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
it('keeps advanced instrument input collapsed and persisted attachments apparent after restart', async () => {
  const q = await start()
  await optIn()
  const input = screen.getByLabelText(/Instrument declaration JSON/)
  const disclosure = input.closest('details')!
  expect(disclosure).not.toBeNull()
  expect(disclosure.open).toBe(false)
  fireEvent.click(
    screen.getByText('Advanced: instrument declaration (optional)'),
  )
  expect(disclosure.open).toBe(true)
  fireEvent.change(input, {
    target: {
      files: [
        new File([JSON.stringify(instrument)], 'synthetic.json', {
          type: 'application/json',
        }),
      ],
    },
  })
  await screen.findByText(/Declaration saved privately/)
  const originalBytes = Array.from(
    (await q.savedLibraryDraft())!.declarationBytes!,
  )
  fireEvent.click(
    screen.getByText('Advanced: instrument declaration (optional)'),
  )
  expect(disclosure.open).toBe(false)
  expect(
    screen
      .getByText(/Instrument declaration attached privately/)
      .closest('details'),
  ).toBeNull()
  fireEvent.click(
    screen.getByText('Advanced: instrument declaration (optional)'),
  )
  expect(disclosure.open).toBe(true)
  expect(Array.from((await q.savedLibraryDraft())!.declarationBytes!)).toEqual(
    originalBytes,
  )
  const stored = (await q.savedLibraryDraft())!
  expect(document.body.textContent).not.toContain(stored.nodeId)
  expect(document.body.textContent).not.toContain(stored.sampleId)
  cleanup()
  vi.resetModules()
  const restored = await start()
  const restoredInput = await screen.findByLabelText(
    /Instrument declaration JSON/,
  )
  const collapsed = restoredInput.closest('details')!
  expect(collapsed.open).toBe(false)
  const attached = screen.getByText(/Instrument declaration attached privately/)
  expect(attached.closest('details')).toBeNull()
  const remove = screen.getByRole('button', { name: 'Remove declaration' })
  expect(remove.closest('details')).toBeNull()
  expect((await restored.savedLibraryDraft())?.instrument).toEqual(instrument)
  fireEvent.click(remove)
  await waitFor(async () =>
    expect((await restored.savedLibraryDraft())?.instrument).toBeNull(),
  )
  expect((await restored.savedLibraryDraft())?.declarationBytes).toBeNull()
  expect(
    screen.queryByText(/Instrument declaration attached privately/),
  ).toBeNull()
})

function fillObservation() {
  for (const [label, value] of [
    ['Latitude', '1'],
    ['Longitude', '1'],
    ['Land cover', 'bare'],
    ['Surface condition', 'dry'],
  ])
    fireEvent.change(screen.getByLabelText(label), { target: { value } })
  fireEvent.click(screen.getByRole('checkbox', { name: /sampling rules/i }))
  fireEvent.click(screen.getByRole('checkbox', { name: /I own these photos/i }))
}
function submitObservation() {
  fireEvent.submit(
    screen.getByRole('button', { name: /queue observation/i }).closest('form')!,
  )
}
async function chooseShots(shots: Array<'A' | 'B'>) {
  const q = await import('../src/queue')
  for (const shot of shots)
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
    expect(Object.keys(await q.draftPhotos()).sort()).toEqual(shots),
  )
}
it.each([{ shots: [] }, { shots: ['A'] }, { shots: ['B'] }] as Array<{
  shots: Array<'A' | 'B'>
}>)(
  'requires both photos when the saved-picker path has shots $shots',
  async ({ shots }) => {
    const q = await start()
    await chooseShots(shots)
    fillObservation()
    submitObservation()
    await screen.findByText('Add photos A and B before continuing.')
    expect(await q.queued()).toEqual([])
    expect(await q.savedLibraryDraft()).toBeUndefined()
  },
)
it('queues A+B without a card, optional C or invented library context', async () => {
  const q = await start()
  expect(screen.queryByLabelText('Depth top (cm)')).toBeNull()
  await chooseShots(['A', 'B'])
  fillObservation()
  submitObservation()
  await waitFor(async () => expect(await q.queued()).toHaveLength(1))
  const [record] = await q.queued()
  expect(record.library).toBeUndefined()
  expect(record.photos.map((photo) => photo.shotType)).toEqual(['A', 'B'])
  expect(record.photos.map((photo) => Array.from(photo.bytes))).toEqual([
    [255, 216, 255, 1],
    [255, 216, 255, 2],
  ])
  expect(Object.keys(record.claims!).sort()).toEqual([
    'captureMethod',
    'clientVersion',
    'ingestPath',
    'locationSource',
  ])
  expect(await q.savedLibraryDraft()).toBeUndefined()
  expect(
    screen.queryByText(/stored_private_unverified|already_stored/),
  ).toBeNull()
})

it('does not present a refused picker save as ready and allows a fresh choice', async () => {
  const q = await start()
  const refused = vi
    .spyOn(q, 'saveDraftPhoto')
    .mockResolvedValueOnce(false as never)
  const file = new File([new Uint8Array([255, 216, 255, 1])], 'synthetic.jpg', {
    type: 'image/jpeg',
  })
  fireEvent.change(screen.getByLabelText(/A · Context/), {
    target: { files: [file] },
  })
  await screen.findByText(/Photo A could not be saved.*Choose it again/)
  expect(screen.queryByText('Photo A ready on this device')).toBeNull()
  expect(await q.draftPhotos()).toEqual({})
  refused.mockRestore()
  await chooseShots(['A'])
  await screen.findByText('Photo A ready on this device')
})

it('holds a restored library context with no original revision until explicit restart', async () => {
  const q = await import('../src/queue')
  await q.queueRevision()
  const { newLibraryDraft } = await import('../src/library')
  const legacy = { ...newLibraryDraft(uuid), depthTop: '0', depthBottom: '5' }
  const { openDB } = await import('idb')
  const db = await openDB('gsip-capture-v1')
  await db.put('libraryDraft', legacy, 'current')
  db.close()
  await start()
  await screen.findByLabelText('Depth top (cm)')
  await screen.findByText(/original revision.*discard.*start/i)
  expect((await q.savedLibraryDraft())?.deviceRevision).toBeUndefined()
  expect(
    (screen.getByLabelText('Depth top (cm)') as HTMLInputElement).disabled,
  ).toBe(true)
  const clearLibrary = q.clearLibraryDraft
  let finishClear!: () => void
  const clearing = new Promise<void>((resolve) => {
    finishClear = resolve
  })
  vi.spyOn(q, 'clearLibraryDraft').mockImplementationOnce(async () => {
    await clearing
    await clearLibrary()
  })
  fireEvent.click(
    screen.getByRole('checkbox', { name: /add a private library sample/i }),
  )
  await waitFor(() =>
    expect(screen.queryByLabelText('Depth top (cm)')).toBeNull(),
  )
  expect(
    (
      screen
        .getByRole('checkbox', { name: /add a private library sample/i })
        .closest('fieldset') as HTMLFieldSetElement
    ).disabled,
  ).toBe(true)
  const restart = optIn()
  await act(async () => finishClear())
  await restart
  await waitFor(async () =>
    expect((await q.savedLibraryDraft())?.deviceRevision).toBe(
      await q.queueRevision(),
    ),
  )
})

it('does not refill discarded state from delayed initial restores or delete fresh successor drafts', async () => {
  const q = await import('../src/queue')
  const { newLibraryDraft } = await import('../src/library')
  const revision = await q.queueRevision()
  const photo = {
    bytes: new Uint8Array([255, 216, 255, 1]),
    mimeType: 'image/jpeg' as const,
    method: 'file' as const,
    takenAt: 1,
  }
  const original = { ...newLibraryDraft(uuid), deviceRevision: revision }
  let photos!: (value: Awaited<ReturnType<typeof q.draftPhotos>>) => void
  let context!: (value: typeof original) => void
  const restorePhotos = vi.spyOn(q, 'draftPhotos').mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        photos = resolve
      }),
  )
  const restoreContext = vi
    .spyOn(q, 'savedLibraryDraft')
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          context = resolve
        }),
    )
  await start(false)
  await waitFor(() => {
    expect(restorePhotos).toHaveBeenCalledOnce()
    expect(restoreContext).toHaveBeenCalledOnce()
  })
  fireEvent.click(
    screen.getByRole('button', {
      name: /discard draft photos and private sample/i,
    }),
  )
  await screen.findByText('Photos discarded.')
  const successor = await q.queueRevision()
  const fresh = { ...newLibraryDraft(uuid), deviceRevision: successor }
  await q.saveDraftPhoto('B', photo, successor)
  await q.saveLibraryDraft(fresh, successor)
  await act(async () => {
    photos({ A: photo })
    context(original)
  })
  await waitFor(() =>
    expect(
      (screen.getByLabelText(/A · Context/) as HTMLInputElement).disabled,
    ).toBe(false),
  )
  expect(screen.queryByText('Photo A ready on this device')).toBeNull()
  expect(screen.queryByLabelText('Depth top (cm)')).toBeNull()
  expect((await q.draftPhotos()).B?.takenAt).toBe(1)
  expect((await q.savedLibraryDraft())?.sampleId).toBe(fresh.sampleId)
})

it('keeps newer library edits when an older refused save finishes later', async () => {
  const q = await start()
  await optIn()
  let finish!: (value: boolean) => void
  vi.spyOn(q, 'saveLibraryDraft').mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve
      }),
  )
  fireEvent.change(screen.getByLabelText('Depth top (cm)'), {
    target: { value: '1' },
  })
  fireEvent.change(screen.getByLabelText('Depth bottom (cm)'), {
    target: { value: '5' },
  })
  await waitFor(async () =>
    expect((await q.savedLibraryDraft())?.depthBottom).toBe('5'),
  )
  await act(async () => finish(false))
  expect(
    (screen.getByLabelText('Depth top (cm)') as HTMLInputElement).value,
  ).toBe('1')
  expect(
    (screen.getByLabelText('Depth bottom (cm)') as HTMLInputElement).value,
  ).toBe('5')
  expect(screen.queryByText(/no usable original revision/)).toBeNull()
  expect((await q.savedLibraryDraft())?.depthTop).toBe('1')
})

it('holds photo reuse after library opt-out without erasing persisted bytes or rebinding selections', async () => {
  const q = await start()
  await optIn()
  await chooseShots(['A', 'B'])
  const before = structuredClone(await q.draftPhotos())
  const revision = await q.queueRevision()
  fireEvent.click(
    screen.getByRole('checkbox', { name: /add a private library sample/i }),
  )
  await screen.findByText(
    'Private sample removed. Choose photos again before queueing.',
  )
  expect(await q.queueRevision()).toBe(revision + 1)
  expect(await q.draftPhotos()).toEqual(before)
  expect(screen.queryByText('Photo A ready on this device')).toBeNull()
  expect(screen.queryByText('Photo B ready on this device')).toBeNull()
  fillObservation()
  submitObservation()
  await screen.findByText('Add photos A and B before continuing.')
  expect(await q.queued()).toEqual([])
  await chooseShots(['A', 'B'])
  await screen.findByText('Photo B ready on this device')
  submitObservation()
  await waitFor(async () => expect(await q.queued()).toHaveLength(1))
  expect((await q.queued())[0]!.library).toBeUndefined()
})

it('keeps a failed explicit library removal held and visible for another discard attempt', async () => {
  const q = await start()
  await optIn()
  const original = (await q.savedLibraryDraft())!
  vi.spyOn(q, 'clearLibraryDraft').mockRejectedValueOnce(
    new Error('synthetic storage refusal'),
  )
  fireEvent.click(
    screen.getByRole('checkbox', { name: /add a private library sample/i }),
  )
  await screen.findByText(
    'The private draft could not be saved. Try again before queueing.',
  )
  expect(
    (screen.getByLabelText('Depth top (cm)') as HTMLInputElement).disabled,
  ).toBe(true)
  expect((await q.savedLibraryDraft())?.sampleId).toBe(original.sampleId)
  fireEvent.click(
    screen.getByRole('checkbox', { name: /add a private library sample/i }),
  )
  await screen.findByText(
    'Private sample removed. Choose photos again before queueing.',
  )
  expect(await q.savedLibraryDraft()).toBeUndefined()
})

it('can start fresh context and declaration after discarding an unresolved older declaration read', async () => {
  const q = await start()
  await optIn()
  const original = (await q.savedLibraryDraft())!
  let finish!: (value: string) => void
  const text = vi.fn(
    () =>
      new Promise<string>((resolve) => {
        finish = resolve
      }),
  )
  fireEvent.change(screen.getByLabelText(/Instrument declaration JSON/), {
    target: { files: [{ size: 1, text } as unknown as File] },
  })
  await waitFor(() => expect(text).toHaveBeenCalledOnce())
  fireEvent.click(
    screen.getByRole('button', {
      name: /discard draft photos and private sample/i,
    }),
  )
  await screen.findByText('Photos discarded.')
  expect(
    (
      screen.getByRole('checkbox', {
        name: /add a private library sample/i,
      }) as HTMLInputElement
    ).disabled,
  ).toBe(false)
  await optIn()
  const fresh = (await q.savedLibraryDraft())!
  expect(fresh.sampleId).not.toBe(original.sampleId)
  fireEvent.change(screen.getByLabelText(/Instrument declaration JSON/), {
    target: {
      files: [
        new File([JSON.stringify(instrument)], 'fresh.json', {
          type: 'application/json',
        }),
      ],
    },
  })
  await screen.findByText(/Declaration saved privately/)
  await act(async () => finish(JSON.stringify(instrument)))
  expect((await q.savedLibraryDraft())?.sampleId).toBe(fresh.sampleId)
  expect((await q.savedLibraryDraft())?.instrument).toEqual(instrument)
})

it('imports one strict declaration privately and clears bytes with the draft', async () => {
  const q = await start()
  await optIn()
  fireEvent.click(
    screen.getByText('Advanced: instrument declaration (optional)'),
  )
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
  fireEvent.click(
    screen.getByText('Advanced: instrument declaration (optional)'),
  )
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
