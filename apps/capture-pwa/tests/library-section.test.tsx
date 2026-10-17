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
import { newLibraryDraft } from '../src/library'

beforeEach(() => {
  vi.resetModules()
  vi.stubGlobal('indexedDB', new IDBFactory())
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

it('does not claim a declaration was saved when the parent refused persistence', async () => {
  const { LibrarySection } = await import('../src/LibrarySection')
  const onChange = vi.fn(async () => false)
  render(
    <LibrarySection
      client={null}
      value={{ ...newLibraryDraft('node'), deviceRevision: 0 }}
      onChange={onChange}
    />,
  )
  const file = new File(
    [
      JSON.stringify({
        measurement_id: '00000000-0000-4000-8000-000000000001',
        measurement: {
          kind: 'instrument_reflectance',
          source_sha256: 'a'.repeat(64),
          instrument_id: '00000000-0000-4000-8000-000000000001',
          calibration_id: '00000000-0000-4000-8000-000000000001',
          wavelength_nm: [400, 500, 600],
          reflectance: [0.1, 0.2, 0.3],
          uncertainty: [0.01, 0.01, 0.01],
        },
      }),
    ],
    'synthetic.json',
    { type: 'application/json' },
  )
  fireEvent.change(screen.getByLabelText(/Instrument declaration JSON/), {
    target: { files: [file] },
  })
  await waitFor(() => expect(onChange).toHaveBeenCalledOnce())
  await screen.findByText(/private draft could not be saved/i)
  expect(screen.queryByText(/Declaration saved privately/)).toBeNull()
})

it('does not attach an old declaration read to a different draft at the same revision', async () => {
  const { LibrarySection } = await import('../src/LibrarySection')
  let finish!: (value: string) => void
  const text = vi.fn(
    () =>
      new Promise<string>((resolve) => {
        finish = resolve
      }),
  )
  const file = { size: 1, text } as unknown as File
  const onChange = vi.fn(async () => true)
  const first = { ...newLibraryDraft('node'), deviceRevision: 0 }
  const view = render(
    <LibrarySection client={null} value={first} onChange={onChange} />,
  )
  fireEvent.change(screen.getByLabelText(/Instrument declaration JSON/), {
    target: { files: [file] },
  })
  await waitFor(() => expect(text).toHaveBeenCalledOnce())
  view.rerender(
    <LibrarySection
      client={null}
      value={{ ...newLibraryDraft('node'), deviceRevision: 0 }}
      onChange={onChange}
    />,
  )
  await act(async () => {
    finish(
      JSON.stringify({
        measurement_id: '00000000-0000-4000-8000-000000000001',
        measurement: {
          kind: 'instrument_reflectance',
          source_sha256: 'a'.repeat(64),
          instrument_id: '00000000-0000-4000-8000-000000000001',
          calibration_id: '00000000-0000-4000-8000-000000000001',
          wavelength_nm: [400, 500, 600],
          reflectance: [0.1, 0.2, 0.3],
          uncertainty: [0.01, 0.01, 0.01],
        },
      }),
    )
  })
  await waitFor(() =>
    expect(
      (screen.getByLabelText(/Instrument declaration JSON/) as HTMLInputElement)
        .disabled,
    ).toBe(false),
  )
  expect(onChange).not.toHaveBeenCalled()
  expect(screen.queryByText(/Declaration saved privately/)).toBeNull()
})
