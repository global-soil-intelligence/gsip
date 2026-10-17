import { describe, expect, it } from 'vitest'
import {
  createGuideSession,
  guideAccessAllowed,
  guideFrameAllowed,
  GUIDE_ACCESS_LEASE_MS,
  GUIDE_MAX_RETAINED_BYTES,
  type GuideAccess,
  type GuideSession,
} from '../src/guideSession'
import type { CapturedPhoto } from '../src/platform/types'
import { queueLibraryDraft, type LibraryDraft } from '../src/library'
import type { QueueRecord, ShotType } from '../src/types'

const now = 100_000
const observationId = '00000000-0000-4000-8000-000000000001'
const access: GuideAccess = {
  pilot: true,
  native: false,
  rightsView: false,
  libraryLive: true,
  canCollect: true,
  rightsHold: false,
  ownerUid: 'synthetic-owner',
  anonymous: false,
  authGeneration: 4,
  revision: 7,
  verifiedAt: now,
}
const dimensions = { width: 1280, height: 720 }

function libraryDraft(overrides: Partial<LibraryDraft> = {}): LibraryDraft {
  return {
    version: 1,
    intakeId: '00000000-0000-4000-8000-000000000010',
    nodeId: '00000000-0000-4000-8000-000000000011',
    sampleId: '00000000-0000-4000-8000-000000000012',
    submissionId: '00000000-0000-4000-8000-000000000013',
    ownerUid: access.ownerUid!,
    deviceRevision: access.revision,
    depthTop: '0',
    depthBottom: '10',
    condition: 'unknown',
    instrument: null,
    declarationBytes: null,
    ...overrides,
  }
}

function photo(value = 1, length = 4): CapturedPhoto {
  const bytes = new Uint8Array(length)
  bytes.set([0xff, 0xd8, 0xff, value])
  return { bytes, mimeType: 'image/jpeg', method: 'camera', takenAt: now }
}

function session(
  overrides: Partial<Parameters<typeof createGuideSession>[0]> = {},
) {
  return createGuideSession(
    {
      sessionId: 'synthetic-session',
      observationId,
      access,
      restorationComplete: true,
      pendingPickerReads: 0,
      pickerPhotosEmpty: true,
      persistedPhotosEmpty: true,
      libraryDraft: null,
      ...overrides,
    },
    now,
  )!
}

function select(guide: GuideSession, shot: ShotType, value = 1) {
  const token = guide.start(shot, access, now)!
  expect(token).not.toBeNull()
  expect(guide.permissionResolved(token, access, now)).toBe(true)
  expect(guide.playbackReady(token, access, now)).toBe(true)
  expect(guide.shutter(token, dimensions, access, now)).toBe(true)
  expect(guide.encoded(token, photo(value), dimensions, access, now)).toBe(true)
  expect(guide.accept(token, access, now)).toBe(true)
  return token
}

function record(guide: GuideSession): QueueRecord {
  const photos = guide.photos(access, now)!
  return {
    submissionId: observationId,
    ownerUid: access.ownerUid!,
    collectionMode: 'invited_private',
    grantId: '00000000-0000-4000-8000-000000000002',
    acceptedAt: '2026-10-16T00:00:00Z',
    queuedAt: '2026-10-16T00:00:00Z',
    termsVersion: 'synthetic-terms',
    capturedAt: '2026-10-16T00:00:00Z',
    attributionName: '',
    deviceModel: 'synthetic-device',
    accuracyM: null,
    latitude: 0,
    longitude: 0,
    landCover: 'cropland',
    surfaceCondition: 'dry',
    disturbed: false,
    photos: (['A', 'B', 'C'] as const).flatMap((shot, index) =>
      photos[shot]
        ? [
            {
              bytes: photos[shot]!.bytes,
              mimeType: 'image/jpeg',
              objectId: `00000000-0000-4000-8000-00000000000${index + 3}`,
              shotType: shot,
            },
          ]
        : [],
    ),
  }
}

