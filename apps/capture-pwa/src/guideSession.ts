import {
  MAX_LIBRARY_INTAKE_BYTES,
  parseInstrumentDeclaration,
} from '@gsip/schema'
import { queueLibraryDraft, type LibraryDraft } from './library'
import { isJpeg, MAX_PHOTO_BYTES } from './platform/camera'
import type { CapturedPhoto } from './platform/types'
import type { QueueRecord, ShotType } from './types'

export const GUIDE_ACCESS_LEASE_MS = 15_000
export const GUIDE_MAX_RETAINED_BYTES = 50_331_648
const shots: readonly ShotType[] = ['A', 'B', 'C']
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

/** Verified facts supplied by App. This module never authenticates, refreshes or polls. */
export type GuideAccess = {
  pilot: boolean
  native: boolean
  rightsView: boolean
  libraryLive: boolean
  canCollect: boolean
  rightsHold: boolean
  ownerUid: string | null
  anonymous: boolean
  authGeneration: number
  revision: number
  verifiedAt: number
}

export type GuideEntry = {
  sessionId: string
  observationId: string
  access: GuideAccess
  restorationComplete: boolean
  pendingPickerReads: number
  pickerPhotosEmpty: boolean
  persistedPhotosEmpty: boolean
  libraryDraft: LibraryDraft | null
}

export type GuideToken = Readonly<{
  sessionId: string
  observationId: string
  ownerUid: string
  authGeneration: number
  revision: number
  shotType: ShotType
  shotIntent: number
  generation: number
}>

export type GuideCommitToken = Readonly<{
  sessionId: string
  submissionId: string
  generation: number
}>

export type GuidePendingObservation = {
  token: GuideCommitToken
  /** Captured once per queue attempt, so a pre-hide NEW write cannot revive after resume. */
  attemptGeneration: number
  revision: number
  /** A detached copy in the unchanged queue format; mutating it cannot change a retry. */
  record: QueueRecord
}

export type GuideQueueOutcome = {
  status: 'committed' | 'reconciled' | 'held'
  revision: number
}

type Dimensions = { width: number; height: number }
type Photos = Partial<Record<ShotType, CapturedPhoto>>
type Phase =
  | 'idle'
  | 'requesting'
  | 'playback'
  | 'preview'
  | 'encoding'
  | 'review'
  | 'selected'
  | 'held'
  | 'queuing'
  | 'closed'

function safeCounter(value: number): boolean {
  return (
    Number.isSafeInteger(value) && value >= 0 && value < Number.MAX_SAFE_INTEGER
  )
}

function eligible(access: GuideAccess): boolean {
  return (
    access.pilot &&
    !access.native &&
    !access.rightsView &&
    access.libraryLive &&
    access.canCollect &&
    !access.rightsHold &&
    !access.anonymous &&
    typeof access.ownerUid === 'string' &&
    access.ownerUid.length > 0 &&
    access.ownerUid.length <= 128 &&
    safeCounter(access.authGeneration) &&
    safeCounter(access.revision)
  )
}

export function guideAccessAllowed(access: GuideAccess, now: number): boolean {
  return (
    eligible(access) &&
    Number.isFinite(now) &&
    Number.isFinite(access.verifiedAt) &&
    access.verifiedAt <= now &&
    now - access.verifiedAt < GUIDE_ACCESS_LEASE_MS
  )
}

/** Optional guide engineering bounds, never global admission or calibration thresholds. */
export function guideFrameAllowed(width: number, height: number): boolean {
  return (
    Number.isSafeInteger(width) &&
    Number.isSafeInteger(height) &&
    Math.max(width, height) <= 2048 &&
    width * height <= 4_194_304 &&
    Math.min(width, height) >= 720 &&
    Math.max(width, height) >= 1280
  )
}

