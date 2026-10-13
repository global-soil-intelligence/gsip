import { isNativeApp } from './index'

/** The canonical public site (WP-SITE-1D). */
export const SITE_ORIGIN = 'https://globalsoilintelligence.com'

/**
 * A link to the public site. On the website the capture app is served at /capture/, so links
 * stay relative; the phone app's pages are not on the site, so its links become absolute and
 * open in the browser.
 */
export function siteLink(
  path: string,
  native: boolean = isNativeApp(),
): string {
  return native ? new URL(path, `${SITE_ORIGIN}/capture/`).toString() : path
}
