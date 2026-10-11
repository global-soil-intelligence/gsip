// @vitest-environment node
// Runs the deploy gate as Pages does, against a local server, so the command itself (argument
// handling, the PMTiles reader and the exit code) is covered, not only its checking logic.
import { execFile } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { createServer } from 'node:http'
import process from 'node:process'
import { fileURLToPath, URL } from 'node:url'
import { promisify } from 'node:util'
import { describe, expect, it } from 'vitest'

const script = fileURLToPath(
  new URL('../scripts/check-prior-tiles.mjs', import.meta.url),
)
const { version } = JSON.parse(
  readFileSync(
    new URL(
      '../../../packages/schema/src/palettes/soilgrids.json',
      import.meta.url,
    ),
    'utf8',
  ),
)

async function run(env) {
  return promisify(execFile)(process.execPath, [script], {
    env: { ...process.env, ...env },
  }).then(
    ({ stdout }) => ({ code: 0, stderr: '', stdout }),
    (error) => ({
      code: error.code,
      stderr: error.stderr,
      stdout: error.stdout,
    }),
  )
}

describe('prior tiles deploy gate command', () => {
  it('passes without a tiles base: the map then uses ISRIC WMS and legends', async () => {
    const result = await run({ VITE_PRIOR_TILES_BASE: '' })
    expect(result.code).toBe(0)
    expect(result.stdout).toMatch(/ISRIC WMS/)
  })

  it('blocks the deploy when the published archives cannot be read', async () => {
    const requested = []
    const server = createServer((request, response) => {
      requested.push(request.url ?? '')
      response.writeHead(404).end()
    })
    await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve))
    try {
      const { port } = server.address()
      const result = await run({
        VITE_PRIOR_TILES_BASE: `http://127.0.0.1:${port}/t/`,
      })
      expect(result.code).toBe(1)
      expect(result.stderr).toMatch(/unreadable/)
      expect(requested).toContain(`/t/${version}/soc.pmtiles`)
    } finally {
      server.close()
    }
  })
})
