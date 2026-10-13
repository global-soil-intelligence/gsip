import { describe, expect, it } from 'vitest'
import { createPublicHandler } from '../../src/agent/handler'
import { LEGACY_VERSIONS, MODERN_VERSIONS } from '../../src/agent/mcp'
import {
  BURLINGTON_R4,
  BURLINGTON_R8,
  BURLINGTON_R9,
  fakeReader,
  PUBLISHED,
} from './fixtures'

const ENDPOINT = 'https://project.supabase.co/functions/v1/gsip-public/mcp'
const MODERN = MODERN_VERSIONS[0]

const handle = createPublicHandler({
  reader: fakeReader(PUBLISHED),
  datasetRepo: 'global-soil-intelligence/gsip',
  rateLimitPerMinute: 10_000,
})

// The parsed body stays untyped (JSON.parse) so assertions can read any field.
async function post(body: unknown, headers: Record<string, string> = {}) {
  const response = await handle(
    new Request(ENDPOINT, {
      method: 'POST',
      headers: {
        Accept: 'application/json, text/event-stream',
        'Content-Type': 'application/json',
        ...headers,
      },
      body: typeof body === 'string' ? body : JSON.stringify(body),
    }),
  )
  const text = await response.text()
  return {
    status: response.status,
    json: text ? JSON.parse(text) : null,
    headers: response.headers,
  }
}

/** A 2026-07-28 request: version in `_meta`, mirrored into the required headers. */
function modern(
  id: number,
  method: string,
  params: Record<string, unknown> = {},
  version: string = MODERN,
) {
  const headers: Record<string, string> = {
    'MCP-Protocol-Version': version,
    'Mcp-Method': method,
  }
  if (method === 'tools/call') headers['Mcp-Name'] = String(params.name)
  return post(
    {
      jsonrpc: '2.0',
      id,
      method,
      params: {
        ...params,
        _meta: {
          'io.modelcontextprotocol/protocolVersion': version,
          'io.modelcontextprotocol/clientInfo': {
            name: 'test-client',
            version: '1.0.0',
          },
          'io.modelcontextprotocol/clientCapabilities': {},
        },
      },
    },
    headers,
  )
}

