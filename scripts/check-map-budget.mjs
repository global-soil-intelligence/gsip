import { readdir, stat } from 'node:fs/promises'

const root = new URL('../apps/map-web/dist/', import.meta.url)
const limit = 5 * 1024 * 1024

async function bytes(directory) {
  let total = 0
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = new URL(entry.name, directory)
    if (entry.isDirectory())
      total += await bytes(new URL(`${entry.name}/`, directory))
    else if (!entry.name.endsWith('.map')) total += (await stat(path)).size
  }
  return total
}

const total = await bytes(root)
if (total > limit)
  throw new Error(
    `Map initial bundle ${total} bytes exceeds the ${limit} byte budget`,
  )
console.log(`map initial bundle: ${total} bytes / ${limit} byte budget`)
