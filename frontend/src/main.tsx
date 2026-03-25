import { StrictMode, useEffect, useLayoutEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme] = useState<'light' | 'dark'>(() => {
    try {
      const saved = window.localStorage.getItem('theme')
      if (saved === 'light' || saved === 'dark') return saved
    } catch (err) { void err }
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })
  useLayoutEffect(() => {
    const root = document.documentElement
    if (theme === 'dark') root.classList.add('dark')
    else root.classList.remove('dark')
  }, [theme])
  useEffect(() => {
    try {
      window.localStorage.setItem('theme', theme)
    } catch (err) { void err }
  }, [theme])
  return (
    <div data-theme={theme}>
      {children}
    </div>
  )
}

const queryClient = new QueryClient()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
        <Toaster position="top-right" richColors closeButton />
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
)