export function createGuideSession(
  entry: GuideEntry,
  now: number,
): GuideSession | null {
  const draft = entry.libraryDraft
  if (
    !guideAccessAllowed(entry.access, now) ||
    !entry.sessionId ||
    entry.sessionId.length > 128 ||
    !uuid.test(entry.observationId) ||
    !entry.restorationComplete ||
    entry.pendingPickerReads !== 0 ||
    !entry.pickerPhotosEmpty ||
    !entry.persistedPhotosEmpty ||
    (draft && !ownedLibraryContext(draft, entry.access))
  )
    return null
  return new GuideSessionState(entry)
}

export type GuideSession = GuideSessionState

/**
 * Pure RAM ownership contract, with no media, timers, auth, queue or storage effects.
 * Explicit start/shutter/accept/freeze/resume callers must pass the fresh access result obtained
 * for that action. The lease is a maximum age, not permission to skip that refresh.
 * Controllers own disposal of every rejected result. Cancel/hold never settle browser promises:
 * their original slots remain reserved until permissionResolved/encoded reports settlement.
 */
class GuideSessionState {
  private readonly entry: GuideEntry
  private phase: Phase = 'idle'
  private generation = 0
  private shotIntents: Record<ShotType, number> = { A: 0, B: 0, C: 0 }
  private selected: Photos = {}
  private active: GuideToken | null = null
  private request: GuideToken | null = null
  private encoder: GuideToken | null = null
  private frame: (Dimensions & { takenAt: number }) | null = null
  private candidate: CapturedPhoto | null = null
  private commitToken: GuideCommitToken | null = null
  private frozen: QueueRecord | null = null
  private outcome: 'none' | 'pending' | 'committed' | 'discarded' = 'none'
  private privateReleased = false

  /** Use createGuideSession, which verifies the entry/restoration prerequisites. */
  constructor(entry: GuideEntry) {
    this.entry = structuredClone(entry)
  }

  state() {
    return {
      phase: this.phase,
      selectedShots: shots.filter((shot) => this.selected[shot] !== undefined),
      // Module-owned retained buffers only. 4B must also release/budget every caller copy.
      retainedBytes: this.retainedBytes(),
      pendingRequest: this.request !== null,
      pendingEncoder: this.encoder !== null,
      hasCandidate: this.candidate !== null,
      outcome: this.outcome,
    }
  }

  /** Observe current facts even while held. A positive check never resumes a held session. */
  observe(access: GuideAccess, now: number): boolean {
    if (!this.sameOwner(access) || !eligible(access)) {
      this.releasePrivate()
      return false
    }
    if (access.revision !== this.entry.access.revision) {
      this.invalidateController()
      this.selected = {}
      this.entry.libraryDraft = null
      if (!this.frozen || this.phase !== 'held') this.phase = 'closed'
      // In particular, our own r+1 must not erase an uncertain immutable queue outcome.
      return false
    }
    if (!guideAccessAllowed(access, now)) {
      this.hold()
      return false
    }
    return this.phase !== 'closed' && this.phase !== 'held'
  }

  start(
    shotType: ShotType,
    access: GuideAccess,
    now: number,
  ): GuideToken | null {
    if (
      !shots.includes(shotType) ||
      !this.observe(access, now) ||
      this.commitToken ||
      this.request ||
      this.encoder ||
      !['idle', 'selected', 'review'].includes(this.phase)
    )
      return null
    this.invalidateController()
    this.shotIntents[shotType] += 1
    const token = Object.freeze({
      sessionId: this.entry.sessionId,
      observationId: this.entry.observationId,
      ownerUid: this.entry.access.ownerUid!,
      authGeneration: this.entry.access.authGeneration,
      revision: this.entry.access.revision,
      shotType,
      shotIntent: this.shotIntents[shotType],
      generation: this.generation,
    })
    this.active = token
    this.request = token
    this.phase = 'requesting'
    return token
  }

  permissionResolved(
    token: GuideToken,
    access: GuideAccess,
    now: number,
  ): boolean {
    if (this.request !== token) return false
    this.request = null
    if (!this.current(token, access, now) || this.phase !== 'requesting')
      return false
    this.phase = 'playback'
    return true
  }

