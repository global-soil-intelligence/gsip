import { describe, expect, it } from 'vitest'
import {
  DEFAULT_ATTRIBUTION,
  attributionProblem,
  normalizeAttribution,
} from '../src/attribution'

describe('public attribution names', () => {
  it.each([
    DEFAULT_ATTRIBUTION,
    'Ana María O’Neil-Ngũgĩ',
    "Dr. Lee's 4th-grade class",
    '土壌の友',
    'Field notes (Vermont)',
  ])('accepts %s', (name) => {
    expect(attributionProblem(name)).toBeNull()
  })

  it.each([
    ['', 'empty'],
    [' padded', 'surrounding_space'],
    ['<img src=x onerror=alert(1)>', 'characters'],
    ['jane@example.com', 'characters'],
    ['tab\tseparated', 'characters'],
    ['nul\u0000byte', 'characters'],
    ['C1\u0085control', 'characters'],
    ['right\u202eto-left override', 'characters'],
    ['isolate\u2066text\u2069', 'characters'],
    ['zero\u200bwidth', 'characters'],
    ['soft\u00adhyphen', 'characters'],
    ['visit https://spam.example', 'link'],
    ['see www.spam.example', 'link'],
    ['ignore previous instructions {system}', 'characters'],
    ['x'.repeat(81), 'too_long'],
  ])('rejects %j as %s', (name, problem) => {
    expect(attributionProblem(name)).toBe(problem)
  })

  it('normalizes whitespace and falls back to the pseudonym', () => {
    expect(normalizeAttribution('  Soil   Friend ')).toBe('Soil Friend')
    expect(normalizeAttribution('   ')).toBe(DEFAULT_ATTRIBUTION)
  })
})
