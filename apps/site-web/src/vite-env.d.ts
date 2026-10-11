/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CAPTURE_LIVE?: string
  readonly VITE_DATASET_URL?: string
  readonly VITE_GSIP_PUBLIC_API?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