describe('MCP, earlier revisions (initialize handshake)', () => {
  it('negotiates a supported protocol version on initialize', async () => {
    const { status, json } = await post({
      jsonrpc: '2.0',
      id: 1,
      method: 'initialize',
      params: {
        protocolVersion: '2025-06-18',
        capabilities: {},
        clientInfo: { name: 'test-client', version: '1.0.0' },
      },
    })
    expect(status).toBe(200)
    expect(json.result.protocolVersion).toBe('2025-06-18')
    expect(json.result.capabilities).toEqual({ tools: { listChanged: false } })
    expect(json.result.serverInfo.name).toBe('gsip-public')
    expect(json.result.instructions).toMatch(/untrusted/)

    const unknown = await post({
      jsonrpc: '2.0',
      id: 2,
      method: 'initialize',
      params: { protocolVersion: '1999-01-01', capabilities: {} },
    })
    expect(unknown.json.result.protocolVersion).toBe(LEGACY_VERSIONS[0])
  })

  it('accepts notifications with 202 and no body, and never mints a session', async () => {
    const response = await post({
      jsonrpc: '2.0',
      method: 'notifications/initialized',
    })
    expect(response.status).toBe(202)
    expect(response.json).toBeNull()
    expect(response.headers.get('mcp-session-id')).toBeNull()
  })

  it('lists exactly four read-only tools with JSON Schemas', async () => {
    const { json } = await post(
      { jsonrpc: '2.0', id: 3, method: 'tools/list' },
      { 'MCP-Protocol-Version': '2025-06-18' },
    )
    const tools = json.result.tools
    expect(tools.map((tool: { name: string }) => tool.name)).toEqual([
      'get_protocol',
      'get_cell',
      'list_cells',
      'get_release',
    ])
    for (const tool of tools) {
      expect(tool.inputSchema.type).toBe('object')
      expect(tool.inputSchema.additionalProperties).toBe(false)
      expect(tool.outputSchema.type).toBe('object')
      expect(tool.annotations).toMatchObject({
        readOnlyHint: true,
        destructiveHint: false,
      })
    }
    expect(tools[1].inputSchema.required).toEqual(['cell'])
  })

  it('returns structured content with a text copy, carrying licence and citation', async () => {
    const { json } = await post({
      jsonrpc: '2.0',
      id: 4,
      method: 'tools/call',
      params: { name: 'get_cell', arguments: { cell: BURLINGTON_R8 } },
    })
    const result = json.result
    expect(result.isError).toBe(false)
    expect(result.structuredContent.data.status).toBe('published')
    expect(result.structuredContent.license.data).toBe('ODbL-1.0')
    expect(result.structuredContent.citation.text).toContain(
      'Global Soil Intelligence',
    )
    expect(JSON.parse(result.content[0].text)).toEqual(result.structuredContent)
    expect(result.resultType).toBeUndefined()
  })

  it('reports bad arguments as tool errors the model can correct', async () => {
    const bad = await post({
      jsonrpc: '2.0',
      id: 5,
      method: 'tools/call',
      params: { name: 'get_cell', arguments: { cell: 'somewhere nice' } },
    })
    expect(bad.json.result.isError).toBe(true)
    expect(bad.json.result.content[0].text).toMatch(/H3 cell/)
    const tooFine = await post({
      jsonrpc: '2.0',
      id: 5,
      method: 'tools/call',
      params: { name: 'get_cell', arguments: { cell: BURLINGTON_R9 } },
    })
    expect(tooFine.json.result.isError).toBe(true)
    expect(tooFine.json.result.content[0].text).toMatch(/resolution-8 parent/)
    const extra = await post({
      jsonrpc: '2.0',
      id: 6,
      method: 'tools/call',
      params: {
        name: 'list_cells',
        arguments: { within: BURLINGTON_R4, sql: 'drop' },
      },
    })
    expect(extra.json.result.isError).toBe(true)
  })

  it('answers protocol errors as JSON-RPC errors', async () => {
    const unknownTool = await post({
      jsonrpc: '2.0',
      id: 7,
      method: 'tools/call',
      params: { name: 'delete_everything', arguments: {} },
    })
    expect(unknownTool.json.error.code).toBe(-32602)
    const unknownMethod = await post({
      jsonrpc: '2.0',
      id: 8,
      method: 'resources/list',
    })
    expect(unknownMethod.json.error.code).toBe(-32601)
    const parse = await post('{"jsonrpc": "2.0", "id": 9, "method": ')
    expect(parse.status).toBe(400)
    expect(parse.json.error.code).toBe(-32700)
    const batch = await post([{ jsonrpc: '2.0', id: 10, method: 'ping' }])
    expect(batch.status).toBe(400)
    expect(batch.json.error.code).toBe(-32600)
    const invalid = await post({ jsonrpc: '1.0', id: 11, method: 'ping' })
    expect(invalid.json.error.code).toBe(-32600)
    // A request without a usable method is an error the client can see, never a silent 202.
    for (const malformed of [
      { jsonrpc: '2.0', id: 13, method: 5 },
      { jsonrpc: '2.0', id: 13 },
    ]) {
      const answer = await post(malformed)
      expect(answer.status).toBe(400)
      expect(answer.json).toMatchObject({
        id: 13,
        error: { code: -32600 },
      })
    }
    const unidentified = await post({ jsonrpc: '2.0', method: 7 })
    expect(unidentified.status).toBe(400)
    expect(unidentified.json.id).toBeUndefined()
    // A response sent to the server has nothing to answer.
    const reply = await post({ jsonrpc: '2.0', id: 14, result: {} })
    expect(reply.status).toBe(202)
    expect(reply.json).toBeNull()
    const badVersion = await post(
      { jsonrpc: '2.0', id: 12, method: 'tools/list' },
      { 'MCP-Protocol-Version': '1999-01-01' },
    )
    expect(badVersion.status).toBe(400)
  })
})

