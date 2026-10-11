import { readdir, readFile } from 'node:fs/promises'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const roots = [
  new URL('../apps/capture-pwa/src/', import.meta.url),
  new URL('../apps/map-web/src/', import.meta.url),
  new URL('../apps/site-web/src/', import.meta.url),
  // Contributor-facing legal copy (WP-6d) follows the same rule.
  new URL('../docs/legal/', import.meta.url),
  // WP-AGENT-1: what agents read — the protocol and API text, the public function, llms.txt.
  new URL('../packages/schema/src/', import.meta.url),
  new URL('../supabase/functions/', import.meta.url),
  new URL('../apps/site-web/scripts/', import.meta.url),
]
const files = [new URL('../docs/AGENTS.md', import.meta.url)]
const prohibited = /soil[\s-]+test/i
const checked = /\.(?:ts|tsx|mjs|html|md)$/

async function check(path) {
  const content = await readFile(path, 'utf8')
  if (prohibited.test(content))
    throw new Error(`I5 language violation in ${path}`)
}

for (const root of roots) {
  const entries = await readdir(root, { recursive: true, withFileTypes: true })
  for (const entry of entries) {
    if (!entry.isFile() || !checked.test(entry.name)) continue
    await check(join(entry.parentPath, entry.name))
  }
}
for (const file of files) await check(fileURLToPath(file))
