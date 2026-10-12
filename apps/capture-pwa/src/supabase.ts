import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import type { Database } from '@gsip/schema'
import { AccountChanged, isWithdrawal, RecordWithdrawn } from './errors'
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

export type ServiceState = 'open' | 'closed' | 'unknown'

/**
 * Reads the database capture gate (WP-6b). The database enforces it on every insert; the app
 * reads it only to pause sync and explain why, so any failure here is "unknown", not closed.
 */
export async function fetchServiceState(
  client: GsipClient,
): Promise<ServiceState> {
  try {
    const { data, error } = await client
      .from('service_state')
      .select('capture_open')
      .maybeSingle()
    if (error || !data) return 'unknown'
    return data.capture_open ? 'open' : 'closed'
  } catch {
    return 'unknown'
  }
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

const LAST_UID_KEY = 'gsip-last-auth-uid'

function rememberUid(uid: string): void {
  try {
    window.localStorage.setItem(LAST_UID_KEY, uid)
  } catch {
    // Storage can be unavailable (private mode); ownership then relies on the live session.
  }
}

function forgetUid(): void {
  try {
    window.localStorage.removeItem(LAST_UID_KEY)
  } catch {
    // Nothing to forget.
  }
}

function lastKnownUid(): string | undefined {
  try {
    return window.localStorage.getItem(LAST_UID_KEY) ?? undefined
  } catch {
    return undefined
  }
}

/**
 * The account a new observation belongs to: the signed-in user, or (offline, with a session that
 * cannot refresh) the last account seen on this device. Undefined only on a device that has never
 * signed in; its first sync creates the anonymous account.
 */
export async function recordOwner(
  client: GsipClient | null,
): Promise<string | undefined> {
  if (!client) return undefined
  try {
    const { data } = await client.auth.getSession()
    const uid = data.session?.user.id
    if (uid) {
      rememberUid(uid)
      return uid
    }
  } catch {
    // Fall back to the last account seen here.
  }
  return lastKnownUid()
}

/**
 * The account to send a record as. A record queued under one account is never sent as another,
 * and a device whose account is gone never silently creates a new one for it (WP-6d).
 */
async function senderUid(
  client: GsipClient,
  record: QueueRecord,
): Promise<string> {
  const { data, error } = await client.auth.getSession()
  if (error) throw error
  const uid = data.session?.user.id
  if (uid) {
    if (record.ownerUid && record.ownerUid !== uid) throw new AccountChanged()
    rememberUid(uid)
    return uid
  }
  if (record.ownerUid) throw new AccountChanged()
  const { data: signedIn, error: signInError } =
    await client.auth.signInAnonymously()
  if (signInError || !signedIn.user)
    throw signInError ?? new Error('Anonymous sign-in failed')
  rememberUid(signedIn.user.id)
  return signedIn.user.id
}

function refusal(error: unknown): unknown {
  return isWithdrawal(error) ? new RecordWithdrawn() : error
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
  if (created.error) throw refusal(created.error)
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
  const uid = await senderUid(client, record)
  const contributor = await contributorId(client, uid)
  const grant = await client
    .from('contribution_grants')
    .select('id')
    .eq('id', record.grantId)
    .maybeSingle()
  if (grant.error) throw grant.error
  if (!grant.data) {
    // The grant records when the person accepted the terms, never the photo's own timestamp.
    const created = await client.from('contribution_grants').insert({
      accepted_at: record.acceptedAt ?? record.queuedAt,
      attribution_name: record.attributionName,
      contributor_id: contributor,
      id: record.grantId,
      terms_version: record.termsVersion,
    })
    if (created.error) throw refusal(created.error)
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
    if (created.error) throw refusal(created.error)
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
      if (created.error) throw refusal(created.error)
    }
  }

  // Shots A and B are uploaded: finalize so the server can settle QA status.
  // Finalize is idempotent, so a retry after a lost response is safe.
  const finalized = await client.rpc('finalize_submission', {
    p_submission_id: record.submissionId,
  })
  if (finalized.error) throw finalized.error

  // The durable prior_jobs row is created by the submission trigger. This
  // best-effort invocation starts enrichment immediately; an upstream outage
  // must not retain private capture data in the device queue after upload.
  await client.functions.invoke('prior-attach', {
    body: { submissionId: record.submissionId },
  })
}

