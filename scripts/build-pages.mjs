import { cp, mkdir, rm, writeFile } from 'node:fs/promises'

const output = new URL('../_site/', import.meta.url)
await rm(output, { force: true, recursive: true })
await mkdir(output, { recursive: true })
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
await writeFile(
  new URL('index.html', output),
  '<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=./map/"><title>GSIP</title><a href="./map/">Open the GSIP map</a>\n',
)
