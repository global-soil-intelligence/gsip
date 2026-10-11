import type { CapacitorConfig } from '@capacitor/cli'

/**
 * WP-APP-1: the GSIP phone app wraps this capture app. The native projects (android/, ios/) are
 * generated from this file in CI (.github/workflows/app-build.yml) and never committed; their
 * permissions come from scripts/app_permissions.py. Build the web assets with `pnpm build:app`.
 */
const config: CapacitorConfig = {
  appId: 'com.globalsoilintelligence.app',
  appName: 'GSIP Capture',
  webDir: 'dist',
  // Plugin results include precise positions; they never go to the device log, even in debug builds.
  loggingBehavior: 'none',
  android: {
    // Every request goes to HTTPS endpoints; never load mixed content.
    allowMixedContent: false,
    // No geolocation plugin on Android: it would compile Google's closed Play services location
    // SDK into the app (BUILD_ORDER guardrail 6). The web view's own location API asks for the
    // same foreground permissions instead.
    includePlugins: ['@capacitor/camera', '@capacitor/filesystem'],
  },
}

export default config
