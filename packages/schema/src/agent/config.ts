import { SERVER_NAME } from './envelope.ts'
import { publishableKeyFrom } from './keys.ts'

/**
 * The `gsip-public` function's settings, read from its environment. Kept here rather than in the
 * Deno adapter so it is tested: blank values count as unset, and the base URL that answers embed
 * always comes from configuration, never from a request.
 */
export type PublicFunctionConfig = {
  url: string
  publishableKey: string
  publicBaseUrl: string
  datasetRepo?: string
  rateLimitPerMinute?: number
  instanceRateLimitPerMinute?: number
}

type Env = (name: string) => string | undefined

function setting(env: Env, name: string): string | undefined {
  const value = env(name)?.trim()
  return value ? value : undefined
}

function positiveWhole(env: Env, name: string): number | undefined {
  const value = Number(setting(env, name))
  return Number.isInteger(value) && value > 0 ? value : undefined
}

/** Null when the project URL or a publishable key is missing: the function then reads nothing. */
export function publicFunctionConfig(env: Env): PublicFunctionConfig | null {
  const url = setting(env, 'SUPABASE_URL')?.replace(/\/+$/, '')
  const publishableKey = publishableKeyFrom(env)
  if (!url || !publishableKey) return null
  return {
    url,
    publishableKey,
    publicBaseUrl:
      setting(env, 'GSIP_PUBLIC_BASE_URL')?.replace(/\/+$/, '') ??
      `${url}/functions/v1/${SERVER_NAME}`,
    datasetRepo: setting(env, 'HF_DATASET_REPO'),
    rateLimitPerMinute: positiveWhole(env, 'GSIP_PUBLIC_RATE_LIMIT_PER_MINUTE'),
    instanceRateLimitPerMinute: positiveWhole(
      env,
      'GSIP_PUBLIC_INSTANCE_LIMIT_PER_MINUTE',
    ),
  }
}
