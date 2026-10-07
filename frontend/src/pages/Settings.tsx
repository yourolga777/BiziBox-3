import { useState, useEffect, useRef } from 'react'
import Card from '../components/common/Card'
import { useToast } from '../components/common/Toast'
import { settingsApi } from '../api/settings'
import { initTheme, storeTheme } from '../utils/theme'
import { getNotificationPermission, isPushSupported, requestNotificationPermission, subscribeToPush } from '../notifications/push'
import NetworkModeSelector, { type ProxyFields } from '../components/common/NetworkModeSelector'
import type { NetworkMode, Settings } from '../types/settings'

function Settings() {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [loading, setLoading] = useState(true)
  const [importResult, setImportResult] = useState<{
    status: string
    imported: Record<string, { created: number; updated: number }>
  } | null>(null)
  const [notifPermission, setNotifPermission] = useState<string>(() => getNotificationPermission())
  const [enablingNotifs, setEnablingNotifs] = useState(false)
  const [telegramInterval, setTelegramInterval] = useState<number | null>(null)
  const [emailInterval, setEmailInterval] = useState<number | null>(null)
  const [proxyMode, setProxyMode] = useState<NetworkMode>('direct')
  const [proxyFields, setProxyFields] = useState<ProxyFields>({ type: 'socks5', host: '', port: '', username: '', password: '', secret: '' })
  const [savingProxy, setSavingProxy] = useState(false)
  const debounceTimers = useRef<Record<string, ReturnType<typeof setTimeout>>>({})
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { showToast } = useToast()

  useEffect(() => {
    settingsApi.get().then((data) => {
      setSettings(data)
      setTelegramInterval(typeof data.telegram_poll_interval === 'number' ? data.telegram_poll_interval : null)
      setEmailInterval(typeof data.email_poll_interval === 'number' ? data.email_poll_interval : null)
      const px = data.proxy_config
      if (px && typeof px === 'object') {
        const p = px as Record<string, unknown>
        const rawMode = String(p.mode ?? '')
        const mode: NetworkMode =
          rawMode === 'system_vpn' || rawMode === 'custom_proxy'
            ? rawMode
            : p.enabled && p.host && p.port
              ? 'custom_proxy'
              : 'direct'
        setProxyMode(mode)
        setProxyFields({
          type: String(p.type ?? 'socks5'),
          host: p.host ? String(p.host) : '',
          port: p.port ? String(p.port) : '',
          username: p.username ? String(p.username) : '',
          password: '',
          secret: '',
        })
      }
      setLoading(false)
    }).catch(() => {
      setLoading(false)
      showToast('Ошибка загрузки настроек', 'error')
    })
  }, [])

  useEffect(() => {
    initTheme()
  }, [])

  async function updateSetting(key: string, value: unknown) {
    try {
      const updated = await settingsApi.update({ values: { [key]: value } })
      setSettings(updated as Settings)
    } catch {
      showToast('Ошибка сохранения', 'error')
    }
  }

  function updateSettingDebounced(key: string, value: unknown) {
    if (debounceTimers.current[key]) clearTimeout(debounceTimers.current[key])
    debounceTimers.current[key] = setTimeout(() => updateSetting(key, value), 400)
  }

  function toggleTheme() {
    const newTheme = settings?.theme === 'dark' ? 'light' : 'dark'
    storeTheme(newTheme)
    updateSetting('theme', newTheme)
  }

  async function saveProxy() {
    if (proxyMode === 'custom_proxy' && (!proxyFields.host.trim() || !proxyFields.port.trim())) {
      showToast('Укажите хост и порт прокси', 'error')
      return
    }
    setSavingProxy(true)
    try {
      const proxyConfig: Record<string, unknown> = {
        mode: proxyMode,
        enabled: proxyMode === 'custom_proxy',
        type: proxyFields.type,
        host: proxyMode === 'custom_proxy' ? proxyFields.host.trim() : '',
        port: proxyMode === 'custom_proxy' ? Number(proxyFields.port) : null,
        username: proxyFields.username.trim() || null,
      }
      if (proxyFields.password) proxyConfig.password = proxyFields.password
      if (proxyFields.secret) proxyConfig.secret = proxyFields.secret
      const updated = await settingsApi.update({ values: { proxy_config: proxyConfig } })
      setSettings(updated as Settings)
      showToast('Настройки прокси сохранены', 'success')
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Ошибка сохранения прокси', 'error')
    } finally {
      setSavingProxy(false)
    }
  }

  async function handleEnableNotifications() {
    if (enablingNotifs) return
    setEnablingNotifs(true)
    try {
      const permission = await requestNotificationPermission()
      setNotifPermission(permission)
      if (permission !== 'granted') {
        showToast('Разрешение на уведомления не получено', 'error')
        return
      }
      await subscribeToPush()
      showToast('Уведомления включены', 'success')
    } catch {
      showToast('Не удалось включить уведомления', 'error')
    } finally {
      setEnablingNotifs(false)
    }
  }

  async function handleExport() {
    try {
      const response = await fetch('/api/export/all')
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `bizibox-export-${new Date().toISOString().split('T')[0]}.json`
      a.click()
      window.URL.revokeObjectURL(url)
      showToast('Данные экспортированы', 'success')
    } catch {
      showToast('Ошибка экспорта', 'error')
    }
  }

  async function handleImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('/api/import/all', {
        method: 'POST',
        body: formData,
      })
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Ошибка импорта' }))
        throw new Error(err.detail || 'Ошибка импорта')
      }
      const data = await response.json()
      setImportResult(data)
      showToast('Данные импортированы', 'success')
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Ошибка импорта', 'error')
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">Настройки</h2>
        <Card><p className="text-gray-500">Загрузка...</p></Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">Настройки</h2>

      <Card>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Общие настройки</h3>
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Интервал опроса Telegram: {telegramInterval ?? settings?.telegram_poll_interval ?? 10} сек
            </label>
            <input
              type="range"
              min="10"
              max="60"
              step="5"
              value={telegramInterval ?? settings?.telegram_poll_interval ?? 10}
              onChange={(e) => {
                const v = parseInt(e.target.value, 10)
                setTelegramInterval(v)
                updateSettingDebounced('telegram_poll_interval', v)
              }}
              className="w-full accent-indigo-500"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>10 сек</span>
              <span>60 сек</span>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Интервал опроса Email: {emailInterval ?? settings?.email_poll_interval ?? 60} сек
            </label>
            <input
              type="range"
              min="30"
              max="300"
              step="10"
              value={emailInterval ?? settings?.email_poll_interval ?? 60}
              onChange={(e) => {
                const v = parseInt(e.target.value, 10)
                setEmailInterval(v)
                updateSettingDebounced('email_poll_interval', v)
              }}
              className="w-full accent-indigo-500"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>30 сек</span>
              <span>300 сек</span>
            </div>
          </div>
        </div>
      </Card>

      <Card>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">VPN / Прокси</h3>
        <div className="space-y-4">
          <NetworkModeSelector
            mode={proxyMode}
            fields={proxyFields}
            onModeChange={setProxyMode}
            onFieldsChange={(field, value) => setProxyFields(prev => ({ ...prev, [field]: value }))}
          />
          <button
            onClick={saveProxy}
            disabled={savingProxy}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-500 rounded-lg hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {savingProxy ? 'Сохранение...' : 'Сохранить прокси'}
          </button>
        </div>
      </Card>

      <Card>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Внешний вид</h3>
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-700 dark:text-gray-300">
            Тема: {settings?.theme === 'dark' ? 'Тёмная' : 'Светлая'}
          </span>
          <button
            onClick={toggleTheme}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              settings?.theme === 'dark' ? 'bg-indigo-500' : 'bg-gray-300'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                settings?.theme === 'dark' ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      </Card>

      <Card>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Уведомления</h3>
        <div className="flex items-center justify-between gap-4">
          <div className="text-sm text-gray-700 dark:text-gray-300">
            {!isPushSupported() ? (
              'Push-уведомления не поддерживаются в этом браузере'
            ) : notifPermission === 'granted' ? (
              'Уведомления включены'
            ) : notifPermission === 'denied' ? (
              'Уведомления заблокированы в настройках браузера'
            ) : (
              'Получайте уведомления о новых сообщениях и просроченных задачах'
            )}
          </div>
          <button
            onClick={handleEnableNotifications}
            disabled={!isPushSupported() || enablingNotifs || notifPermission === 'granted'}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-500 rounded-lg hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {enablingNotifs ? 'Включение...' : notifPermission === 'granted' ? 'Включены' : 'Включить'}
          </button>
        </div>
      </Card>

      <Card>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Шаблоны ответов</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Быстрые шаблоны для ответов будут позже.
        </p>
      </Card>

      <Card>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Данные</h3>
        <p className="text-sm text-gray-500 mb-3">
          Будут экспортированы: контакты, сообщения, задачи, события календаря.
        </p>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleExport}
            className="px-4 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors text-sm font-medium"
          >
            Экспорт всех данных
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-4 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors text-sm font-medium"
          >
            Импорт данных
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            onChange={handleImport}
            className="hidden"
          />
        </div>
        {importResult && (
          <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg text-sm text-gray-700 dark:text-gray-300">
            <p className="font-medium mb-2">Результат импорта:</p>
            <ul className="space-y-1">
              {Object.entries(importResult.imported).map(([key, val]) => (
                <li key={key}>
                  {key}: создано {val.created}, обновлено {val.updated}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>

      <Card>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">О приложении</h3>
        <div className="text-sm text-gray-600 dark:text-gray-400 space-y-2">
          <p>Версия: <span className="font-medium">2.0.0</span></p>
          <p>
            BiziBox — локальное PWA-приложение для личных сообщений и дел.
            Объединяет Telegram, Email, контакты, задачи и календарь в одном окне.
          </p>
          <p className="text-gray-400">
            Справку по разделам можно открыть кнопкой «Справка» в меню слева.
          </p>
        </div>
      </Card>

    </div>
  )
}

export default Settings
