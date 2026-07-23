export function HexPreview({ cell }: { cell: string }) {
  return (
    <figure className="hex-preview" aria-label={`Public H3 cell ${cell}`}>
      <svg viewBox="0 0 240 150" role="img" aria-label="Fuzzed public map cell">
        <path d="M120 12 210 62v52l-90 50-90-50V62z" />
        <circle cx="58" cy="42" r="3" />
        <circle cx="188" cy="126" r="4" />
        <path className="contour" d="M18 96c32-30 58-16 86-35s62-26 118-4" />
      </svg>
      <figcaption>
        Public cell <code>{cell}</code>
      </figcaption>
    </figure>
  )
}
