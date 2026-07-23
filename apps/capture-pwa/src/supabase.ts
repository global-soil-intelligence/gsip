import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import type { Database } from '@gsip/schema'
import { fuzzLocation } from './geo'
import type { QueueRecord } from './types'
import { enqueue } from './queue'
import { authRedirect } from './platform'
import { captureEnabled } from './config'

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
      flowType: 'pkce',
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
  if (!captureEnabled()) throw new Error('Contribution intake is closed.')
  const intake = await client.rpc('is_intake_open')
  if (intake.error || intake.data !== true)
    throw new Error(
      'Contribution intake is unavailable or closed. Your observation stays on this device.',
    )
  if (
    !record.photos.some((p) => p.shotType === 'A') ||
    !record.photos.some((p) => p.shotType === 'B')
  )
    throw new Error('Both required photos are needed.')
  const uid = await userId(client)
  if (record.ownerId && record.ownerId !== uid)
    throw new Error('Sign in with the account that started this upload.')
  if (!record.ownerId) {
    record.ownerId = uid
    await enqueue(record)
  }
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
    .select('id,upload_completed_at')
    .eq('id', record.submissionId)
    .maybeSingle()
  if (existingSubmission.error) throw existingSubmission.error
  if (!existingSubmission.data) {
    const created = await client.from('submissions').insert({
      captured_at: record.capturedAt,
      expected_shots: record.photos.map((p) => p.shotType).sort(),
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

  if (existingSubmission.data?.upload_completed_at) return

  for (const photo of record.photos) {
    const path = photoStoragePath(uid, record, photo)
    const existingPhoto = await client
      .from('photos')
      .select('id')
      .eq('submission_id', record.submissionId)
      .eq('shot_type', photo.shotType)
      .maybeSingle()
    if (existingPhoto.error) throw existingPhoto.error
    if (!existingPhoto.data) {
      const uploaded = await client.storage
        .from('incoming-photos')
        .upload(path, photo.bytes, {
          contentType: photo.mimeType,
          upsert: false,
        })
      if (uploaded.error && !duplicateUpload(uploaded.error))
        throw uploaded.error

      const created = await client.from('photos').insert({
        shot_type: photo.shotType,
        storage_path: path,
        submission_id: record.submissionId,
      })
      if (created.error) throw created.error
    }
  }

  const completed = await client.rpc('complete_submission_upload', {
    p_submission_id: record.submissionId,
  })
  if (completed.error) throw completed.error
  // Enrichment is handled by the durable scheduled queue. Local data cleanup
  // must not wait for the external sources to respond.
}

export async function connectEmail(
  client: GsipClient,
  email: string,
): Promise<'email_change' | 'email'> {
  const { data, error: sessionError } = await client.auth.getSession()
  if (sessionError) throw sessionError
  if (data.session?.user.is_anonymous) {
    const { error } = await client.auth.updateUser(
      { email },
      { emailRedirectTo: authRedirect() },
    )
    if (error)
      throw new Error(
        'Could not link this email. If it belongs to another account, finish current uploads before switching accounts.',
      )
    return 'email_change'
  }
  const { error } = await client.auth.signInWithOtp({
    email,
    options: { emailRedirectTo: authRedirect() },
  })
  if (error) throw error
  return 'email'
}

export async function observationHistory(client: GsipClient) {
  const { data: session } = await client.auth.getSession()
  if (!session.session) return []
  const { data, error } = await client
    .from('submissions')
    .select(
      'id,captured_at,status,h3_r8,land_cover,upload_completed_at,priors(source,property,value,unit,uncertainty_lo,uncertainty_hi,depth_top_cm,depth_bottom_cm),qa_events(check_name,passed)',
    )
    .order('captured_at', { ascending: false })
    .limit(100)
  if (error)
    throw new Error(
      'Could not refresh your observations. Local drafts are still available.',
    )
  return data ?? []
}
export type RemoteObservation = Awaited<
  ReturnType<typeof observationHistory>
>[number]
