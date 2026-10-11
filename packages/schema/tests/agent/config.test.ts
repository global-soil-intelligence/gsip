import { describe, expect, it } from 'vitest'
import { publicFunctionConfig } from '../../src/agent/config'

const KEY = 'sb_publishable_Q2hlY2tz_0123456789'
const env =
  (values: Record<string, string>) =>
  (name: string): string | undefined =>
    values[name]

describe('the gsip-public function configuration', () => {
  it('reads nothing without a project URL and a publishable key', () => {
    expect(
      publicFunctionConfig(env({ SUPABASE_URL: 'https://p.supabase.co' })),
    ).toBeNull()
    expect(
      publicFunctionConfig(
        env({
          SUPABASE_URL: '  ',
          SUPABASE_PUBLISHABLE_KEYS: `{"default":"${KEY}"}`,
        }),
      ),
    ).toBeNull()
  })

  it('takes its public URL from configuration, treating a blank value as unset', () => {
    const hosted = env({
      SUPABASE_URL: 'https://p.supabase.co/',
      SUPABASE_PUBLISHABLE_KEYS: JSON.stringify({ default: KEY }),
      GSIP_PUBLIC_BASE_URL: ' ',
      HF_DATASET_REPO: '',
    })
    expect(publicFunctionConfig(hosted)).toEqual({
      url: 'https://p.supabase.co',
      publishableKey: KEY,
      publicBaseUrl: 'https://p.supabase.co/functions/v1/gsip-public',
      datasetRepo: undefined,
      rateLimitPerMinute: undefined,
      instanceRateLimitPerMinute: undefined,
    })
    expect(
      publicFunctionConfig(
        env({
          SUPABASE_URL: 'https://p.supabase.co',
          SUPABASE_ANON_KEY: KEY,
          GSIP_PUBLIC_BASE_URL: 'https://api.example.org/gsip/',
          HF_DATASET_REPO: 'global-soil-intelligence/gsip',
        }),
      ),
    ).toMatchObject({
      publicBaseUrl: 'https://api.example.org/gsip',
      datasetRepo: 'global-soil-intelligence/gsip',
    })
  })

  it('accepts only positive whole-number limits', () => {
    const limits = (value: string) =>
      publicFunctionConfig(
        env({
          SUPABASE_URL: 'https://p.supabase.co',
          SUPABASE_ANON_KEY: KEY,
          GSIP_PUBLIC_RATE_LIMIT_PER_MINUTE: value,
          GSIP_PUBLIC_INSTANCE_LIMIT_PER_MINUTE: value,
        }),
      )
    expect(limits('120')).toMatchObject({
      rateLimitPerMinute: 120,
      instanceRateLimitPerMinute: 120,
    })
    for (const bad of ['0', '-5', '2.5', 'many', '', ' ']) {
      expect(limits(bad), bad).toMatchObject({
        rateLimitPerMinute: undefined,
        instanceRateLimitPerMinute: undefined,
      })
    }
  })
})
