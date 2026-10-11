import { createClient } from 'npm:@supabase/supabase-js@2.110.8'
import { fetchJsonWithRetry } from '../../../packages/schema/src/prior.ts'
import {
  type BeginResult,
  DEFAULT_PRIOR_JOB_CONFIG,
  isServiceRequest,
  PRIOR_OUTCOME_HTTP_STATUS,
  type PriorJobDeps,
  runPriorJob,
  type StaticSource,
} from '../../../packages/schema/src/priorJob.ts'
import type {
  Database,
  Json,
} from '../../../packages/schema/src/database.types.ts'

// WP-6c: a thin adapter. All decisions (cell-centre lookups, cache, atomic claim-and-spend,
// "no prior" as a terminal state) live in packages/schema/src/priorJob.ts and the database
// function begin_prior_attempt(), both of which are tested.

const corsHeaders = {
  'Access-Control-Allow-Headers':
    'authorization, content-type, x-client-info, apikey',
  'Access-Control-Allow-Origin': '*',
}

function json(
  body: unknown,
  status = 200,
  headers: Record<string, string> = {},
): Response {
  return new Response(JSON.stringify(body), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json', ...headers },
    status,
  })
}

function coordinates(geometry: unknown): {
  latitude: number
  longitude: number
} {
  if (
    typeof geometry !== 'object' ||
    geometry === null ||
    !('coordinates' in geometry) ||
    !Array.isArray(geometry.coordinates) ||
    geometry.coordinates.length < 2
  )
    throw new Error('Submission geometry is unavailable')
  const [longitude, latitude] = geometry.coordinates.map(Number)
  if (
    !Number.isFinite(latitude) ||
    !Number.isFinite(longitude) ||
    Math.abs(latitude) > 90 ||
    Math.abs(longitude) > 180
  )
    throw new Error('Submission geometry is invalid')
  return { latitude, longitude }
}

