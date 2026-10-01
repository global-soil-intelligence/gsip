import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import type { Database } from '@gsip/schema'
import { fuzzLocation } from './geo'
import type { QueueRecord } from './types'

export type GsipClient = SupabaseClient<Database>

export function photoStoragePath(
  uid: string,
  record: QueueRecord,
  photo: QueueRecord['photos'][number],
): string {
  return `${uid}/${record.submissionId}/${photo.shotType}/${photo.objectId}.jpg`
}

export function isServiceConfigured(): boolean {
  return Boolean(
    import.meta.env.VITE_SUPABASE_URL &&
    import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
  )
}

export function createGsipClient(): GsipClient {
  const url = import.meta.env.VITE_SUPABASE_URL
  const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY
  if (!url || !key) throw new Error('GSIP service configuration is unavailable')
  return createClient<Database>(url, key, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  })
}

async function userId(client: GsipClient): Promise<string> {
  const { data } = await client.auth.getSession()
  if (data.session?.user.id) return data.session.user.id
  const { data: signedIn, error } = await client.auth.signInAnonymously()
  if (error || !signedIn.user)
    throw error ?? new Error('Anonymous sign-in failed')
  return signedIn.user.id
}

async function contributorId(client: GsipClient, uid: string): Promise<string> {
  const existing = await client
    .from('contributors')
    .select('id')
    .eq('auth_uid', uid)
    .maybeSingle()
  if (existing.error) throw existing.error
  if (existing.data) return existing.data.id

  const created = await client
    .from('contributors')
    .insert({
      auth_uid: uid,
      handle: `soil-${uid.replaceAll('-', '').slice(0, 12)}`,
    })
    .select('id')
    .single()
  if (created.error) throw created.error
  return created.data.id
}

function duplicateUpload(error: {
  message: string
  statusCode?: string | number
}): boolean {
  return (
    Number(error.statusCode) === 409 ||
    /duplicate|already exists/i.test(error.message)
  )
}

export async function submitQueued(
  client: GsipClient,
  record: QueueRecord,
): Promise<void> {
  const uid = await userId(client)
  const contributor = await contributorId(client, uid)
  const grant = await client
    .from('contribution_grants')
    .select('id')
    .eq('id', record.grantId)
    .maybeSingle()
  if (grant.error) throw grant.error
  if (!grant.data) {
    const created = await client.from('contribution_grants').insert({
      accepted_at: record.capturedAt,
      attribution_name: record.attributionName,
      contributor_id: contributor,
      id: record.grantId,
      terms_version: record.termsVersion,
    })
    if (created.error) throw created.error
  }

  const location = fuzzLocation(record.latitude, record.longitude)
  const existingSubmission = await client
    .from('submissions')
    .select('id')
    .eq('id', record.submissionId)
    .maybeSingle()
  if (existingSubmission.error) throw existingSubmission.error
  if (!existingSubmission.data) {
    const created = await client.from('submissions').insert({
      captured_at: record.capturedAt,
      contributor_id: contributor,
      disturbed: record.disturbed,
      device_model: record.deviceModel,
      geom_precise: `POINT(${record.longitude} ${record.latitude})`,
      gps_accuracy_m: record.accuracyM,
      grant_id: record.grantId,
      h3_r6: location.h3R6,
      h3_r8: location.h3R8,
      id: record.submissionId,
      land_cover: record.landCover,
      status: 'pending',
      surface_condition: record.surfaceCondition,
    })
    if (created.error) throw created.error
  }

  for (const photo of record.photos) {
    const path = photoStoragePath(uid, record, photo)
    const uploaded = await client.storage
      .from('incoming-photos')
      .upload(path, photo.bytes, {
        contentType: photo.mimeType,
        upsert: false,
      })
    if (uploaded.error && !duplicateUpload(uploaded.error)) throw uploaded.error

    const existingPhoto = await client
      .from('photos')
      .select('id')
      .eq('submission_id', record.submissionId)
      .eq('shot_type', photo.shotType)
      .maybeSingle()
    if (existingPhoto.error) throw existingPhoto.error
    if (!existingPhoto.data) {
      const created = await client.from('photos').insert({
        shot_type: photo.shotType,
        storage_path: path,
        submission_id: record.submissionId,
      })
      if (created.error) throw created.error
    }
  }
}
