/// <reference types="vite/client" />

/** The capture app build, e.g. `0.1.0+abc1234` (WP-6e client_version claim). */
declare const __GSIP_CLIENT_VERSION__: string

interface ImportMetaEnv {
  readonly VITE_COLLECTION_MODE?: string
  readonly VITE_CAPTURE_LIVE?: string
  readonly VITE_LIBRARY_INTAKE_LIVE?: string
  readonly VITE_PRIVACY_URL?: string
  readonly VITE_SAMPLING_RULES_URL?: string
  readonly VITE_SUPABASE_PUBLISHABLE_KEY?: string
  readonly VITE_SUPABASE_URL?: string
  readonly VITE_TERMS_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