describe('pure guide eligibility and entry', () => {
  it.each([
    { pilot: false },
    { native: true },
    { rightsView: true },
    { libraryLive: false },
    { canCollect: false },
    { rightsHold: true },
    { ownerUid: null },
    { ownerUid: '' },
    { anonymous: true },
    { authGeneration: -1 },
    { revision: Number.NaN },
    { verifiedAt: now + 1 },
    { verifiedAt: now - GUIDE_ACCESS_LEASE_MS },
  ])('refuses unsupported or stale access %j', (change) => {
    expect(guideAccessAllowed({ ...access, ...change }, now)).toBe(false)
    expect(session({ access: { ...access, ...change } })).toBeNull()
  })

  it.each([
    { restorationComplete: false },
    { pendingPickerReads: 1 },
    { pendingPickerReads: Number.NaN },
    { pickerPhotosEmpty: false },
    { persistedPhotosEmpty: false },
  ])('holds until picker restoration and empty checks finish %j', (change) => {
    expect(session(change)).toBeNull()
  })

  it('holds foreign, unowned and ambiguous library context', () => {
    const draft = {
      version: 1 as const,
      intakeId: 'intake',
      nodeId: 'node',
      sampleId: 'sample',
      submissionId: observationId,
      depthTop: '0',
      depthBottom: '10',
      condition: 'unknown' as const,
      instrument: null,
      declarationBytes: null,
    }
    expect(session({ libraryDraft: draft })).toBeNull()
    expect(
      session({
        libraryDraft: { ...draft, ownerUid: 'other', deviceRevision: 7 },
      }),
    ).toBeNull()
    expect(
      session({ libraryDraft: { ...draft, ownerUid: access.ownerUid! } }),
    ).toBeNull()
    expect(
      session({
        libraryDraft: {
          ...draft,
          ownerUid: access.ownerUid!,
          deviceRevision: 6,
        },
      }),
    ).toBeNull()
  })
})

