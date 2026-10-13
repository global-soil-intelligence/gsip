import {
  type InstrumentDeclaration,
  type LibraryIntakeRequest,
  MAX_LIBRARY_INTAKE_BYTES,
  parseInstrumentDeclaration,
  parseLibraryIntakeRequest,
} from '@gsip/schema'
import { LibraryConflict } from './errors'

/** Separate from capture and the server's capability gate; absent means closed. */
export function isLibraryIntakeLive(): boolean {
  return import.meta.env.VITE_LIBRARY_INTAKE_LIVE === 'true'
}

export type LibraryDraft = {
  version: 1
  intakeId: string
  nodeId: string
  sampleId: string
  submissionId: string
  ownerUid?: string
  /** Device clear fence, never sent to the service. */
  deviceRevision?: number
  depthTop: string
  depthBottom: string
  condition: LibraryIntakeRequest['context']['condition']
  instrument: InstrumentDeclaration | null
  /** Original strict JSON declaration bytes, private and bounded; no original instrument file. */
  declarationBytes: Uint8Array | null
}

export type QueuedLibrary = {
  version: 1
  request: LibraryIntakeRequest
  declarationBytes: Uint8Array | null
  /** Checkpoint only after the server finalized the existing capture lifecycle. */
  photosFinalized?: boolean
}

export function newLibraryDraft(
  nodeId: string,
  ownerUid?: string,
): LibraryDraft {
  return {
    version: 1,
    intakeId: crypto.randomUUID(),
    nodeId,
    sampleId: crypto.randomUUID(),
    submissionId: crypto.randomUUID(),
    ownerUid,
    depthTop: '',
    depthBottom: '',
    condition: 'unknown',
    instrument: null,
    declarationBytes: null,
  }
}

export function queueLibraryDraft(draft: LibraryDraft): QueuedLibrary {
  if (!draft.depthTop.trim() || !draft.depthBottom.trim())
    throw new LibraryConflict()
  try {
    return {
      version: 1,
      request: parseLibraryIntakeRequest(
        JSON.stringify({
          schema_version: 'gsip-library-intake-v1',
          intake_id: draft.intakeId,
          node_id: draft.nodeId,
          sample_id: draft.sampleId,
          submission_id: draft.submissionId,
          protocol_version: 'gsip-capture-v1',
          context: {
            depth_top_cm: Number(draft.depthTop),
            depth_bottom_cm: Number(draft.depthBottom),
            condition: draft.condition,
          },
          instrument_declaration: draft.instrument,
        }),
      ),
      declarationBytes: draft.declarationBytes,
    }
  } catch {
    throw new LibraryConflict()
  }
}

/** Size is checked before reading, and the shared parser checks UTF-8 size and duplicate keys. */
export async function readInstrumentDeclaration(file: File): Promise<{
  instrument: InstrumentDeclaration
  declarationBytes: Uint8Array
}> {
  if (file.size > MAX_LIBRARY_INTAKE_BYTES) throw new LibraryConflict()
  try {
    const raw = await file.text()
    const instrument = parseInstrumentDeclaration(raw)
    return { instrument, declarationBytes: new TextEncoder().encode(raw) }
  } catch {
    throw new LibraryConflict()
  }
}