describe('MCP, stateless 2026-07-28 revision', () => {
  it('describes itself through server/discover', async () => {
    const { status, json } = await modern(20, 'server/discover')
    expect(status).toBe(200)
    expect(json.result.resultType).toBe('complete')
    expect(json.result.supportedVersions).toEqual([
      ...MODERN_VERSIONS,
      ...LEGACY_VERSIONS,
    ])
    expect(json.result.capabilities).toEqual({ tools: { listChanged: false } })
    expect(json.result._meta['io.modelcontextprotocol/serverInfo'].name).toBe(
      'gsip-public',
    )
    expect(json.result).toMatchObject({
      cacheScope: 'public',
      ttlMs: 3_600_000,
    })
  })

  it('lists cacheable tools and calls them without a handshake', async () => {
    const list = await modern(21, 'tools/list')
    expect(list.json.result).toMatchObject({
      resultType: 'complete',
      cacheScope: 'public',
    })
    expect(list.json.result.tools).toHaveLength(4)
    const call = await modern(22, 'tools/call', {
      name: 'list_cells',
      arguments: { within: BURLINGTON_R4, limit: 3 },
    })
    expect(call.json.result.resultType).toBe('complete')
    expect(call.json.result.structuredContent.data.cells).toHaveLength(3)
    expect(call.json.result.structuredContent.data.next).not.toBeNull()
  })

  it('rejects headers that do not mirror the body', async () => {
    const body = {
      jsonrpc: '2.0',
      id: 23,
      method: 'tools/call',
      params: {
        name: 'get_release',
        arguments: {},
        _meta: { 'io.modelcontextprotocol/protocolVersion': MODERN },
      },
    }
    const missing = await post(body, {
      'MCP-Protocol-Version': MODERN,
      'Mcp-Method': 'tools/call',
    })
    expect(missing.status).toBe(400)
    expect(missing.json.error.code).toBe(-32020)
    const wrongMethod = await post(body, {
      'MCP-Protocol-Version': MODERN,
      'Mcp-Method': 'tools/list',
      'Mcp-Name': 'get_release',
    })
    expect(wrongMethod.json.error.code).toBe(-32020)
    const encoded = await post(body, {
      'MCP-Protocol-Version': MODERN,
      'Mcp-Method': 'tools/call',
      'Mcp-Name': `=?base64?${btoa('get_release')}?=`,
    })
    expect(encoded.status).toBe(200)
    expect(encoded.json.result.isError).toBe(false)
  })

  it('names its supported versions when a request uses another', async () => {
    const { status, json } = await modern(24, 'tools/list', {}, '2027-01-01')
    expect(status).toBe(400)
    expect(json.error.code).toBe(-32022)
    expect(json.error.data).toEqual({
      supported: [...MODERN_VERSIONS, ...LEGACY_VERSIONS],
      requested: '2027-01-01',
    })
  })

  it('answers an unknown method with 404 and a JSON-RPC error', async () => {
    const { status, json } = await modern(25, 'resources/list')
    expect(status).toBe(404)
    expect(json.error.code).toBe(-32601)
  })

  it('answers ping', async () => {
    const { status, json } = await modern(26, 'ping')
    expect(status).toBe(200)
    expect(json.result.resultType).toBe('complete')
  })
})

describe('MCP transport', () => {
  it('offers no GET stream and no sessions to delete', async () => {
    for (const method of ['GET', 'DELETE']) {
      const response = await handle(new Request(ENDPOINT, { method }))
      expect(response.status).toBe(405)
      expect(response.headers.get('allow')).toContain('POST')
    }
  })

  it('serves every well-formed origin and refuses only a malformed header', async () => {
    // Public, read-only and uncredentialed: sandboxed frames, local files, extensions and app
    // webviews are all welcome.
    for (const origin of [
      'https://example.org',
      'http://localhost:6274',
      'null',
      'chrome-extension://abcdefghijklmnop',
      'tauri://localhost',
    ]) {
      const { status } = await post(
        { jsonrpc: '2.0', id: 30, method: 'ping' },
        { Origin: origin },
      )
      expect(status, origin).toBe(200)
    }
    for (const origin of ['https://example.org/path', 'not an origin', '']) {
      const { status, json } = await post(
        { jsonrpc: '2.0', id: 31, method: 'ping' },
        { Origin: origin },
      )
      expect(status, origin).toBe(403)
      expect(json.error.code).toBe(-32600)
    }
  })

  it('refuses oversized bodies', async () => {
    const { status } = await post({
      jsonrpc: '2.0',
      id: 32,
      method: 'ping',
      params: { pad: 'x'.repeat(70_000) },
    })
    expect(status).toBe(413)
  })

  it('refuses a declared oversized body without reading it', async () => {
    let pulled = false
    // highWaterMark 0: the stream is pulled only when someone reads it.
    const body = new ReadableStream<Uint8Array>(
      {
        pull() {
          pulled = true
          throw new Error('the body must not be read')
        },
      },
      { highWaterMark: 0 },
    )
    const response = await handle(
      new Request(ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': String(100 * 1024 * 1024),
        },
        body,
        duplex: 'half',
      } as RequestInit),
    )
    expect(response.status).toBe(413)
    expect(pulled).toBe(false)
  })

  it('stops reading an undeclared body once it passes the limit', async () => {
    const chunk = new TextEncoder().encode('x'.repeat(16 * 1024))
    let sent = 0
    let cancelled = false
    const body = new ReadableStream<Uint8Array>({
      pull(controller) {
        sent += 1
        controller.enqueue(chunk)
      },
      cancel() {
        cancelled = true
      },
    })
    const response = await handle(
      new Request(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        duplex: 'half',
      } as RequestInit),
    )
    expect(response.status).toBe(413)
    expect(cancelled).toBe(true)
    // 64 KiB is four chunks; reading stops at the fifth, never draining the stream.
    expect(sent).toBeLessThanOrEqual(6)
  })

  it('answers a body that is not UTF-8 as a parse error', async () => {
    const response = await handle(
      new Request(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: new Uint8Array([0x7b, 0xff, 0xfe, 0x7d]),
      }),
    )
    expect(response.status).toBe(400)
    expect((await response.json()).error.code).toBe(-32700)
  })
})
