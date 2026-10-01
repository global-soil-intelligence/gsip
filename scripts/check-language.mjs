import { readdir, readFile } from 'node:fs/promises'
import { join } from 'node:path'

const roots = [
  new URL('../apps/capture-pwa/src/', import.meta.url),
  new URL('../apps/map-web/src/', import.meta.url),
]
const prohibited = /soil[\s-]+test/i

for (const root of roots) {
  const entries = await readdir(root, { recursive: true, withFileTypes: true })
  for (const entry of entries) {
    if (!entry.isFile() || !/\.(?:ts|tsx|html|md)$/.test(entry.name)) continue
    const path = join(entry.parentPath, entry.name)
    const content = await readFile(path, 'utf8')
    if (prohibited.test(content))
      throw new Error(`I5 language violation in ${path}`)
  }
}