Deno.serve(async (request: Request) => {
  if (request.method === 'OPTIONS')
    return new Response('ok', { headers: corsHeaders })
  if (request.method !== 'POST')
    return json({ error: 'Method not allowed' }, 405)

  const supabaseUrl = Deno.env.get('SUPABASE_URL')
  const anonKey = Deno.env.get('SUPABASE_ANON_KEY')
  const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')
  if (!supabaseUrl || !anonKey || !serviceKey)
    return json({ error: 'Service unavailable' }, 503)
  const authorization = request.headers.get('Authorization')
  if (!authorization) return json({ error: 'Authentication required' }, 401)

  let body: { submissionId?: unknown }
  try {
    body = (await request.json()) as { submissionId?: unknown }
  } catch {
    return json({ error: 'Request body must be valid JSON' }, 400)
  }
  if (typeof body.submissionId !== 'string')
    return json({ error: 'submissionId is required' }, 400)
  const submissionId = body.submissionId

  // Service mode (retries) only for the exact service-role key; never an unverified claim.
  const ownerRequest = !isServiceRequest(authorization, serviceKey)
  const serviceClient = createClient<Database>(supabaseUrl, serviceKey)
  // Contributors read through RLS (PostgREST verifies their JWT), so they can only reach their
  // own submission; this read is what stops anyone starting someone else's job.
  const reader = ownerRequest
    ? createClient<Database>(supabaseUrl, anonKey, {
        global: { headers: { Authorization: authorization } },
      })
    : serviceClient
  const found = await reader
    .from('submissions')
    .select('id, geom_precise, captured_at')
    .eq('id', submissionId)
    .maybeSingle()
  if (found.error || !found.data)
    return json({ error: 'Submission not found' }, 404)

  let location: { latitude: number; longitude: number }
  try {
    location = coordinates(found.data.geom_precise)
  } catch {
    // This job can never succeed: end it so it cannot hold the drain's queue head forever.
    await serviceClient.rpc('fail_prior_job', {
      p_reason: 'invalid_geometry',
      p_submission_id: submissionId,
    })
    return json({ error: 'Submission geometry is unavailable' }, 422)
  }

  const deps: PriorJobDeps = {
    begin: async (id, owner, costs): Promise<BeginResult> => {
      const begun = await serviceClient.rpc('begin_prior_attempt', {
        p_costs: costs as Json,
        p_owner_request: owner,
        p_submission_id: id,
      })
      if (begun.error) throw begun.error
      const row = begun.data?.[0]
      if (row?.outcome === 'claimed' && typeof row.attempts === 'number')
        return { attempts: row.attempts, outcome: 'claimed' }
      if (row?.outcome === 'deferred')
        return {
          outcome: 'deferred',
          retryAfterSeconds: row.retry_after_seconds ?? 12,
        }
      return { outcome: 'not_claimable' }
    },
    // One call per token: the job retry is the retry (ISRIC counts retries too).
    fetchJson: (url, init) =>
      fetchJsonWithRetry(fetch, url, init, { attempts: 1 }),
    finish: async (update) => {
      const finished = await serviceClient
        .from('prior_jobs')
        .update({
          attempts: update.attempts,
          completed_at:
            update.status === 'completed' ? new Date().toISOString() : null,
          empty_sources: update.emptySources,
          last_error: update.lastError,
          status: update.status,
          updated_at: new Date().toISOString(),
        })
        .eq('submission_id', submissionId)
      if (finished.error) throw finished.error
    },
    now: () => new Date(),
    readCache: async (cell) => {
      const rows = await serviceClient
        .from('prior_cell_cache')
        .select('source, payload, retrieved_at')
        .eq('h3_r9', cell)
      if (rows.error) throw rows.error
      return Object.fromEntries(
        (rows.data ?? []).map((row) => [
          row.source as StaticSource,
          { payload: row.payload, retrievedAt: row.retrieved_at },
        ]),
      )
    },
    writeCache: async (cell, source, payload) => {
      const written = await serviceClient.from('prior_cell_cache').upsert(
        {
          h3_r9: cell,
          payload: payload as Json,
          retrieved_at: new Date().toISOString(),
          source,
        },
        { onConflict: 'h3_r9,source' },
      )
      if (written.error) throw written.error
    },
    writeEnrichment: async (enrichment) => {
      const enriched = await serviceClient
        .from('submissions')
        .update(enrichment)
        .eq('id', submissionId)
      if (enriched.error) throw enriched.error
    },
    writePriors: async (rows) => {
      const retrievedAt = new Date().toISOString()
      const written = await serviceClient.from('priors').upsert(
        rows.map((row) => ({
          ...row,
          retrieved_at: retrievedAt,
          submission_id: submissionId,
        })),
        {
          onConflict:
            'submission_id,source,property,depth_top_cm,depth_bottom_cm',
        },
      )
      if (written.error) throw written.error
    },
  }

  try {
    const outcome = await runPriorJob(
      deps,
      {
        capturedAt: found.data.captured_at,
        id: submissionId,
        latitude: location.latitude,
        longitude: location.longitude,
      },
      ownerRequest,
      {
        ...DEFAULT_PRIOR_JOB_CONFIG,
        archiveBase:
          Deno.env.get('OPEN_METEO_ARCHIVE_BASE') ??
          DEFAULT_PRIOR_JOB_CONFIG.archiveBase,
        forecastBase:
          Deno.env.get('OPEN_METEO_BASE') ??
          DEFAULT_PRIOR_JOB_CONFIG.forecastBase,
        soilBase:
          Deno.env.get('SOILGRIDS_BASE') ?? DEFAULT_PRIOR_JOB_CONFIG.soilBase,
      },
    )
    // Outcome codes only: upstream errors and coordinates never leave the server.
    return json(
      {
        emptySources: outcome.emptySources,
        failedSources: outcome.failedSources,
        priors: outcome.priors,
        status: outcome.status,
      },
      PRIOR_OUTCOME_HTTP_STATUS[outcome.status],
      outcome.retryAfterSeconds === null
        ? {}
        : { 'Retry-After': String(outcome.retryAfterSeconds) },
    )
  } catch {
    return json({ error: 'Prior job could not start' }, 503)
  }
})
