// File: launcher/src/main.tsx

import { App } from '@/App'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@/styles.css'

const rootElement = document.getElementById('root')
if (rootElement && !rootElement.innerHTML) {
  createRoot(rootElement).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}
