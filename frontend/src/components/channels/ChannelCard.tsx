import { useEffect, useState } from 'react'
import { Clock, Download, Plug, PlugZap, RefreshCw, Trash2 } from 'lucide-react'
import type { Channel, ChannelHealth, ChannelMode } from '../../types/channel'
import { CHANNEL_MODES, CHANNEL_MODE_LABELS } from '../../types/channel'
import Button from '../common/Button'
import { useToast } from '../common/Toast'
import { getChannelIcon } from '../../utils/channelIcons'
import { formatLastPolled } from '../../utils/format'
import { channelApi } from '../../api/client'

interface ChannelCardProps {
  channel: Channel
  onDelete: (id: number) => void
  onReconnect?: (channel: Channel) => void
  onDownload?: (type: string) => void
}

function ChannelCard({ channel, onDelete, onReconnect, onDownload }: ChannelCardProps) {
  const Icon = getChannelIcon(channel.type)
  const isConnected = channel.is_connected
  const { showToast } = useToast()
  const [mode, setMode] = useState<ChannelMode>(channel.mode ?? 'both')
  const [health, setHealth] = useState<ChannelHealth | null>(null)
  const [checking, setChecking] = useState(false)
  const [downloading, setDownloading] = useState(false)

  const handleModeChange = async (newMode: ChannelMode) => {
    if (newMode === mode) return
    const previous = mode
    setMode(newMode)
    try {
      await channelApi.updateMode(channel.id, newMode)
      showToast('Режим канала обновлён', 'success')
    } catch (err) {
      setMode(previous)
      showToast(err instanceof Error ? err.message : 'Ошибка обновления режима', 'error')
    }
  }

  useEffect(() => {
    if (isConnected) {
      setChecking(true)
      channelApi.health(channel.id)
        .then(setHealth)
        .catch(() => setHealth(null))
        .finally(() => setChecking(false))
    }
  }, [channel.id, isConnected])

  const needsReconnect = health?.needs_reconnect ?? false

  const handleDownload = async () => {
    if (downloading) return
    setDownloading(true)
    try {
      if (onDownload) {
        await onDownload(channel.type)
      } else {
        await channelApi.download(channel.type)
      }
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="p-4 rounded-xl border border-gray-200 bg-white hover:shadow-md transition-shadow">
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-lg ${
          needsReconnect ? 'bg-amber-50' : isConnected ? 'bg-green-50' : 'bg-gray-50'
        }`}>
          <Icon className={`w-6 h-6 ${
            needsReconnect ? 'text-amber-600' : isConnected ? 'text-green-600' : 'text-gray-400'
          }`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-gray-900 capitalize">{channel.name}</h3>
            <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${
              needsReconnect
                ? 'bg-amber-100 text-amber-700'
                : isConnected
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-500'
            }`}>
              {checking ? (
                <RefreshCw className="w-3 h-3 animate-spin" />
              ) : needsReconnect ? (
                <RefreshCw className="w-3 h-3" />
              ) : isConnected ? (
                <PlugZap className="w-3 h-3" />
              ) : (
                <Plug className="w-3 h-3" />
              )}
              {checking ? 'Проверка...' : needsReconnect ? 'Требуется подключение' : isConnected ? 'Подключён' : 'Отключён'}
            </span>
          </div>
          <p className="text-sm text-gray-500 capitalize mt-0.5">{channel.type}</p>
          <div className="flex items-center gap-2 mt-2">
            <span className="text-xs text-gray-400 shrink-0">Режим:</span>
            <select
              value={mode}
              onChange={(e) => handleModeChange(e.target.value as ChannelMode)}
              aria-label="Режим работы канала"
              className="text-xs border border-gray-200 rounded-md px-1.5 py-0.5 bg-white text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-400"
            >
              {CHANNEL_MODES.map((m) => (
                <option key={m} value={m}>{CHANNEL_MODE_LABELS[m]}</option>
              ))}
            </select>
          </div>
          {isConnected && (
            <div className="flex items-center gap-2 mt-1.5">
              <Clock className="w-3 h-3 text-gray-400" />
              <span className="text-xs text-gray-400">{formatLastPolled(channel.last_polled_at)}</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isConnected && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDownload}
              disabled={downloading}
              className="text-blue-600 hover:text-blue-700 hover:bg-blue-50"
              title="Загрузить сообщения"
            >
              <Download className={`w-4 h-4 ${downloading ? 'animate-bounce' : ''}`} />
            </Button>
          )}
          {needsReconnect && onReconnect && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onReconnect(channel)}
              className="text-amber-600 hover:text-amber-700 hover:bg-amber-50"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(channel.id)}
            className="text-red-500 hover:text-red-700 hover:bg-red-50"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

export default ChannelCard
