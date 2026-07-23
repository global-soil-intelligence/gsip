import { createClient } from 'npm:@supabase/supabase-js@2.110.8'
import {
  fetchJsonWithRetry,
  isConus,
  openMeteoUrls,
  parseElevation,
  parseRecentPrecipitation,
  parseSoilGridsResponse,
  parseSsurgoResponse,
  soilGridsUrl,
  ssurgoQuery,
  type PriorInput,
} from '../../../packages/schema/src/prior.ts'
import type { Database } from '../../../packages/schema/src/database.types.ts'

const corsHeaders = {
  'Access-Control-Allow-Headers':
    'authorization, content-type, x-client-info, apikey',
  'Access-Control-Allow-Origin': '*',
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

  const userClient = createClient<Database>(supabaseUrl, anonKey, {
    global: { headers: { Authorization: authorization } },
  })
  const serviceClient = createClient<Database>(supabaseUrl, serviceKey)
  const owned = await userClient
    .from('submissions')
    .select('id, geom_precise')
    .eq('id', body.submissionId)
    .maybeSingle()
  if (owned.error || !owned.data)
    return json({ error: 'Submission not found' }, 404)

  const claimed = await serviceClient.rpc('claim_prior_job_attempt', {
    p_submission_id: body.submissionId,
  })
  if (claimed.error) return json({ error: 'Prior job could not start' }, 503)
  if (typeof claimed.data !== 'number')
    return json({ error: 'Prior job retry budget exhausted' }, 429)
  const attempts = claimed.data

  try {
    const { latitude, longitude } = coordinates(owned.data.geom_precise)
    const soilBase = Deno.env.get('SOILGRIDS_BASE') ?? 'https://rest.isric.org'
    const meteoBase =
      Deno.env.get('OPEN_METEO_BASE') ?? 'https://api.open-meteo.com'
    const meteo = openMeteoUrls(meteoBase, latitude, longitude)
    const failures: string[] = []
    const priors: PriorInput[] = []
    let elevation: number | undefined
    let precipFlag: boolean | undefined

    try {
      const soil = await fetchJsonWithRetry(
        fetch,
        soilGridsUrl(soilBase, latitude, longitude),
      )
      priors.push(...parseSoilGridsResponse(soil))
    } catch {
      failures.push('soilgrids')
    }

    if (isConus(latitude, longitude)) {
      try {
        const ssurgo = await fetchJsonWithRetry(
          fetch,
          'https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest',
          {
            body: JSON.stringify({
              format: 'JSON+COLUMNNAME',
              query: ssurgoQuery(latitude, longitude),
            }),
            headers: { 'Content-Type': 'application/json' },
            method: 'POST',
          },
        )
        priors.push(...parseSsurgoResponse(ssurgo))
      } catch {
        failures.push('ssurgo')
      }
    }

    try {
      elevation = parseElevation(
        await fetchJsonWithRetry(fetch, meteo.elevation),
      )
    } catch {
      failures.push('elevation')
    }
    try {
      precipFlag = parseRecentPrecipitation(
        await fetchJsonWithRetry(fetch, meteo.weather),
      )
    } catch {
      failures.push('precipitation')
    }

    const rows = priors.map((prior) => ({
      ...prior,
      retrieved_at: new Date().toISOString(),
      submission_id: body.submissionId,
    }))
    if (rows.length) {
      const written = await serviceClient.from('priors').upsert(rows, {
        onConflict:
          'submission_id,source,property,depth_top_cm,depth_bottom_cm',
      })
      if (written.error) throw written.error
    }
    const enrichment: { elevation?: number; precip_flag?: boolean } = {}
    if (elevation !== undefined) enrichment.elevation = elevation
    if (precipFlag !== undefined) enrichment.precip_flag = precipFlag
    if (Object.keys(enrichment).length) {
      const enriched = await serviceClient
        .from('submissions')
        .update(enrichment)
        .eq('id', body.submissionId)
      if (enriched.error) throw enriched.error
    }
    const status = failures.length ? 'dead_letter' : 'completed'
    const finished = await serviceClient
      .from('prior_jobs')
      .update({
        attempts,
        completed_at: status === 'completed' ? new Date().toISOString() : null,
        last_error: failures.length
          ? `source_failure:${failures.join(',')}`
          : null,
        status,
        updated_at: new Date().toISOString(),
      })
      .eq('submission_id', body.submissionId)
    if (finished.error) throw finished.error
    return json(
      { failedSources: failures, priors: rows.length, status },
      failures.length ? 502 : 200,
    )
  } catch {
    await serviceClient
      .from('prior_jobs')
      .update({
        attempts,
        last_error: 'upstream_or_parse_failure',
        status: 'dead_letter',
        updated_at: new Date().toISOString(),
      })
      .eq('submission_id', body.submissionId)
    return json(
      { error: 'Prior enrichment failed', status: 'dead_letter' },
      502,
    )
  }
})
