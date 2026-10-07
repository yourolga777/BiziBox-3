import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Inbox, Loader2, CheckCircle2, AlertTriangle, ChevronRight } from 'lucide-react'
import Button from '../components/common/Button'
import { startupApi } from '../api/startup'
import { isOfflineError } from '../api/client'
import type { StartupLoadResult } from '../types/startup'
import { useOnlineStatus } from '../hooks/useOnlineStatus'

interface StartupLoadingProps {
  onComplete: () => void
}

const CHANNEL_LABELS: Record<string, string> = {
  telegram: 'Telegram',
  email: 'Email',
}

function StartupLoading({ onComplete }: StartupLoadingProps) {
  const online = useOnlineStatus()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<StartupLoadResult | null>(null)
  const loadPromiseRef = useRef<Promise<StartupLoadResult> | null>(null)

  useEffect(() => {
    if (!online) {
      onComplete()
      return
    }

    let cancelled = false
    let completed = false
    const finish = () => {
      if (cancelled || completed) return
      completed = true
      onComplete()
    }
    const fallback = setTimeout(finish, 8000)

    loadPromiseRef.current ??= startupApi.load()
    loadPromiseRef.current
      .then((res) => {
        if (cancelled) return
        clearTimeout(fallback)
        setResult(res)
      })
      .catch((err) => {
        if (cancelled) return
        clearTimeout(fallback)
        if (isOfflineError(err)) {
          finish()
          return
        }
        setError(err instanceof Error ? err.message : 'Ошибка загрузки')
        setTimeout(finish, 4000)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
      clearTimeout(fallback)
    }
  }, [online])

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-white rounded-2xl shadow-xl p-8 text-center">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="p-3 bg-primary/10 rounded-xl">
              <Inbox className="w-8 h-8 text-primary" />
            </div>
          </div>
          <h1 className="text-xl font-semibold text-gray-900 mb-2">Загрузка входящих</h1>
          <div className="flex items-center justify-center gap-2 text-gray-500">
            <Loader2 className="w-5 h-5 animate-spin" />
            <p className="text-sm">Подключаем каналы и загружаем сообщения...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error && !result) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-white rounded-2xl shadow-xl p-8 text-center">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="p-3 bg-amber-100 rounded-xl">
              <AlertTriangle className="w-8 h-8 text-amber-600" />
            </div>
          </div>
          <h1 className="text-xl font-semibold text-gray-900 mb-2">Не удалось загрузить</h1>
          <p className="text-sm text-gray-500 mb-6">{error}</p>
          <Button onClick={onComplete}>
            Продолжить
          </Button>
        </div>
      </div>
    )
  }

  const channels = result?.channels ?? []
  const totalNew = result?.total_new ?? 0

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-3 bg-emerald-100 rounded-xl">
            <CheckCircle2 className="w-8 h-8 text-emerald-600" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Готово</h1>
            <p className="text-sm text-gray-500">Каналы загружены</p>
          </div>
        </div>

        <div className="bg-gray-50 rounded-xl p-4 mb-4 text-center">
          <p className="text-3xl font-bold text-gray-900">{totalNew}</p>
          <p className="text-sm text-gray-500">новых сообщений</p>
        </div>

        <div className="space-y-2 mb-6">
          {channels.map((ch) => (
            <div
              key={ch.type}
              className="flex items-center justify-between bg-white border border-gray-200 rounded-xl px-4 py-3"
            >
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-800">
                  {CHANNEL_LABELS[ch.type] ?? ch.name}
                </span>
                {ch.connected && ch.new_messages > 0 && (
                  <span className="text-xs text-gray-500">+{ch.new_messages}</span>
                )}
              </div>
              {ch.connected ? (
                <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                  Подключён
                </span>
              ) : (
                <button
                  onClick={() => navigate('/channels')}
                  className="text-xs font-medium text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full hover:bg-amber-100 transition-colors"
                >
                  Не подключён
                </button>
              )}
            </div>
          ))}
        </div>

        {channels.some((ch) => !ch.connected) && (
          <p className="text-xs text-gray-400 mb-4">
            Некоторые каналы не удалось подключить. Нажмите «Не подключён», чтобы настроить.
          </p>
        )}

        <Button className="w-full" onClick={onComplete}>
          Продолжить <ChevronRight className="w-4 h-4 ml-1" />
        </Button>
      </div>
    </div>
  )
}

export default StartupLoading
