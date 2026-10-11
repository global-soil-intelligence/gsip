/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CAPTURE_LIVE?: string
  readonly VITE_PRIVACY_URL?: string
  readonly VITE_SAMPLING_RULES_URL?: string
  readonly VITE_SUPABASE_PUBLISHABLE_KEY?: string
  readonly VITE_SUPABASE_URL?: string
  readonly VITE_TERMS_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
