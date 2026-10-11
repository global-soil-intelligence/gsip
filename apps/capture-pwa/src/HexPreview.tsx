export function HexPreview({ cell }: { cell: string }) {
  return (
    <figure
      className="hex-preview"
      aria-label={`Private preview of H3 cell ${cell}`}
    >
      <svg
        viewBox="0 0 240 150"
        role="img"
        aria-label="Your area as an H3 cell"
      >
        <path d="M120 12 210 62v52l-90 50-90-50V62z" />
        <circle cx="58" cy="42" r="3" />
        <circle cx="188" cy="126" r="4" />
        <path className="contour" d="M18 96c32-30 58-16 86-35s62-26 118-4" />
      </svg>
      <figcaption>
        Your area, H3 cell <code>{cell}</code>. Shown only to you; public maps
        show a cell only once at least three contributors share it.
      </figcaption>
    </figure>
  )
}
