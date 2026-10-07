export type Theme = 'light' | 'dark'

export function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle('dark', theme === 'dark')
}

export function getStoredTheme(): Theme {
  try {
    return localStorage.getItem('theme') === 'dark' ? 'dark' : 'light'
  } catch {
    return 'light'
  }
}

export function storeTheme(theme: Theme): void {
  try {
    localStorage.setItem('theme', theme)
  } catch {
    // localStorage может быть недоступен (private mode) — игнорируем
  }
  applyTheme(theme)
}

export function initTheme(): Theme {
  const theme = getStoredTheme()
  applyTheme(theme)
  return theme
}
