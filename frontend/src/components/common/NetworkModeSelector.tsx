import { useState } from 'react'
import { ChevronDown, ChevronUp, HelpCircle, Search, Shield } from 'lucide-react'
import { settingsApi, type VpnHelpResult } from '../../api/settings'
import type { NetworkMode } from '../../types/settings'

export interface ProxyFields {
  type: string
  host: string
  port: string
  username: string
  password: string
  secret: string
}

interface Props {
  mode: NetworkMode
  fields: ProxyFields
  onModeChange: (mode: NetworkMode) => void
  onFieldsChange: (field: keyof ProxyFields, value: string) => void
}

const MODES: { key: NetworkMode; title: string; short: string; detail: string }[] = [
  {
    key: 'direct',
    title: 'Напрямую (без VPN и прокси)',
    short: 'Telegram открывается на этом компьютере без дополнительных программ.',
    detail:
      'Выберите этот вариант, если Telegram работает как обычно, без VPN и прокси. BiziBox подключится к Telegram напрямую.',
  },
  {
    key: 'system_vpn',
    title: 'Системный VPN',
    short: 'OpenVPN, WireGuard, Happ, Mullvad, Proton VPN, NordVPN, Outline…',
    detail:
      'Системный VPN работает на уровне операционной системы: весь трафик компьютера уже идёт через VPN-туннель. Настраивать прокси не нужно — BiziBox подключится к Telegram как обычно, через ваш VPN.',
  },
  {
    key: 'custom_proxy',
    title: 'Свой прокси',
    short: 'v2rayN, Clash, Nekoray/NekoBox, Hiddify, Shadowsocks, MTProto-прокси…',
    detail:
      'Нужен, когда Telegram заблокирован, а системного VPN нет. Прокси-клиент открывает локальный адрес (обычно 127.0.0.1:порт) — укажите его ниже, и BiziBox будет ходить в Telegram через него.',
  },
]

const CATEGORY_LABELS: Record<string, string> = {
  system_vpn: 'Системный VPN',
  proxy: 'Прокси',
  mtproto: 'MTProto-прокси',
  unknown: 'Тип не определён',
}

