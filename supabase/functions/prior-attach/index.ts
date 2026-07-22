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

  const body = (await request.json()) as { submissionId?: unknown }
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

  await serviceClient.from('prior_jobs').upsert({
    attempts: 1,
    last_error: null,
    started_at: new Date().toISOString(),
    status: 'processing',
    submission_id: body.submissionId,
    updated_at: new Date().toISOString(),
  })

  try {
    const { latitude, longitude } = coordinates(owned.data.geom_precise)
    const soilBase = Deno.env.get('SOILGRIDS_BASE') ?? 'https://rest.isric.org'
    const meteoBase =
      Deno.env.get('OPEN_METEO_BASE') ?? 'https://api.open-meteo.com'
    const meteo = openMeteoUrls(meteoBase, latitude, longitude)
    const [soil, elevationResponse, weatherResponse] = await Promise.all([
      fetchJsonWithRetry(fetch, soilGridsUrl(soilBase, latitude, longitude)),
      fetchJsonWithRetry(fetch, meteo.elevation),
      fetchJsonWithRetry(fetch, meteo.weather),
    ])
    const priors: PriorInput[] = parseSoilGridsResponse(soil)

    if (isConus(latitude, longitude)) {
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
    }

    const rows = priors.map((prior) => ({
      ...prior,
      retrieved_at: new Date().toISOString(),
      submission_id: body.submissionId,
    }))
    const written = await serviceClient.from('priors').upsert(rows, {
      onConflict: 'submission_id,source,property,depth_top_cm,depth_bottom_cm',
    })
    if (written.error) throw written.error
    const enriched = await serviceClient
      .from('submissions')
      .update({
        elevation: parseElevation(elevationResponse),
        precip_flag: parseRecentPrecipitation(weatherResponse),
      })
      .eq('id', body.submissionId)
    if (enriched.error) throw enriched.error
    await serviceClient
      .from('prior_jobs')
      .update({
        attempts: 1,
        completed_at: new Date().toISOString(),
        last_error: null,
        status: 'completed',
        updated_at: new Date().toISOString(),
      })
      .eq('submission_id', body.submissionId)
    return json({ priors: rows.length, status: 'completed' })
  } catch {
    await serviceClient
      .from('prior_jobs')
      .update({
        attempts: 1,
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