export type DeletionKind = 'withdraw_contributions' | 'delete_account'
export type DeletionStatus = {
  completedAt: string | null
  kind: DeletionKind
  requestedAt: string
  status: 'pending' | 'processing' | 'completed'
}
export type DeletionOutcome = 'requested' | 'already_open' | 'no_account'

/**
 * The signed-in contributor, or null when this device holds no account at all. Rights requests
 * never sign in: creating an account in order to delete it would be absurd. A session that exists
 * but cannot be read right now (offline with an expired token, an auth outage) is an error, never
 * "no account": that would wrongly tell the person nothing of theirs is stored.
 */
async function existingContributor(client: GsipClient): Promise<string | null> {
  const { data, error } = await client.auth.getSession()
  if (error) throw error
  const uid = data.session?.user.id
  if (!uid) return null
  const found = await client
    .from('contributors')
    .select('id')
    .eq('auth_uid', uid)
    .maybeSingle()
  if (found.error) throw found.error
  return found.data?.id ?? null
}

/** The contributor's latest withdrawal or deletion request, if they have one. */
export async function latestDeletionRequest(
  client: GsipClient,
): Promise<DeletionStatus | null> {
  if (!(await existingContributor(client))) return null
  const { data, error } = await client
    .from('deletion_requests')
    .select('kind, status, requested_at, completed_at')
    .order('requested_at', { ascending: false })
    .limit(1)
    .maybeSingle()
  if (error) throw error
  if (!data) return null
  return {
    completedAt: data.completed_at,
    kind: data.kind as DeletionKind,
    requestedAt: data.requested_at,
    status: data.status as DeletionStatus['status'],
  }
}

/**
 * Files a withdrawal or account-deletion request (WP-6d). The database withdraws the person's
 * grants in the same transaction, so publication stops at once, and refuses anything queued
 * before the request on any device; the hourly rights worker deletes the data. After an account
 * deletion every session of the account is revoked, so no other device can keep sending.
 */
export async function requestDeletion(
  client: GsipClient,
  kind: DeletionKind,
): Promise<DeletionOutcome> {
  const contributor = await existingContributor(client)
  if (!contributor) return 'no_account'
  const { error } = await client
    .from('deletion_requests')
    .insert({ contributor_id: contributor, kind })
  if (error) {
    if (error.code === '23505') return 'already_open'
    throw error
  }
  if (kind === 'delete_account') {
    forgetUid()
    // Global sign-out revokes the account's refresh tokens everywhere; this device's session is
    // removed even if the revocation call fails.
    await client.auth.signOut({ scope: 'global' })
  }
  return 'requested'
}

export type SignInLinkOutcome =
  'sent' | 'confirm_sent' | 'email_in_use' | 'failed'

/**
 * Sends an e-mail sign-in link. An anonymous account is upgraded in place (same user, so its
 * contributions stay withdrawable from any device); otherwise this signs in to the e-mail's
 * account. With `switchAccount`, the person chose to leave this device's anonymous account.
 */
export async function sendSignInLink(
  client: GsipClient,
  email: string,
  redirectTo: string,
  switchAccount = false,
): Promise<SignInLinkOutcome> {
  const { data } = await client.auth.getSession()
  if (data.session?.user.is_anonymous && !switchAccount) {
    const { error } = await client.auth.updateUser(
      { email },
      { emailRedirectTo: redirectTo },
    )
    if (!error) return 'confirm_sent'
    return error.code === 'email_exists' || /already/i.test(error.message)
      ? 'email_in_use'
      : 'failed'
  }
  const { error } = await client.auth.signInWithOtp({
    email,
    options: { emailRedirectTo: redirectTo },
  })
  return error ? 'failed' : 'sent'
}
