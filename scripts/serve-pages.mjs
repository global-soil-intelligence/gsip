import { createReadStream } from 'node:fs'
import { stat } from 'node:fs/promises'
import { createServer } from 'node:http'
import { extname, join, normalize, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const siteRoot = fileURLToPath(new URL('../_site/', import.meta.url))
const resolvedSiteRoot = resolve(siteRoot)
const mimeTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.jpg': 'image/jpeg',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.pdf': 'application/pdf',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
  '.webmanifest': 'application/manifest+json; charset=utf-8',
  '.xml': 'application/xml; charset=utf-8',
}

createServer(async (request, response) => {
  try {
    const pathname = decodeURIComponent(
      new URL(request.url ?? '/', 'http://127.0.0.1').pathname,
    )
    if (!pathname.startsWith('/gsip/')) {
      response.writeHead(404).end('Not found')
      return
    }

    const relativePath = normalize(pathname.slice('/gsip/'.length))
    let filePath = resolve(resolvedSiteRoot, relativePath)
    if (
      filePath !== resolvedSiteRoot &&
      !filePath.startsWith(`${resolvedSiteRoot}${sep}`)
    ) {
      response.writeHead(403).end('Forbidden')
      return
    }

    const details = await stat(filePath)
    if (details.isDirectory()) filePath = join(filePath, 'index.html')
    response.setHeader(
      'content-type',
      mimeTypes[extname(filePath)] ?? 'application/octet-stream',
    )
    createReadStream(filePath).pipe(response)
  } catch {
    response.writeHead(404).end('Not found')
  }
}).listen(4173, '127.0.0.1')
