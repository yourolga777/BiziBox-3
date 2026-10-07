import { useState, useEffect } from 'react'
import { Info, MessageCircle } from 'lucide-react'
import Button from '../common/Button'
import { channelApi } from '../../api/client'
import { settingsApi } from '../../api/settings'

interface VkConnectProps {
  onConnected: () => void
}

function VkConnect({ onConnected }: VkConnectProps) {
  const [form, setForm] = useState({ group_id: '', token: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    settingsApi.onboardingConfig().then(config => {
      if (config.vk) {
        setForm(prev => ({
          ...prev,
          group_id: config.vk?.group_id ? String(config.vk.group_id) : prev.group_id,
          token: config.vk?.token || prev.token,
        }))
      }
    }).catch(() => {})
  }, [])

  const connect = async () => {
    setLoading(true)
    setError(null)
    try {
      await channelApi.connectVk({
        group_id: form.group_id ? Number(form.group_id) : undefined,
        token: form.token || undefined,
      })
      onConnected()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка подключения')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-4 rounded-xl border border-gray-200 bg-white space-y-3">
      <div className="flex items-center gap-2">
        <MessageCircle className="w-5 h-5 text-blue-600" />
        <span className="font-medium text-gray-900">Подключить ВКонтакте</span>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-start gap-2">
        <Info className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
        <div className="text-xs text-blue-700 space-y-1">
          <p className="font-medium">Как получить данные</p>
          <p>1. Создайте сообщество на vk.com и включите «Сообщения сообщества».</p>
          <p>2. «Управление» → «Работа с API» → «Ключи доступа» → создайте ключ с правом «Сообщения сообщества».</p>
          <p>3. Включите Long Poll API и событие «Входящее сообщение».</p>
          <p className="text-blue-500">Поля можно оставить пустыми — данные возьмутся из .env.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3">
        <input
          type="text"
          value={form.group_id}
          onChange={(e) => setForm((prev) => ({ ...prev, group_id: e.target.value }))}
          placeholder="ID сообщества (например, 12345678)"
          className="px-3 py-2 rounded-lg border border-gray-300 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
        />
        <input
          type="password"
          value={form.token}
          onChange={(e) => setForm((prev) => ({ ...prev, token: e.target.value }))}
          placeholder="Токен (ключ доступа)"
          className="px-3 py-2 rounded-lg border border-gray-300 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
        />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <Button onClick={connect} disabled={loading}>
        {loading ? 'Подключение...' : 'Подключить'}
      </Button>
    </div>
  )
}

export default VkConnect
