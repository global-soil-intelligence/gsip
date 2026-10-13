import { StrictMode } from 'react'
import { createRoot, hydrateRoot } from 'react-dom/client'
import { App, type PageId } from './App'
import './styles.css'

const page = (document.body.dataset.page ?? 'home') as PageId
const root = document.getElementById('root')!
const app = (
  <StrictMode>
    <App page={page} />
  </StrictMode>
)

// Built pages arrive prerendered (WP-AGENT-1), so people and crawlers read them without
// JavaScript; the browser then attaches to that markup instead of drawing it again.
if (root.hasChildNodes()) hydrateRoot(root, app)
else createRoot(root).render(app)