export default function NetworkModeSelector({ mode, fields, onModeChange, onFieldsChange }: Props) {
  const [expanded, setExpanded] = useState<NetworkMode | null>(null)
  const [helpOpen, setHelpOpen] = useState(false)
  const [helpQuery, setHelpQuery] = useState('')
  const [helpResult, setHelpResult] = useState<VpnHelpResult | null>(null)
  const [helpLoading, setHelpLoading] = useState(false)
  const [helpError, setHelpError] = useState<string | null>(null)

  async function runHelp() {
    const q = helpQuery.trim()
    if (!q) return
    setHelpLoading(true)
    setHelpError(null)
    setHelpResult(null)
    try {
      const result = await settingsApi.vpnHelp(q)
      setHelpResult(result)
    } catch {
      setHelpError('Не удалось получить справку. Проверьте соединение с интернетом.')
    } finally {
      setHelpLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 bg-purple-100 rounded-lg">
          <Shield className="w-6 h-6 text-purple-600" />
        </div>
        <div>
          <h2 className="text-lg font-semibold">Прокси / VPN</h2>
          <p className="text-sm text-gray-500">Как BiziBox будет подключаться к Telegram</p>
        </div>
      </div>

      <div className="space-y-2">
        {MODES.map(entry => {
          const active = mode === entry.key
          const isExpanded = expanded === entry.key
          return (
            <div
              key={entry.key}
              className={`border rounded-xl transition-colors ${active ? 'border-blue-400 bg-blue-50/50' : 'border-gray-200'}`}
            >
              <label className="flex items-start gap-3 p-3 cursor-pointer">
                <input
                  type="radio"
                  name="network-mode"
                  checked={active}
                  onChange={() => onModeChange(entry.key)}
                  className="mt-0.5 accent-blue-600"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-gray-800">{entry.title}</span>
                    <button
                      type="button"
                      onClick={() => setExpanded(isExpanded ? null : entry.key)}
                      className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 shrink-0"
                    >
                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      {isExpanded ? 'Свернуть' : 'Подробнее'}
                    </button>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{entry.short}</p>
                  {isExpanded && (
                    <p className="text-xs text-gray-600 mt-2 bg-white rounded-lg px-3 py-2 border border-gray-100">
                      {entry.detail}
                    </p>
                  )}
                </div>
              </label>
            </div>
          )
        })}
      </div>

      {mode === 'custom_proxy' && (
        <div className="mt-4 space-y-3 border-t border-gray-100 pt-4">
          <p className="text-xs text-blue-600 bg-blue-50 rounded-lg px-3 py-2">
            <b>Что куда вводить:</b> Тип — протокол (SOCKS5/HTTP/MTProto). Хост — локальный адрес,
            обычно <span className="font-mono">127.0.0.1</span> (не IP VPN-сервера). Порт — локальный
            порт из настроек вашего клиента (напр. <span className="font-mono">10808</span> у v2rayN,
            <span className="font-mono"> 7890</span> у Clash). Логин/пароль — только если прокси
            требует авторизацию. Secret — только для MTProto.
          </p>
          <div>
            <label htmlFor="proxy-type" className="block text-sm font-medium text-gray-700 mb-1">Тип</label>
            <select
              id="proxy-type"
              value={fields.type}
              onChange={e => onFieldsChange('type', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="socks5">SOCKS5</option>
              <option value="mtproto">MTProto</option>
              <option value="http">HTTP</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="proxy-host" className="block text-sm font-medium text-gray-700 mb-1">Хост</label>
              <input
                id="proxy-host"
                type="text"
                value={fields.host}
                onChange={e => onFieldsChange('host', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                placeholder="127.0.0.1"
                autoComplete="off"
              />
            </div>
            <div>
              <label htmlFor="proxy-port" className="block text-sm font-medium text-gray-700 mb-1">Порт</label>
              <input
                id="proxy-port"
                type="number"
                value={fields.port}
                onChange={e => onFieldsChange('port', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                placeholder="10808"
                autoComplete="off"
              />
            </div>
          </div>
          {fields.type === 'mtproto' ? (
            <div>
              <label htmlFor="proxy-secret" className="block text-sm font-medium text-gray-700 mb-1">Secret</label>
              <input
                id="proxy-secret"
                type="text"
                value={fields.secret}
                onChange={e => onFieldsChange('secret', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                placeholder="Секретный ключ MTProto-прокси"
                autoComplete="off"
              />
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="proxy-user" className="block text-sm font-medium text-gray-700 mb-1">Логин</label>
                <input
                  id="proxy-user"
                  type="text"
                  value={fields.username}
                  onChange={e => onFieldsChange('username', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  placeholder="(опционально)"
                  autoComplete="off"
                />
              </div>
              <div>
                <label htmlFor="proxy-pass" className="block text-sm font-medium text-gray-700 mb-1">Пароль</label>
                <input
                  id="proxy-pass"
                  type="password"
                  value={fields.password}
                  onChange={e => onFieldsChange('password', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  placeholder="(опционально)"
                  autoComplete="new-password"
                />
              </div>
            </div>
          )}
        </div>
      )}

      <div className="border-t border-gray-100 pt-3">
        <button
          type="button"
          onClick={() => setHelpOpen(!helpOpen)}
          className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-600 transition-colors"
        >
          <HelpCircle className="w-4 h-4" />
          Я не знаю, что у меня за сервис
        </button>
        {helpOpen && (
          <div className="mt-3 space-y-3">
            <p className="text-xs text-gray-400">
              Введите название вашего VPN или прокси-приложения — BiziBox подскажет, что выбрать и что вводить.
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                value={helpQuery}
                onChange={e => setHelpQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && runHelp()}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
                placeholder="Например: v2rayN, Happ, Clash…"
                autoComplete="off"
              />
              <button
                type="button"
                onClick={runHelp}
                disabled={helpLoading || !helpQuery.trim()}
                className="flex items-center gap-1 px-3 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                <Search className="w-4 h-4" />
                {helpLoading ? 'Ищем…' : 'Найти'}
              </button>
            </div>
            {helpError && <p className="text-xs text-red-600">{helpError}</p>}
            {helpResult?.found && (
              <div className="bg-gray-50 rounded-lg px-3 py-2 space-y-1.5 text-sm">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-800">{helpResult.name}</span>
                  {helpResult.category && helpResult.category !== 'unknown' && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
                      {CATEGORY_LABELS[helpResult.category]}
                    </span>
                  )}
                </div>
                {helpResult.description && <p className="text-xs text-gray-600">{helpResult.description}</p>}
                {helpResult.default_port && (
                  <p className="text-xs text-gray-500">
                    Локальный порт обычно: <span className="font-mono">{helpResult.default_port}</span>
                  </p>
                )}
                {helpResult.advice && <p className="text-xs text-gray-700 font-medium">{helpResult.advice}</p>}
              </div>
            )}
            {helpResult && !helpResult.found && helpResult.message && (
              <p className="text-xs text-gray-500">{helpResult.message}</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
