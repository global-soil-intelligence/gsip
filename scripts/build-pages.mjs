import { cp, mkdir, rm } from 'node:fs/promises'

const output = new URL('../_site/', import.meta.url)
await rm(output, { force: true, recursive: true })
await mkdir(output, { recursive: true })
await cp(new URL('../apps/site-web/dist/', import.meta.url), output, {
  recursive: true,
})
await cp(
  new URL('../apps/capture-pwa/dist/', import.meta.url),
  new URL('capture/', output),
  {
    recursive: true,
  },
)
await cp(
  new URL('../apps/map-web/dist/', import.meta.url),
  new URL('map/', output),
  {
    recursive: true,
  },
)
await cp(
  new URL('../output/pdf/', import.meta.url),
  new URL('reference-card/', output),
  { recursive: true },
)