  playbackReady(token: GuideToken, access: GuideAccess, now: number): boolean {
    if (!this.current(token, access, now) || this.phase !== 'playback')
      return false
    this.phase = 'preview'
    return true
  }

  shutter(
    token: GuideToken,
    frame: Dimensions,
    access: GuideAccess,
    now: number,
  ): boolean {
    if (
      !this.current(token, access, now) ||
      this.phase !== 'preview' ||
      this.encoder ||
      !guideFrameAllowed(frame.width, frame.height)
    )
      return false
    this.frame = { width: frame.width, height: frame.height, takenAt: now }
    this.encoder = token
    this.phase = 'encoding'
    return true
  }

  encoded(
    token: GuideToken,
    photo: CapturedPhoto | null,
    decoded: Dimensions | null,
    access: GuideAccess,
    now: number,
  ): boolean {
    if (this.encoder !== token) return false
    this.encoder = null
    if (!this.current(token, access, now) || this.phase !== 'encoding')
      return false
    const frame = this.frame
    if (
      !frame ||
      !decoded ||
      !photo ||
      decoded.width !== frame.width ||
      decoded.height !== frame.height ||
      photo.mimeType !== 'image/jpeg' ||
      photo.method !== 'camera' ||
      !isJpeg(photo.bytes) ||
      photo.bytes.byteLength > MAX_PHOTO_BYTES ||
      this.retainedBytes() + photo.bytes.byteLength > GUIDE_MAX_RETAINED_BYTES
    ) {
      this.cancelRetake(token)
      return false
    }
    try {
      this.candidate = {
        bytes: new Uint8Array(photo.bytes),
        mimeType: 'image/jpeg',
        method: 'camera',
        takenAt: frame.takenAt,
      }
    } catch {
      this.cancelRetake(token)
      return false
    }
    this.frame = null
    this.phase = 'review'
    return true
  }

  accept(token: GuideToken, access: GuideAccess, now: number): boolean {
    if (
      !this.current(token, access, now) ||
      this.phase !== 'review' ||
      !this.candidate
    )
      return false
    this.selected[token.shotType] = this.candidate
    this.candidate = null
    this.invalidateController()
    this.phase = 'selected'
    return true
  }

  /** Copies have caller ownership. No caller ever receives an alias to retained private bytes. */
  photos(access: GuideAccess, now: number): Photos | null {
    return this.observe(access, now) && !this.commitToken
      ? structuredClone(this.selected)
      : null
  }

  cancelRetake(token: GuideToken): boolean {
    if (this.active !== token) return false
    this.invalidateController()
    this.phase = Object.keys(this.selected).length ? 'selected' : 'idle'
    return true
  }

  /** Hidden/pagehide/lease timeout: no automatic camera restart and no display of held photos. */
  hold(): void {
    if (this.phase === 'closed' && !this.frozen) return
    this.invalidateController()
    this.phase = 'held'
  }

  resume(access: GuideAccess, now: number): boolean {
    if (!this.sameOwner(access) || !eligible(access)) {
      this.releasePrivate()
      return false
    }
    if (this.phase !== 'held' || !guideAccessAllowed(access, now)) return false
    if (access.revision !== this.entry.access.revision) {
      this.observe(access, now)
      if (!this.frozen) return false
      // Explicit fresh access may reveal a pending outcome for reconciliation only.
      this.phase = 'closed'
      return true
    }
    this.phase = this.commitToken
      ? 'queuing'
      : Object.keys(this.selected).length
        ? 'selected'
        : 'idle'
    return true
  }

  /** The caller owns the confirmation UI. Refusal has no mutation, including pending work. */
  cancel(confirmedDiscard: boolean): boolean {
    if (
      (Object.keys(this.selected).length || this.candidate || this.frozen) &&
      !confirmedDiscard
    )
      return false
    this.releasePrivate()
    return true
  }