describe('guide asynchronous selection ownership', () => {
  it('fences every async stage by owner, auth generation, revision and admission', () => {
    for (const change of [
      { ownerUid: 'other' },
      { authGeneration: 5 },
      { revision: 8 },
      { canCollect: false },
      { anonymous: true },
    ]) {
      for (const stage of [
        'permission',
        'playback',
        'shutter',
        'encoded',
        'accept',
      ]) {
        const guide = session()
        const token = guide.start('A', access, now)!
        if (stage !== 'permission') guide.permissionResolved(token, access, now)
        if (!['permission', 'playback'].includes(stage))
          guide.playbackReady(token, access, now)
        if (['encoded', 'accept'].includes(stage))
          guide.shutter(token, dimensions, access, now)
        if (stage === 'accept')
          guide.encoded(token, photo(), dimensions, access, now)
        const changed = { ...access, ...change }
        const accepted =
          stage === 'permission'
            ? guide.permissionResolved(token, changed, now)
            : stage === 'playback'
              ? guide.playbackReady(token, changed, now)
              : stage === 'shutter'
                ? guide.shutter(token, dimensions, changed, now)
                : stage === 'encoded'
                  ? guide.encoded(token, photo(), dimensions, changed, now)
                  : guide.accept(token, changed, now)
        expect(accepted, `${stage}: ${JSON.stringify(change)}`).toBe(false)
        expect(guide.photos(access, now)).toBeNull()
      }
    }
  })

  it('retains unresolved resource reservations after cancellation and drops late results', () => {
    const guide = session()
    const first = guide.start('A', access, now)!
    expect(guide.start('B', access, now)).toBeNull()
    guide.cancelRetake(first)
    expect(guide.state().pendingRequest).toBe(true)
    expect(guide.start('B', access, now)).toBeNull()
    expect(guide.permissionResolved(first, access, now)).toBe(false)
    const next = guide.start('B', access, now)!
    guide.permissionResolved(next, access, now)
    guide.playbackReady(next, access, now)
    guide.shutter(next, dimensions, access, now)
    guide.hold()
    expect(guide.state().pendingEncoder).toBe(true)
    expect(guide.resume(access, now)).toBe(true)
    expect(guide.start('A', access, now)).toBeNull()
    expect(guide.encoded(next, photo(), dimensions, access, now)).toBe(false)
    expect(guide.start('A', access, now)).not.toBeNull()
  })

  it('rejects tokens for another observation, shot or cancelled intent', () => {
    const guide = session()
    const first = guide.start('A', access, now)!
    for (const change of [
      { observationId: 'other' },
      { sessionId: 'other' },
      { shotType: 'B' as const },
      { shotIntent: first.shotIntent + 1 },
      { generation: first.generation + 1 },
    ])
      expect(
        guide.permissionResolved({ ...first, ...change }, access, now),
      ).toBe(false)
    expect(guide.permissionResolved(first, access, now)).toBe(true)
    guide.cancelRetake(first)
    const next = guide.start('A', access, now)!
    expect(next.shotIntent).toBeGreaterThan(first.shotIntent)
    expect(guide.playbackReady(first, access, now)).toBe(false)
    expect(guide.permissionResolved(next, access, now)).toBe(true)
  })

  it('preserves accepted shots when a retake is cancelled or invalid', () => {
    const guide = session()
    select(guide, 'A', 7)
    const retake = guide.start('A', access, now)!
    guide.permissionResolved(retake, access, now)
    guide.playbackReady(retake, access, now)
    guide.shutter(retake, dimensions, access, now)
    expect(
      guide.encoded(
        retake,
        { ...photo(), mimeType: 'image/png' } as never,
        dimensions,
        access,
        now,
      ),
    ).toBe(false)
    expect(guide.photos(access, now)?.A?.bytes[3]).toBe(7)
    const another = guide.start('A', access, now)!
    guide.cancelRetake(another)
    expect(guide.photos(access, now)?.A?.bytes[3]).toBe(7)
    expect(guide.cancel(false)).toBe(false)
    expect(guide.cancel(true)).toBe(true)
    expect(guide.state().retainedBytes).toBe(0)
  })

  it('hides accepted RAM and discards review while held; resumes only explicitly with fresh same context', () => {
    const guide = session()
    select(guide, 'A', 7)
    const pending = guide.start('B', access, now)!
    guide.permissionResolved(pending, access, now)
    guide.playbackReady(pending, access, now)
    guide.shutter(pending, dimensions, access, now)
    guide.encoded(pending, photo(9), dimensions, access, now)
    guide.hold()
    expect(guide.state().hasCandidate).toBe(false)
    expect(guide.state().retainedBytes).toBe(4)
    expect(guide.photos(access, now)).toBeNull()
    expect(guide.accept(pending, access, now)).toBe(false)
    expect(guide.resume(access, now + GUIDE_ACCESS_LEASE_MS)).toBe(false)
    const fresh = { ...access, verifiedAt: now + GUIDE_ACCESS_LEASE_MS }
    expect(guide.photos(fresh, fresh.verifiedAt)).toBeNull()
    expect(guide.resume(fresh, fresh.verifiedAt)).toBe(true)
    expect(guide.photos(fresh, fresh.verifiedAt)?.A?.bytes[3]).toBe(7)
    expect(guide.state().phase).toBe('selected')
    guide.hold()
    expect(
      guide.resume({ ...fresh, authGeneration: 5 }, fresh.verifiedAt),
    ).toBe(false)
    expect(guide.state().retainedBytes).toBe(0)
  })

  it('expires its lease at an explicit action even if no timer ran', () => {
    const guide = session()
    select(guide, 'A')
    expect(guide.start('B', access, now + GUIDE_ACCESS_LEASE_MS)).toBeNull()
    expect(guide.photos(access, now)).toBeNull()
    expect(guide.state().phase).toBe('held')
  })
})

