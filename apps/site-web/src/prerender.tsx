import { StrictMode } from 'react'
import { renderToString } from 'react-dom/server'
import { App, PAGES, type PageId, pageMeta } from './App'

/** Server-side render of one page, for apps/site-web/scripts/prerender.mjs. */
export function render(page: PageId): string {
  return renderToString(
    <StrictMode>
      <App page={page} />
    </StrictMode>,
  )
}

export function headline(page: PageId): string {
  return pageMeta[page].title
}

export { PAGES }
