import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App, type PageId } from './App'
import './styles.css'

const page = (document.body.dataset.page ?? 'home') as PageId

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App page={page} />
  </StrictMode>,
)
