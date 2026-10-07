import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/index.css'
import App from './App'
import { initTheme } from './utils/theme'

const VERSION_KEY = 'bizibox:app-version'

initTheme()

// Десктоп-сборка: сервис-воркер PWA ломает API-запросы и не нужен (бэкенд локальный).
// Принудительно снимаем регистрацию любых ранее установленных SW.
if ('serviceWorker' in navigator) {
  navigator.serviceWorker
    .getRegistrations()
    .then((registrations) => {
      for (const reg of registrations) reg.unregister()
    })
    .catch(() => {})
}

async function clearStaleCaches(): Promise<void> {
  if (!('caches' in window)) return
  try {
    const keys = await caches.keys()
    await Promise.all(keys.map((k) => caches.delete(k)))
  } catch {
    // Не критично — пропускаем.
  }
}

// При обновлении версии приложения очищаем браузерный кэш, чтобы пользователь
// гарантированно увидел свежую версию без ручной очистки.
async function syncVersion(): Promise<void> {
  try {
    const res = await fetch('/api/health', { cache: 'no-store' })
    if (!res.ok) return
    const data = (await res.json()) as { version?: string }
    const current = data.version
    if (!current) return
    const stored = localStorage.getItem(VERSION_KEY)
    if (stored !== current) {
      await clearStaleCaches()
      localStorage.setItem(VERSION_KEY, current)
    }
  } catch {
    // Сервер ещё не готов или оффлайн — пропускаем, повторится при следующем запуске.
  }
}

void syncVersion()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
