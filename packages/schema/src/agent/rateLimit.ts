/**
 * Best-effort, per-client token bucket (BUILD_ORDER WP-AGENT-1). It lives in one function
 * instance's memory, so it smooths bursts rather than enforcing a global quota. Client keys
 * (IP addresses) are held only in memory, briefly, and never logged.
 */
export type RateLimiter = (client: string) => {
  allowed: boolean
  retryAfterSeconds: number
}

export function createRateLimiter(options: {
  perMinute: number
  now?: () => number
  maxClients?: number
}): RateLimiter {
  const capacity = Math.max(1, Math.floor(options.perMinute))
  const refillPerMs = capacity / 60_000
  const now = options.now ?? Date.now
  const maxClients = options.maxClients ?? 10_000
  const buckets = new Map<string, { tokens: number; updated: number }>()

  return (client) => {
    const at = now()
    let bucket = buckets.get(client)
    if (bucket) {
      bucket.tokens = Math.min(
        capacity,
        bucket.tokens + (at - bucket.updated) * refillPerMs,
      )
      bucket.updated = at
      // Map order is insertion order: re-inserting keeps recently seen clients at the end.
      buckets.delete(client)
    } else {
      bucket = { tokens: capacity, updated: at }
      while (buckets.size >= maxClients) {
        const oldest = buckets.keys().next().value
        if (oldest === undefined) break
        buckets.delete(oldest)
      }
    }
    buckets.set(client, bucket)
    if (bucket.tokens >= 1) {
      bucket.tokens -= 1
      return { allowed: true, retryAfterSeconds: 0 }
    }
    return {
      allowed: false,
      retryAfterSeconds: Math.max(
        1,
        Math.ceil((1 - bucket.tokens) / refillPerMs / 1000),
      ),
    }
  }
}

/** Longer than any IPv6 address; a forged header cannot grow the limiter's memory beyond it. */
const MAX_KEY_LENGTH = 64

/**
 * The caller's address as the platform reports it; never stored beyond the limiter's memory.
 * `CF-Connecting-IP` is set by the edge network in front of Supabase and preferred; the first
 * `X-Forwarded-For` entry is a fallback a caller may be able to forge, which the per-instance
 * ceiling in handler.ts bounds.
 */
export function clientKey(request: Request): string {
  const edge = request.headers.get('cf-connecting-ip')?.trim()
  const forwarded = request.headers
    .get('x-forwarded-for')
    ?.split(',')[0]
    ?.trim()
  return (edge || forwarded || 'unknown').slice(0, MAX_KEY_LENGTH)
}
