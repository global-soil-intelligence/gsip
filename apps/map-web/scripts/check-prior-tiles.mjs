// WP-6c deploy gate. The map loads `${VITE_PRIOR_TILES_BASE}/<palette version>/<layer>.pmtiles`
// and draws its legends from the same palette file. Before Pages deploys, every archive must exist
// and carry that palette version in its metadata, so a legend can never disagree with its tiles.
// With no tiles base the map shows ISRIC's WMS with ISRIC's own legend: nothing to check.
import { readFile } from 'node:fs/promises'
import process from 'node:process'
import { pathToFileURL } from 'node:url'
import { PMTiles } from 'pmtiles'

const PALETTE = new URL(
  '../../../packages/schema/src/palettes/soilgrids.json',
  import.meta.url,
)

/**
 * @param {{ base: string, open: (url: string) => { getMetadata(): Promise<unknown> },
 *   palette: { layers: { id: string }[], version: string } }} options
 * @returns {Promise<string[]>} one problem per archive that the map must not use
 */
export async function checkPriorTiles({ base, open, palette }) {
  const root = base.trim().replace(/\/+$/, '')
  const problems = []
  for (const layer of palette.layers) {
    const url = `${root}/${palette.version}/${layer.id}.pmtiles`
    let metadata
    try {
      metadata = await open(url).getMetadata()
    } catch (error) {
      problems.push(
        `${url}: unreadable (${error instanceof Error ? error.message : error})`,
      )
      continue
    }
    const stamped =
      typeof metadata === 'object' && metadata !== null ? metadata : {}
    if (stamped.gsip_palette_version !== palette.version)
      problems.push(
        `${url}: coloured with palette ${stamped.gsip_palette_version ?? 'unknown'}, but the legends use ${palette.version}`,
      )
    else if (stamped.gsip_layer !== layer.id)
      problems.push(`${url}: holds layer ${stamped.gsip_layer ?? 'unknown'}`)
  }
  return problems
}

async function main() {
  const base = process.env.VITE_PRIOR_TILES_BASE?.trim()
  if (!base) {
    console.log(
      'VITE_PRIOR_TILES_BASE is unset: the map uses ISRIC WMS tiles with ISRIC legends.',
    )
    return
  }
  const palette = JSON.parse(await readFile(PALETTE, 'utf8'))
  const problems = await checkPriorTiles({
    base,
    open: (url) => new PMTiles(url),
    palette,
  })
  if (problems.length) {
    for (const problem of problems) console.error(problem)
    console.error(
      'Rebuild with `uv run python -m pipeline.build_prior_tiles` and publish the whole version directory.',
    )
    process.exitCode = 1
    return
  }
  console.log(
    `prior tiles: ${palette.layers.length} archives match palette ${palette.version}`,
  )
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href)
  await main()
