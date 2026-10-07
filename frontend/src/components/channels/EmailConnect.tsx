import { useState, useEffect } from 'react'
import { Globe, Info } from 'lucide-react'
import Button from '../common/Button'
import { channelApi } from '../../api/client'
import { settingsApi } from '../../api/settings'

interface EmailConnectProps {
  onConnected: () => void
  initialEmail?: string
}

interface ProviderConfig {
  label: string
  imap_host: string
  imap_port: number
  smtp_host: string
  smtp_port: number
}

const PROVIDERS: Record<string, ProviderConfig> = {
  gmail: { label: 'Gmail', imap_host: 'imap.gmail.com', imap_port: 993, smtp_host: 'smtp.gmail.com', smtp_port: 465 },
  yandex: { label: 'Yandex', imap_host: 'imap.yandex.ru', imap_port: 993, smtp_host: 'smtp.yandex.ru', smtp_port: 465 },
  mailru: { label: 'Mail.ru', imap_host: 'imap.mail.ru', imap_port: 993, smtp_host: 'smtp.mail.ru', smtp_port: 465 },
  outlook: { label: 'Outlook', imap_host: 'outlook.office365.com', imap_port: 993, smtp_host: 'smtp.office365.com', smtp_port: 587 },
  yahoo: { label: 'Yahoo', imap_host: 'imap.mail.yahoo.com', imap_port: 993, smtp_host: 'smtp.mail.yahoo.com', smtp_port: 465 },
  icloud: { label: 'iCloud', imap_host: 'imap.mail.me.com', imap_port: 993, smtp_host: 'smtp.mail.me.com', smtp_port: 587 },
}

function EmailConnect({ onConnected, initialEmail }: EmailConnectProps) {
  const [form, setForm] = useState({
    email: '',
    password: '',
    imap_host: '',
    smtp_host: '',
    imap_port: 993,
    smtp_port: 465,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedProvider, setSelectedProvider] = useState('')

  const isReconnect = !!initialEmail

  useEffect(() => {
    if (initialEmail) {
      setForm(prev => ({ ...prev, email: initialEmail }))
      return
    }
    settingsApi.onboardingConfig().then(config => {
      if (config.email) {
        setForm(prev => ({
          ...prev,
          email: config.email?.email || prev.email,
          password: config.email?.password || prev.password,
          imap_host: config.email?.imap_host || prev.imap_host,
          imap_port: config.email?.imap_port || prev.imap_port,
          smtp_host: config.email?.smtp_host || prev.smtp_host,
          smtp_port: config.email?.smtp_port || prev.smtp_port,
        }))
      }
    }).catch(() => {})
  }, [initialEmail])

  const handleChange = (field: string, value: string | number) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleProviderChange = (key: string) => {
    setSelectedProvider(key)
    if (key && key !== '__custom__') {
      const p = PROVIDERS[key]
      setForm(prev => ({
        ...prev,
        imap_host: p.imap_host,
        imap_port: p.imap_port,
        smtp_host: p.smtp_host,
        smtp_port: p.smtp_port,
      }))
    }
  }

  const connect = async () => {
    setLoading(true)
    setError(null)
    try {
      if (isReconnect) {
        await channelApi.reconnectEmail(form)
      } else {
        await channelApi.connectEmail(form)
      }
      onConnected()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка подключения')
    } finally {
      setLoading(false)
    }
  }

  const canSubmit = form.email && form.password && form.imap_host && form.smtp_host

  return (
    <div className="p-4 rounded-xl border border-gray-200 bg-white space-y-3">
      <div className="flex items-center gap-2">
        <Globe className="w-5 h-5 text-blue-600" />
        <span className="font-medium text-gray-900">
          {isReconnect ? 'Переподключить Email' : 'Подключить Email'}
        </span>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-2">
        <Info className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
        <div className="text-xs text-amber-700 space-y-1">
          <p className="font-medium">Пароль приложения</p>
          <p>Gmail: Настройки → Безопасность → Пароли приложений</p>
          <p>Yandex: Настройки → Безопасность → Пароли приложений</p>
          <p>Mail.ru: Настройки → Безопасность → Пароли приложений</p>
        </div>
      </div>

      {!isReconnect && (
        <div>
          <select
            value={selectedProvider}
            onChange={e => handleProviderChange(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary bg-white"
          >
            <option value="">— Выберите провайдера —</option>
            {Object.entries(PROVIDERS).map(([key, p]) => (
              <option key={key} value={key}>{p.label}</option>
            ))}
            <option value="__custom__">Свой вариант (ввести вручную)</option>
          </select>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <input
          type="email"
          value={form.email}
          onChange={(e) => handleChange('email', e.target.value)}
          placeholder="email@example.com"
          disabled={isReconnect}
          className="px-3 py-2 rounded-lg border border-gray-300 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary disabled:bg-gray-50 disabled:text-gray-500"
        />
        <input
          type="password"
          value={form.password}
          onChange={(e) => handleChange('password', e.target.value)}
          placeholder="Пароль приложения"
          className="px-3 py-2 rounded-lg border border-gray-300 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
        />
        <input
          type="text"
          value={form.imap_host}
          onChange={(e) => handleChange('imap_host', e.target.value)}
          placeholder="IMAP сервер"
          className="px-3 py-2 rounded-lg border border-gray-300 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
        />
        <input
          type="text"
          value={form.smtp_host}
          onChange={(e) => handleChange('smtp_host', e.target.value)}
          placeholder="SMTP сервер"
          className="px-3 py-2 rounded-lg border border-gray-300 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
        />
        <input
          type="number"
          value={form.imap_port}
          onChange={(e) => handleChange('imap_port', Number(e.target.value))}
          placeholder="IMAP порт (993)"
          className="px-3 py-2 rounded-lg border border-gray-300 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
        />
        <input
          type="number"
          value={form.smtp_port}
          onChange={(e) => handleChange('smtp_port', Number(e.target.value))}
          placeholder="SMTP порт (465)"
          className="px-3 py-2 rounded-lg border border-gray-300 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
        />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <Button onClick={connect} disabled={loading || !canSubmit}>
        {loading ? 'Подключение...' : isReconnect ? 'Переподключить' : 'Подключить'}
      </Button>
    </div>
  )
}

export default EmailConnect