describe('guide bounds and immutable pending queue identity', () => {
  it.each([
    null,
    { ...photo(), bytes: new Uint8Array() },
    { ...photo(), bytes: new Uint8Array([0xff, 0xd8, 1, 1]) },
    { ...photo(), method: 'file' as const },
    photo(1, 12 * 1024 * 1024 + 1),
  ])(
    'rejects null, malformed, noncamera or excess candidate output',
    (invalid) => {
      const guide = session()
      const token = guide.start('A', access, now)!
      guide.permissionResolved(token, access, now)
      guide.playbackReady(token, access, now)
      guide.shutter(token, dimensions, access, now)
      expect(guide.encoded(token, invalid, dimensions, access, now)).toBe(false)
      expect(guide.state().retainedBytes).toBe(0)
      expect(guide.state().pendingEncoder).toBe(false)
    },
  )

  it('detaches candidate input and requires personal acceptance before a snapshot', () => {
    const guide = session()
    const token = guide.start('A', access, now)!
    guide.permissionResolved(token, access, now)
    guide.playbackReady(token, access, now)
    guide.shutter(token, dimensions, access, now)
    const input = photo(7)
    guide.encoded(token, input, dimensions, access, now)
    input.bytes[3] = 99
    guide.accept(token, access, now)
    expect(guide.photos(access, now)?.A?.bytes[3]).toBe(7)
    select(guide, 'B')
    expect(
      guide.freeze({ ...record(guide), acceptedAt: undefined }, access, now),
    ).toBeNull()
  })

  it('freezes only exact opted-in library context with real declared depth', () => {
    const draft: LibraryDraft = {
      version: 1,
      intakeId: '00000000-0000-4000-8000-000000000010',
      nodeId: '00000000-0000-4000-8000-000000000011',
      sampleId: '00000000-0000-4000-8000-000000000012',
      submissionId: observationId,
      ownerUid: access.ownerUid!,
      deviceRevision: 7,
      depthTop: '0',
      depthBottom: '10',
      condition: 'unknown',
      instrument: null,
      declarationBytes: null,
    }
    const guide = session({ libraryDraft: draft })
    select(guide, 'A')
    select(guide, 'B')
    const selected = record(guide)
    expect(guide.freeze(selected, access, now)).toBeNull()
    expect(
      guide.freeze(
        {
          ...selected,
          library: queueLibraryDraft({ ...draft, depthBottom: '11' }),
        },
        access,
        now,
      ),
    ).toBeNull()
    const blank = session({
      libraryDraft: { ...draft, depthTop: '', depthBottom: '' },
    })
    select(blank, 'A')
    select(blank, 'B')
    expect(
      blank.freeze(
        { ...record(blank), library: queueLibraryDraft(draft) },
        access,
        now,
      ),
    ).toBeNull()
    expect(blank.setLibraryDraft(draft, access, now)).toBe(true)
    expect(
      blank.freeze(
        { ...record(blank), library: queueLibraryDraft(draft) },
        access,
        now,
      ),
    ).not.toBeNull()
    const exact = { ...selected, library: queueLibraryDraft(draft) }
    const pending = guide.freeze(exact, access, now)!
    expect(pending.record.library?.request.context.depth_bottom_cm).toBe(10)
    draft.depthBottom = '20'
    exact.library.request.context.depth_bottom_cm = 30
    pending.record.library!.request.context.depth_bottom_cm = 40
    expect(
      guide.pending(access, now)?.record.library?.request.context
        .depth_bottom_cm,
    ).toBe(10)
  })

  it('accepts photos before later opt-in and freezes the current canonical library identity', () => {
    const guide = session()
    const a = select(guide, 'A', 7)
    const b = select(guide, 'B', 8)
    const draft = libraryDraft()
    expect(guide.setLibraryDraft(draft, access, now)).toBe(true)
    expect(a.observationId).toBe(observationId)
    expect(b.observationId).toBe(observationId)
    const selected = record(guide)
    expect(
      guide.freeze(
        { ...selected, library: queueLibraryDraft(draft) },
        access,
        now,
      ),
    ).toBeNull()
    const pending = guide.freeze(
      {
        ...selected,
        submissionId: draft.submissionId,
        library: queueLibraryDraft(draft),
      },
      access,
      now,
    )!
    expect(pending.record.submissionId).toBe(draft.submissionId)
    expect(pending.token.submissionId).toBe(draft.submissionId)
    expect(pending.record.photos.map((p) => p.bytes[3])).toEqual([7, 8])
    expect(guide.setLibraryDraft(null, access, now)).toBe(false)
    expect(
      guide.setLibraryDraft({ ...draft, depthBottom: '20' }, access, now),
    ).toBe(false)
    const retry = guide.freeze(
      { ...pending.record, submissionId: observationId },
      access,
      now,
    )!
    expect(retry.token).toBe(pending.token)
    expect(retry.record.submissionId).toBe(draft.submissionId)
    expect(retry.record.library!.request.context.depth_bottom_cm).toBe(10)
  })

  it('binds completed edited context after entry without changing photo intents or exposing caller aliases', () => {
    const initial = libraryDraft({ depthTop: '', depthBottom: '' })
    const guide = session({ libraryDraft: initial })
    expect(guide).not.toBeNull()
    const a = select(guide, 'A', 7)
    select(guide, 'B', 8)
    const completed = { ...initial, depthTop: '2', depthBottom: '8' }
    expect(guide.setLibraryDraft(completed, access, now)).toBe(true)
    completed.depthBottom = '99'
    const retake = guide.start('A', access, now)!
    expect(retake.observationId).toBe(a.observationId)
    expect(retake.shotIntent).toBe(a.shotIntent + 1)
    guide.cancelRetake(retake)
    guide.permissionResolved(retake, access, now)
    const selected = record(guide)
    const current = { ...initial, depthTop: '2', depthBottom: '8' }
    const pending = guide.freeze(
      {
        ...selected,
        submissionId: current.submissionId,
        library: queueLibraryDraft(current),
      },
      access,
      now,
    )!
    expect(pending.record.library!.request.context).toEqual({
      depth_top_cm: 2,
      depth_bottom_cm: 8,
      condition: 'unknown',
    })
    expect(pending.record.photos[0]!.bytes[3]).toBe(7)
  })

  it('permits explicit pre-freeze opt-out while keeping accepted photos and the ordinary identity', () => {
    const guide = session({ libraryDraft: libraryDraft() })
    expect(guide).not.toBeNull()
    select(guide, 'A')
    select(guide, 'B')
    expect(guide.setLibraryDraft(null, access, now)).toBe(true)
    expect(guide.freeze(record(guide), access, now)?.record.submissionId).toBe(
      observationId,
    )
  })

  it('rejects incomplete, foreign, stale or malformed explicit context updates', () => {
    const guide = session()
    select(guide, 'A')
    select(guide, 'B')
    for (const change of [
      { ownerUid: 'other' },
      { ownerUid: undefined },
      { deviceRevision: undefined },
      { deviceRevision: 6 },
      { intakeId: 'bad' },
      { sampleId: 'bad' },
      { submissionId: 'bad' },
      { depthTop: '' },
      { depthBottom: '0' },
      { declarationBytes: new Uint8Array([1]) },
    ])
      expect(guide.setLibraryDraft(libraryDraft(change), access, now)).toBe(
        false,
      )
    expect(guide.photos(access, now)?.A).toBeDefined()
    expect(
      guide.freeze(record(guide), access, now)?.record.library,
    ).toBeUndefined()
  })

  it('holds context changes during every active controller or unresolved resource reservation', () => {
    const guide = session()
    const token = guide.start('A', access, now)!
    expect(guide.setLibraryDraft(libraryDraft(), access, now)).toBe(false)
    guide.cancelRetake(token)
    expect(guide.setLibraryDraft(libraryDraft(), access, now)).toBe(false)
    guide.permissionResolved(token, access, now)
    expect(guide.setLibraryDraft(libraryDraft(), access, now)).toBe(true)
    const next = guide.start('A', access, now)!
    guide.permissionResolved(next, access, now)
    expect(guide.setLibraryDraft(null, access, now)).toBe(false)
    guide.playbackReady(next, access, now)
    expect(guide.setLibraryDraft(null, access, now)).toBe(false)
    guide.shutter(next, dimensions, access, now)
    expect(guide.setLibraryDraft(null, access, now)).toBe(false)
    guide.encoded(next, photo(), dimensions, access, now)
    expect(guide.setLibraryDraft(null, access, now)).toBe(false)
  })

  it('resumes a frozen identity with a fresh attempt while the pre-hide attempt stays stale', () => {
    const guide = session()
    select(guide, 'A')
    select(guide, 'B')
    const frozen = guide.freeze(record(guide), access, now)!
    guide.hold()
    expect(guide.resume(access, now)).toBe(true)
    const retry = guide.pending(access, now)!
    expect(retry.token).toBe(frozen.token)
    expect(
      guide.originalContextCurrent(
        frozen.token,
        access,
        now,
        frozen.attemptGeneration,
      ),
    ).toBe(false)
    expect(
      guide.originalContextCurrent(
        retry.token,
        access,
        now,
        retry.attemptGeneration,
      ),
    ).toBe(true)
    expect(guide.complete(frozen.token, { status: 'held', revision: 7 })).toBe(
      false,
    )
    expect(guide.pending(access, now)?.record.submissionId).toBe(observationId)
  })

  it('holds an expired frozen snapshot until explicit fresh resume, including reconciliation at its successor', () => {
    const guide = session()
    select(guide, 'A')
    select(guide, 'B')
    const frozen = guide.freeze(record(guide), access, now)!
    const later = now + GUIDE_ACCESS_LEASE_MS
    expect(guide.pending(access, later)).toBeNull()
    const fresh = { ...access, verifiedAt: later }
    expect(guide.pending(fresh, later)).toBeNull()
    expect(guide.resume(fresh, later)).toBe(true)
    expect(guide.pending(fresh, later)?.token).toBe(frozen.token)
    const successor = { ...fresh, revision: 8 }
    guide.observe(successor, later)
    guide.hold()
    expect(guide.pending(successor, later)).toBeNull()
    expect(guide.resume(successor, later)).toBe(true)
    expect(guide.pending(successor, later)?.record.submissionId).toBe(
      observationId,
    )
    expect(
      guide.originalContextCurrent(
        frozen.token,
        successor,
        later,
        frozen.attemptGeneration,
      ),
    ).toBe(false)
  })

  it('checks full-frame bounds before encoding and decoded dimensions on completion', () => {
    for (const [width, height, expected] of [
      [1280, 720, true],
      [720, 1280, true],
      [2048, 2048, true],
      [1279, 720, false],
      [1280, 719, false],
      [2049, 1280, false],
      [Number.NaN, 1280, false],
      [1280.5, 720, false],
    ] as const)
      expect(guideFrameAllowed(width, height)).toBe(expected)
    const guide = session()
    const token = guide.start('A', access, now)!
    guide.permissionResolved(token, access, now)
    guide.playbackReady(token, access, now)
    expect(
      guide.shutter(token, { width: 3000, height: 2000 }, access, now),
    ).toBe(false)
    expect(guide.state().pendingEncoder).toBe(false)
    expect(guide.shutter(token, dimensions, access, now)).toBe(true)
    expect(
      guide.encoded(token, photo(), { width: 720, height: 1280 }, access, now),
    ).toBe(false)
  })

  it('bounds three accepted slots plus one candidate and clones all external bytes', () => {
    const guide = session()
    for (const shot of ['A', 'B', 'C'] as const) {
      const token = guide.start(shot, access, now)!
      guide.permissionResolved(token, access, now)
      guide.playbackReady(token, access, now)
      guide.shutter(token, dimensions, access, now)
      guide.encoded(token, photo(1, 12 * 1024 * 1024), dimensions, access, now)
      guide.accept(token, access, now)
    }
    const token = guide.start('A', access, now)!
    guide.permissionResolved(token, access, now)
    guide.playbackReady(token, access, now)
    guide.shutter(token, dimensions, access, now)
    expect(
      guide.encoded(token, photo(2, 12 * 1024 * 1024), dimensions, access, now),
    ).toBe(true)
    expect(guide.state().retainedBytes).toBe(GUIDE_MAX_RETAINED_BYTES)
    guide.accept(token, access, now)
    const view = guide.photos(access, now)!
    view.A!.bytes[3] = 99
    expect(guide.photos(access, now)?.A?.bytes[3]).toBe(2)
    expect(guide.state().retainedBytes).toBe(3 * 12 * 1024 * 1024)
  })

  it('refuses incomplete, mixed, duplicate or changed-photo queue snapshots', () => {
    const guide = session()
    select(guide, 'A')
    expect(guide.freeze(record(guide), access, now)).toBeNull()
    select(guide, 'B', 2)
    const valid = record(guide)
    for (const changed of [
      { ownerUid: 'other' },
      { collectionMode: undefined },
      { submissionId: 'another' },
      { acceptedAt: undefined },
      { photos: [valid.photos[0]!, valid.photos[0]!] },
      {
        photos: valid.photos.map((p) => ({
          ...p,
          objectId: valid.photos[0]!.objectId,
        })),
      },
      { photos: valid.photos.map((p) => ({ ...p, bytes: photo(9).bytes })) },
      { library: { version: 1, request: {}, declarationBytes: null } },
    ])
      expect(
        guide.freeze({ ...valid, ...changed } as QueueRecord, access, now),
      ).toBeNull()
    expect(guide.freeze(valid, access, now)).not.toBeNull()
  })

  it('freezes one detached snapshot; uncertain retry and own successor revision keep the same identities', () => {
    const guide = session()
    select(guide, 'A')
    select(guide, 'B', 2)
    const original = record(guide)
    const frozen = guide.freeze(original, access, now)!
    expect(
      guide.originalContextCurrent(
        frozen.token,
        access,
        now,
        frozen.attemptGeneration,
      ),
    ).toBe(true)
    original.photos[0]!.bytes[3] = 99
    frozen.record.photos[1]!.bytes[3] = 99
    frozen.record.grantId = 'changed'
    const retry = guide.freeze(
      { ...original, submissionId: 'new-identity' },
      access,
      now,
    )!
    expect(retry.token).toBe(frozen.token)
    expect(retry.record.photos.map((p) => p.bytes[3])).toEqual([1, 2])
    expect(retry.record.grantId).toBe('00000000-0000-4000-8000-000000000002')
    expect(guide.complete(frozen.token, { status: 'held', revision: 7 })).toBe(
      false,
    )
    const successor = { ...access, revision: 8 }
    expect(guide.observe(successor, now)).toBe(false)
    expect(
      guide.originalContextCurrent(
        frozen.token,
        successor,
        now,
        frozen.attemptGeneration,
      ),
    ).toBe(false)
    expect(guide.pending(successor, now)?.record.submissionId).toBe(
      observationId,
    )
    expect(guide.start('A', successor, now)).toBeNull()
    expect(
      guide.complete(frozen.token, { status: 'reconciled', revision: 8 }),
    ).toBe(true)
    expect(guide.state().retainedBytes).toBe(0)
    expect(guide.pending(successor, now)).toBeNull()
    expect(
      guide.permissionResolved(selectTokenFromAnotherSession(), access, now),
    ).toBe(false)
  })

  it('releases private RAM on owner/rights loss but retains only the pending outcome fence', () => {
    const guide = session()
    select(guide, 'A')
    select(guide, 'B')
    const frozen = guide.freeze(record(guide), access, now)!
    expect(guide.observe({ ...access, ownerUid: 'other' }, now)).toBe(false)
    expect(guide.state().retainedBytes).toBe(0)
    expect(guide.pending(access, now)).toBeNull()
    expect(guide.freeze(record(session()), access, now)).toBeNull()
    expect(
      guide.originalContextCurrent(
        frozen.token,
        access,
        now,
        frozen.attemptGeneration,
      ),
    ).toBe(false)
    expect(
      guide.complete(frozen.token, { status: 'committed', revision: 8 }),
    ).toBe(true)
    expect(guide.state().outcome).toBe('committed')
    expect(guide.photos(access, now)).toBeNull()
  })
})

function selectTokenFromAnotherSession() {
  return session({ sessionId: 'another-session' }).start('A', access, now)!
}
