import { create } from 'zustand'

const getSystemTheme = () =>
  window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'

const applyTheme = (theme) => {
  const resolved = theme === 'system' ? getSystemTheme() : theme
  if (resolved === 'dark') {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

const getInitialTheme = () => {
  try { return localStorage.getItem('itera-theme') || 'system' } catch { return 'system' }
}

const initialTheme = getInitialTheme()
applyTheme(initialTheme)

// Listen for system preference changes
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  if (useThemeStore.getState().theme === 'system') applyTheme('system')
})

const useThemeStore = create((set) => ({
  theme: initialTheme,
  setTheme: (theme) => {
    try { localStorage.setItem('itera-theme', theme) } catch {}
    applyTheme(theme)
    set({ theme })
  },
}))

export default useThemeStore