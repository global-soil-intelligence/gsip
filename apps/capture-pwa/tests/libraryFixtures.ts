import type { GsipClient } from '../src/supabase'
import type { QueueRecord } from '../src/types'

export const uuid = (n: number) =>
  `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`
export const request = {
  schema_version: 'gsip-library-intake-v1',
  intake_id: uuid(1),
  node_id: uuid(2),
  sample_id: uuid(3),
  submission_id: uuid(4),
  protocol_version: 'gsip-capture-v1',
  context: { depth_top_cm: 0, depth_bottom_cm: 5, condition: 'unknown' },
  instrument_declaration: null,
}
export function record(): QueueRecord {
  return {
    accuracyM: null,
    attributionName: 'Anonymous soil contributor',
    capturedAt: new Date().toISOString(),
    deviceModel: 'synthetic',
    disturbed: false,
    grantId: uuid(5),
    landCover: 'bare',
    latitude: 1,
    longitude: 1,
    photos: ['A', 'B'].map((shotType, n) => ({
      bytes: new Uint8Array([255, 216, 255]),
      mimeType: 'image/jpeg',
      objectId: uuid(6 + n),
      shotType: shotType as 'A' | 'B',
    })),
    queuedAt: new Date().toISOString(),
    submissionId: uuid(4),
    surfaceCondition: 'dry',
    termsVersion: '2026-07-22-v1',
    library: {
      version: 1,
      request: structuredClone(request),
      declarationBytes: null,
    },
  } as QueueRecord
}
export function service() {
  const log: string[] = [],
    intakes: unknown[] = []
  const receipts: string[] = []
  const state = {
    available: true,
    version: 'gsip-library-intake-v1',
    receipt: true,
    lost: false,
    failure: '',
    uid: 'owner-a',
    failUpload: false,
  }
  const client = {
    auth: {
      getSession: async () => {
        log.push('session')
        return {
          data: { session: state.uid ? { user: { id: state.uid } } : null },
          error: null,
        }
      },
      signInAnonymously: async () => {
        log.push('signin')
        return { data: { user: { id: 'owner-a' } }, error: null }
      },
    },
    from: (table: string) => {
      const q = {
        select: () => q,
        eq: () => q,
        insert: () => {
          log.push(`insert:${table}`)
          return q
        },
        single: async () => ({ data: { id: uuid(9) }, error: null }),
        maybeSingle: async () => ({
          data:
            table === 'service_state'
              ? { capture_open: true }
              : table === 'contributors'
                ? { id: uuid(9) }
                : null,
          error: null,
        }),
        then: (resolve: (r: unknown) => unknown) =>
          Promise.resolve({ data: null, error: null }).then(resolve),
      }
      return q
    },
    storage: {
      from: () => ({
        upload: async () => {
          log.push('upload')
          if (state.failUpload) {
            state.failUpload = false
            return { error: { statusCode: 503, message: 'retry' } }
          }
          return { error: null }
        },
      }),
    },
    rpc: async (name: string, args: Record<string, unknown>) => {
      log.push(name)
      if (name === 'library_intake_capabilities')
        return {
          data: { version: state.version, available: state.available },
          error: null,
        }
      if (name === 'record_library_intake') {
        intakes.push(structuredClone(args.p_request))
        if (state.failure)
          return {
            data: null,
            error: { code: state.failure, message: 'private sentinel' },
          }
        if (state.lost) {
          state.lost = false
          throw Error('connection lost')
        }
        if (state.receipt)
          receipts.push(
            intakes.length > 1 ? 'already_stored' : 'stored_private_unverified',
          )
        return {
          data: state.receipt
            ? {
                intake_id: (args.p_request as { intake_id: string }).intake_id,
                status:
                  intakes.length > 1
                    ? 'already_stored'
                    : 'stored_private_unverified',
              }
            : null,
          error: null,
        }
      }
      return { data: null, error: null }
    },
    functions: {
      invoke: async () => {
        log.push('prior')
        return { error: null }
      },
    },
  } as unknown as GsipClient
  return { client, state, log, intakes, receipts }
}
