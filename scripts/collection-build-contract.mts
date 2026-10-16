import { lstatSync, realpathSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { tmpdir } from 'node:os'
import { dirname, isAbsolute, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const repository = fileURLToPath(new URL('../', import.meta.url))
export const pilotProject = 'toxldjgwkxtneoqsazym'
export const pilotOrigin = 'https://globalsoilintelligence.com'
export function browserKeyAllowed(value: string): boolean {
  if (/^sb_publishable_[A-Za-z0-9_-]{16,}$/.test(value)) return true
  if (value.length > 8192 || value.split('.').length !== 3) return false
  try {
    return (
      JSON.parse(Buffer.from(value.split('.')[1], 'base64url').toString())
        .role === 'anon'
    )
  } catch {
    return false
  }
}

export function assertReviewedSource(commit: string): void {
  const actual = execFileSync('git', ['rev-parse', 'HEAD'], {
    cwd: repository,
    encoding: 'utf8',
  }).trim()
  const dirty = execFileSync(
    'git',
    ['status', '--porcelain', '--untracked-files=all'],
    { cwd: repository, encoding: 'utf8' },
  ).trim()
  if (!/^[0-9a-f]{40}$/.test(commit) || actual !== commit || dirty)
    throw new Error('Reviewed source must be exact and clean')
}

type Build = {
  receipt?: Record<string, unknown>
  output?: string
  fixture: boolean
}

export function collectionBuild(
  mode: string,
  env: Record<string, string | undefined>,
): Build {
  const requested = env.VITE_COLLECTION_MODE ?? 'closed'
  const pilot = mode === 'invited-pilot' || mode === 'invited-pilot-fixture'
  if (!pilot) {
    if (requested !== 'closed' && requested !== '')
      throw new Error('Explicit browser collection build required')
    return { fixture: false }
  }
  const fixture = mode === 'invited-pilot-fixture'
  const project = fixture ? 'fixture' : pilotProject
  const api = fixture
    ? 'https://supabase.test'
    : `https://${pilotProject}.supabase.co`
  const origin = fixture ? 'http://127.0.0.1:4173' : pilotOrigin
  if (
    requested !== 'invited_private' ||
    env.VITE_CAPTURE_LIVE !== 'true' ||
    env.VITE_LIBRARY_INTAKE_LIVE !== 'true' ||
    env.VITE_COLLECTION_PROJECT_REF !== project ||
    env.VITE_SUPABASE_URL !== api ||
    env.VITE_COLLECTION_SITE_ORIGIN !== origin ||
    !/^[0-9a-f]{40}$/.test(env.GITHUB_SHA ?? '')
  )
    throw new Error('Collection mode, gates, target or source mismatch')
  const output = fixture
    ? env.VITE_COLLECTION_FIXTURE_OUTPUT
    : resolve(repository, '_collection_capture')
  if (!output) throw new Error('Isolated fixture output required')
  if (fixture) {
    if (env.VITE_SUPABASE_PUBLISHABLE_KEY !== 'fixture')
      throw new Error('Synthetic browser configuration required')
    assertFixtureOutput(output)
  } else {
    if (!browserKeyAllowed(env.VITE_SUPABASE_PUBLISHABLE_KEY ?? ''))
      throw new Error('Browser-safe publishable configuration required')
    assertReviewedSource(env.GITHUB_SHA!)
    assertOutputEntry(output, true)
  }
  return {
    fixture,
    output,
    receipt: {
      version: fixture
        ? 'gsip-invited-browser-fixture-v1'
        : 'gsip-invited-browser-v1',
      mode: 'invited_private',
      capture_live: true,
      library_intake_live: true,
      publication_held: true,
      source_commit: env.GITHUB_SHA,
      target: { project_ref: project, supabase_url: api, site_origin: origin },
    },
  }
}

function assertOutputEntry(output: string, fresh: boolean): void {
  try {
    const entry = lstatSync(output)
    if (fresh || entry.isSymbolicLink() || !entry.isDirectory())
      throw new Error('Fresh isolated collection output required')
  } catch (error) {
    if (!(error instanceof Error && 'code' in error && error.code === 'ENOENT'))
      throw error
  }
}

export function assertFixtureOutput(output: string): void {
  if (!isAbsolute(output))
    throw new Error('Fixture output must be absolute and temporary')
  assertOutputEntry(output, false)
  const parent = realpathSync(dirname(output))
  const inside = relative(realpathSync(tmpdir()), parent)
  if (!inside || inside.startsWith('..') || isAbsolute(inside))
    throw new Error('Fixture output must stay temporary')
}

export function assertCollectionOutput(
  build: Build,
  output: string,
  root: string,
): void {
  if (!build.receipt) return
  const actual = resolve(root, output)
  if (actual !== resolve(build.output!))
    throw new Error('Collection output override refused')
  assertOutputEntry(actual, false)
  if (build.fixture) assertFixtureOutput(actual)
  else assertReviewedSource(build.receipt.source_commit as string)
}
