// @vitest-environment node
import { mkdtempSync, rmSync, symlinkSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import {
  assertCollectionOutput,
  assertFixtureOutput,
  assertReviewedSource,
  browserKeyAllowed,
  collectionBuild,
} from '../../../scripts/collection-build-contract.mts'
const folders: string[] = []
afterEach(() => {
  for (const folder of folders.splice(0))
    rmSync(folder, { recursive: true, force: true })
})
function fixture() {
  const folder = mkdtempSync(join(tmpdir(), 'gsip-collection-fixture-'))
  folders.push(folder)
  return {
    VITE_COLLECTION_MODE: 'invited_private',
    VITE_CAPTURE_LIVE: 'true',
    VITE_LIBRARY_INTAKE_LIVE: 'true',
    VITE_COLLECTION_PROJECT_REF: 'fixture',
    VITE_SUPABASE_URL: 'https://supabase.test',
    VITE_SUPABASE_PUBLISHABLE_KEY: 'fixture',
    VITE_COLLECTION_SITE_ORIGIN: 'http://127.0.0.1:4173',
    GITHUB_SHA: 'f'.repeat(40),
    VITE_COLLECTION_FIXTURE_OUTPUT: join(folder, 'pilot'),
  }
}
describe('isolated invited artifact contract', () => {
  it('preserves ordinary output and rejects pilot mode in native/default builds', () => {
    expect(collectionBuild('app', {}).receipt).toBeUndefined()
    expect(collectionBuild('production', {}).output).toBeUndefined()
    for (const mode of ['app', 'production', 'unknown'])
      expect(() => collectionBuild(mode, fixture())).toThrow()
  })
  it('binds the fixture to reserved endpoints and isolated output', () => {
    const env = fixture()
    const result = collectionBuild('invited-pilot-fixture', env)
    expect(result.receipt?.version).toBe('gsip-invited-browser-fixture-v1')
    expect(result.output).toBe(env.VITE_COLLECTION_FIXTURE_OUTPUT)
    expect(() =>
      assertCollectionOutput(result, 'dist', process.cwd()),
    ).toThrow()
  })
  it.each([
    'VITE_CAPTURE_LIVE',
    'VITE_LIBRARY_INTAKE_LIVE',
    'VITE_COLLECTION_PROJECT_REF',
    'VITE_SUPABASE_URL',
    'VITE_COLLECTION_SITE_ORIGIN',
    'GITHUB_SHA',
    'VITE_SUPABASE_PUBLISHABLE_KEY',
  ])('refuses missing, mismatched or secret fixture input %s', (key) => {
    const env = fixture()
    Object.assign(env, { [key]: 'unexpected' })
    expect(() => collectionBuild('invited-pilot-fixture', env)).toThrow()
  })
  it('refuses existing and dangling output symlinks', () => {
    const env = fixture()
    symlinkSync(process.cwd(), env.VITE_COLLECTION_FIXTURE_OUTPUT)
    expect(() => collectionBuild('invited-pilot-fixture', env)).toThrow()
    const dangling = fixture()
    symlinkSync(
      join(dangling.VITE_COLLECTION_FIXTURE_OUTPUT, 'absent'),
      dangling.VITE_COLLECTION_FIXTURE_OUTPUT,
    )
    expect(() =>
      assertFixtureOutput(dangling.VITE_COLLECTION_FIXTURE_OUTPUT),
    ).toThrow()
    expect(() => assertFixtureOutput(join(tmpdir(), 'not-isolated'))).toThrow()
  })
  it('refuses arbitrary reviewed source claims without compiling', () => {
    expect(() => assertReviewedSource('f'.repeat(40))).toThrow()
  })
  it('never permits a service-role or opaque key', () => {
    for (const role of ['service_role', 'authenticated', 'anon']) {
      const encoded = Buffer.from(JSON.stringify({ role })).toString(
        'base64url',
      )
      expect(browserKeyAllowed(`header.${encoded}.synthetic`)).toBe(
        role === 'anon',
      )
    }
    expect(browserKeyAllowed('fixture')).toBe(false)
    expect(browserKeyAllowed('sb_' + 'secret_' + 'x'.repeat(32))).toBe(false)
    expect(browserKeyAllowed('sb_' + 'publishable_' + 'x'.repeat(32))).toBe(
      true,
    )
  })
})