  /**
   * Bind the person's completed optional context after photo review. The camera observation
   * intent stays fixed; an opted-in draft supplies its existing canonical submission identity.
   * The caller must coordinate persistence of this exact context separately before queueing.
   */
  setLibraryDraft(
    draft: LibraryDraft | null,
    access: GuideAccess,
    now: number,
  ): boolean {
    if (
      !this.observe(access, now) ||
      this.commitToken ||
      this.request ||
      this.encoder ||
      this.active ||
      this.candidate ||
      !['idle', 'selected'].includes(this.phase)
    )
      return false
    try {
      if (draft) {
        if (!ownedLibraryContext(draft, access)) return false
        // No default depth, sample or declaration is invented by this binding.
        queueLibraryDraft(draft)
      }
      this.entry.libraryDraft = structuredClone(draft)
      return true
    } catch {
      return false
    }
  }

  freeze(
    record: QueueRecord,
    access: GuideAccess,
    now: number,
  ): GuidePendingObservation | null {
    if (this.commitToken) return this.pending(access, now)
    if (
      !this.observe(access, now) ||
      this.request ||
      this.encoder ||
      this.active ||
      this.candidate ||
      !this.selected.A ||
      !this.selected.B ||
      !this.recordMatches(record)
    )
      return null
    const frozen: QueueRecord = structuredClone({
      ...record,
      photos: record.photos.map((photo) => ({
        ...photo,
        bytes: new Uint8Array(),
      })),
    })
    // Transfer the internally owned selected buffers into the immutable pending snapshot.
    for (const photo of frozen.photos)
      photo.bytes = this.selected[photo.shotType]!.bytes
    this.frozen = frozen
    this.selected = {}
    this.entry.libraryDraft = null
    this.commitToken = Object.freeze({
      sessionId: this.entry.sessionId,
      submissionId: record.submissionId,
      generation: this.generation,
    })
    this.outcome = 'pending'
    this.phase = 'queuing'
    return this.pending(access, now)
  }

  /** Reconciliation may outlive the original revision; NEW insertion may not. */
  pending(access: GuideAccess, now: number): GuidePendingObservation | null {
    if (!this.sameOwner(access) || !eligible(access)) {
      this.releasePrivate()
      return null
    }
    if (!guideAccessAllowed(access, now)) {
      this.hold()
      return null
    }
    if (
      this.phase === 'held' ||
      this.privateReleased ||
      !this.frozen ||
      !this.commitToken
    )
      return null
    return {
      token: this.commitToken,
      attemptGeneration: this.generation,
      revision: this.entry.access.revision,
      record: structuredClone(this.frozen),
    }
  }

  originalContextCurrent(
    token: GuideCommitToken,
    access: GuideAccess,
    now: number,
    attemptGeneration: number,
  ): boolean {
    return (
      this.observe(access, now) &&
      token === this.commitToken &&
      attemptGeneration === this.generation &&
      this.phase === 'queuing' &&
      !this.privateReleased &&
      this.frozen !== null
    )
  }

  /** Only a durable transaction result clears RAM. Held/uncertain attempts retain the same IDs. */
  complete(token: GuideCommitToken, result: GuideQueueOutcome): boolean {
    if (
      token !== this.commitToken ||
      result.status === 'held' ||
      !Number.isSafeInteger(result.revision) ||
      result.revision <= this.entry.access.revision ||
      (result.status === 'committed' &&
        result.revision !== this.entry.access.revision + 1)
    )
      return false
    this.releasePrivate()
    this.outcome = 'committed'
    return true
  }

  private sameOwner(access: GuideAccess): boolean {
    return (
      access.ownerUid === this.entry.access.ownerUid &&
      access.authGeneration === this.entry.access.authGeneration &&
      !access.anonymous
    )
  }

  private current(
    token: GuideToken,
    access: GuideAccess,
    now: number,
  ): boolean {
    return (
      this.observe(access, now) &&
      this.active === token &&
      token.generation === this.generation
    )
  }

  private invalidateController(): void {
    this.generation += 1
    this.active = null
    this.candidate = null
    this.frame = null
  }

