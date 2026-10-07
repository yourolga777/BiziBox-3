import { useEffect, useState } from 'react'
import { Clock, Download, Plug, PlugZap, RefreshCw, Trash2 } from 'lucide-react'
import type { Channel, ChannelHealth } from '../../types/channel'
import Button from '../common/Button'
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
  const [health, setHealth] = useState<ChannelHealth | null>(null)
  const [checking, setChecking] = useState(false)
  const [downloading, setDownloading] = useState(false)

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
