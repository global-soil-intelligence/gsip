import { cp, mkdir, readFile, rm } from 'node:fs/promises'

// The deployed capture artifact stays closed independently of repository/environment variables.
const activation = JSON.parse(
  await readFile(
    new URL('../apps/capture-pwa/dist/gsip-activation.json', import.meta.url),
    'utf8',
  ),
)
if (
  JSON.stringify(Object.keys(activation).sort()) !==
    JSON.stringify(['capture_live', 'library_intake_live']) ||
  activation.capture_live !== false ||
  activation.library_intake_live !== false
)
  throw new Error(
    'Capture artifact activation must be closed before Pages packaging',
  )

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
