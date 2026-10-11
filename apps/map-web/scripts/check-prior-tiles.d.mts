export type ArchiveReader = { getMetadata(): Promise<unknown> }

export function checkPriorTiles(options: {
  base: string
  open: (url: string) => ArchiveReader
  palette: { layers: { id: string }[]; version: string }
}): Promise<string[]>
