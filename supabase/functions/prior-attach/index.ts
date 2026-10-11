import { createClient } from 'npm:@supabase/supabase-js@2.110.8'
import { fetchJsonWithRetry } from '../../../packages/schema/src/prior.ts'
import {
  DEFAULT_PRIOR_JOB_CONFIG,
  type PriorJobDeps,
  type PriorJobOutcome,
  runPriorJob,
  type StaticSource,
} from '../../../packages/schema/src/priorJob.ts'
import type {
  Database,
  Json,
} from '../../../packages/schema/src/database.types.ts'

// WP-6c: a thin adapter. All decisions (cell-centre lookups, cache, token buckets, claim rules,
// "no prior" as a terminal state) live in packages/schema/src/priorJob.ts, which is unit-tested.

const corsHeaders = {
  'Access-Control-Allow-Headers':
    'authorization, content-type, x-client-info, apikey',
  'Access-Control-Allow-Origin': '*',
}

const OUTCOME_STATUS: Record<PriorJobOutcome['status'], number> = {
  completed: 200,
  dead_letter: 502,
  deferred: 202,
  not_claimable: 409,
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
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
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude))
    throw new Error('Submission geometry is invalid')
  return { latitude, longitude }
}

/**
 * The gateway has already verified the JWT signature (verify_jwt is on for this function), so
 * its role claim decides the mode: the service worker may retry; a contributor may only start
 * their own unstarted job.
 */
function isServiceRole(token: string): boolean {
  const [, payload] = token.split('.')
  if (!payload) return false
  try {
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const claims = JSON.parse(atob(normalized)) as { role?: unknown }
    return claims.role === 'service_role'
  } catch {
    return false
  }
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

  const ownerRequest = !isServiceRole(authorization.replace(/^Bearer\s+/i, ''))
  const serviceClient = createClient<Database>(supabaseUrl, serviceKey)
  // Contributors read through RLS, so they can only reach their own submission.
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
    return json({ error: 'Submission geometry is unavailable' }, 422)
  }

  const deps: PriorJobDeps = {
    claim: async (id, owner) => {
      const claimed = await serviceClient.rpc('claim_prior_job_attempt', {
        p_owner_request: owner,
        p_submission_id: id,
      })
      if (claimed.error) throw claimed.error
      return typeof claimed.data === 'number' ? claimed.data : null
    },
    fetchJson: (url, init, attempts) =>
      fetchJsonWithRetry(fetch, url, init, { attempts }),
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
    takeToken: async (bucket, cost) => {
      const taken = await serviceClient.rpc('take_upstream_token', {
        p_cost: cost,
        p_source: bucket,
      })
      if (taken.error) throw taken.error
      return taken.data === true
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
      OUTCOME_STATUS[outcome.status],
    )
  } catch {
    return json({ error: 'Prior job could not start' }, 503)
  }
})
