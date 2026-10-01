import { readFile, stat } from 'node:fs/promises'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const dist = new URL('../apps/site-web/dist/', import.meta.url)
const initialFiles = ['index.html', 'favicon.svg', 'card-color-preview.png']

const html = await readFile(new URL('index.html', dist), 'utf8')
const assetMatches = [...html.matchAll(/(?:href|src)="\.\/([^"]+)"/g)].map(
  ([, file]) => file,
)
const files = [...new Set([...initialFiles, ...assetMatches])]
const distPath = fileURLToPath(dist)
let total = 0

for (const file of files) {
  try {
    const details = await stat(join(distPath, file))
    total += details.size
  } catch {
    // An optional file, such as the social preview before generation, does not
    // contribute to the browser's initial transfer.
  }
}

const budget = 700 * 1024
if (total > budget) {
  throw new Error(
    `Public homepage initial assets are ${total} bytes, exceeding ${budget}.`,
  )
}

console.log(`Public homepage initial assets: ${total} / ${budget} bytes`)