  private releasePrivate(): void {
    this.invalidateController()
    this.selected = {}
    this.frozen = null
    this.entry.libraryDraft = null
    this.privateReleased = true
    this.phase = 'closed'
    if (this.outcome !== 'committed') this.outcome = 'discarded'
  }

  private retainedBytes(): number {
    return (
      Object.values(this.selected).reduce(
        (sum, photo) => sum + photo.bytes.byteLength,
        0,
      ) +
      (this.candidate?.bytes.byteLength ?? 0) +
      (this.frozen?.photos.reduce(
        (sum, photo) => sum + photo.bytes.byteLength,
        0,
      ) ?? 0)
    )
  }

  private recordMatches(record: QueueRecord): boolean {
    const draft = this.entry.libraryDraft
    if (
      record.ownerUid !== this.entry.access.ownerUid ||
      record.collectionMode !== 'invited_private' ||
      record.submissionId !==
        (draft?.submissionId ?? this.entry.observationId) ||
      !uuid.test(record.grantId) ||
      !record.acceptedAt ||
      !Number.isFinite(Date.parse(record.acceptedAt)) ||
      !record.termsVersion ||
      record.photos.length !== Object.keys(this.selected).length ||
      new Set(record.photos.map((photo) => photo.shotType)).size !==
        record.photos.length ||
      new Set(record.photos.map((photo) => photo.objectId)).size !==
        record.photos.length
    )
      return false
    if (
      !record.photos.every((photo) => {
        const selected = this.selected[photo.shotType]
        return (
          selected &&
          uuid.test(photo.objectId) &&
          photo.mimeType === selected.mimeType &&
          sameBytes(photo.bytes, selected.bytes)
        )
      })
    )
      return false
    if (!draft) return record.library === undefined
    try {
      return sameValue(record.library, queueLibraryDraft(draft))
    } catch {
      return false
    }
  }
}

/** Entry may have blank depth fields; explicit context binding and freeze require real bounds. */
function ownedLibraryContext(
  draft: LibraryDraft,
  access: GuideAccess,
): boolean {
  if (
    draft.version !== 1 ||
    draft.ownerUid !== access.ownerUid ||
    draft.deviceRevision !== access.revision ||
    ![draft.intakeId, draft.nodeId, draft.sampleId, draft.submissionId].every(
      (id) => uuid.test(id),
    ) ||
    typeof draft.depthTop !== 'string' ||
    typeof draft.depthBottom !== 'string' ||
    draft.depthTop.length > MAX_LIBRARY_INTAKE_BYTES ||
    draft.depthBottom.length > MAX_LIBRARY_INTAKE_BYTES ||
    !['dry', 'moist', 'wet', 'unknown'].includes(draft.condition)
  )
    return false
  const bytes = draft.declarationBytes
  if (bytes === null) return draft.instrument === null
  if (
    !ArrayBuffer.isView(bytes) ||
    Object.prototype.toString.call(bytes) !== '[object Uint8Array]' ||
    bytes.byteLength > MAX_LIBRARY_INTAKE_BYTES
  )
    return false
  try {
    return sameValue(
      draft.instrument,
      parseInstrumentDeclaration(
        new TextDecoder('utf-8', { fatal: true }).decode(bytes),
      ),
    )
  } catch {
    return false
  }
}

function sameBytes(left: Uint8Array, right: Uint8Array): boolean {
  return (
    left.byteLength === right.byteLength &&
    left.every((value, index) => right[index] === value)
  )
}

function sameValue(left: unknown, right: unknown): boolean {
  if (left instanceof Uint8Array && right instanceof Uint8Array)
    return sameBytes(left, right)
  if (
    left === null ||
    right === null ||
    typeof left !== 'object' ||
    typeof right !== 'object'
  )
    return left === right
  const a = Object.keys(left).sort()
  const b = Object.keys(right).sort()
  return (
    a.length === b.length &&
    a.every(
      (key, index) =>
        key === b[index] &&
        sameValue(Reflect.get(left, key), Reflect.get(right, key)),
    )
  )
}
