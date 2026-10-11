// Vite (and so Vitest) loads repository files as text with `?raw` and `import.meta.glob`, which
// lets tests compare GSIP's sources without Node's type definitions.
declare module '*?raw' {
  const content: string
  export default content
}

interface ImportMeta {
  glob(
    patterns: string | string[],
    options: { eager: true; import: 'default'; query: '?raw' },
  ): Record<string, string>
}
