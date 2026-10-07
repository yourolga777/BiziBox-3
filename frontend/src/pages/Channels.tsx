import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Wifi } from 'lucide-react'
import Card from '../components/common/Card'
import ChannelCard from '../components/channels/ChannelCard'
import TelegramConnect from '../components/channels/TelegramConnect'
import EmailConnect from '../components/channels/EmailConnect'
import VkConnect from '../components/channels/VkConnect'
import Button from '../components/common/Button'
import { useToast } from '../components/common/Toast'
import { channelApi } from '../api/client'
import type { Channel } from '../types/channel'

function Channels() {
  const queryClient = useQueryClient()
  const [channels, setChannels] = useState<Channel[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reconnectChannel, setReconnectChannel] = useState<Channel | null>(null)
  const [reconnecting, setReconnecting] = useState(false)
  const { showToast } = useToast()

  const loadChannels = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await channelApi.getAll()
      setChannels(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки')
    } finally {
      setLoading(false)
    }
  }

  const refreshChannels = async () => {
    setRefreshing(true)
    setError(null)
    try {
      const data = await channelApi.getAll()
      setChannels(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки')
    } finally {
      setRefreshing(false)
    }
  }

  useEffect(() => {
    loadChannels()
  }, [])

  const handleDelete = async (id: number) => {
    try {
      await channelApi.delete(id)
      setChannels((prev) => prev.filter((ch) => ch.id !== id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка отключения')
    }
  }

  const handleConnected = () => {
    setReconnectChannel(null)
    queryClient.invalidateQueries({ queryKey: ['messages'] })
    queryClient.invalidateQueries({ queryKey: ['contacts'] })
    loadChannels()
  }

  const handleReconnect = (channel: Channel) => {
    setReconnectChannel(channel)
  }

  const handleDownload = async (type: string) => {
    try {
      const result = await channelApi.download(type)
      showToast(`Загружено ${result.new_messages} новых сообщений`, 'success')
      queryClient.invalidateQueries({ queryKey: ['messages'] })
      queryClient.invalidateQueries({ queryKey: ['contacts'] })
      await loadChannels()
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Ошибка загрузки', 'error')
    }
  }

  const handleReconnectStored = async () => {
    setReconnecting(true)
    setError(null)
    try {
      await channelApi.reconnectEmailStored()
      showToast('Email переподключён', 'success')
      setReconnectChannel(null)
      await loadChannels()
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Ошибка переподключения', 'error')
      setError(err instanceof Error ? err.message : 'Ошибка переподключения')
    } finally {
      setReconnecting(false)
    }
  }

  const handleReconnectVkStored = async () => {
    setReconnecting(true)
    setError(null)
    try {
      await channelApi.reconnectVkStored()
      showToast('ВКонтакте переподключён', 'success')
      setReconnectChannel(null)
      await loadChannels()
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Ошибка переподключения', 'error')
      setError(err instanceof Error ? err.message : 'Ошибка переподключения')
    } finally {
      setReconnecting(false)
    }
  }

  const telegramChannel = channels.find((ch) => ch.type === 'telegram')
  const emailChannel = channels.find((ch) => ch.type === 'email')
  const vkChannel = channels.find((ch) => ch.type === 'vk')

  const hasTelegram = telegramChannel?.is_connected ?? false
  const hasEmail = emailChannel?.is_connected ?? false
  const hasVk = vkChannel?.is_connected ?? false

  if (loading) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold text-gray-900">Каналы</h2>
        <div className="flex items-center justify-center py-20">
          <RefreshCw className="w-8 h-8 text-primary animate-spin" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-gray-900">Каналы</h2>
        <Button variant="ghost" size="sm" onClick={refreshChannels} disabled={refreshing}>
          <RefreshCw className={`w-4 h-4 mr-1 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? 'Загружается...' : 'Обновить'}
        </Button>
      </div>

      {error && (
        <Card>
          <p className="text-red-500 text-sm">{error}</p>
        </Card>
      )}

      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-700">Подключённые каналы</h3>
        {channels.length === 0 ? (
          <Card>
            <p className="text-gray-500 text-center py-4">Нет подключённых каналов</p>
          </Card>
        ) : (
          channels.map((ch) => (
            <ChannelCard
              key={ch.id}
              channel={ch}
              onDelete={handleDelete}
              onReconnect={handleReconnect}
              onDownload={handleDownload}
            />
          ))
        )}
      </div>

      {reconnectChannel?.type === 'email' && (
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-700">Переподключение Email</h3>
          {!reconnecting && (
            <Button
              variant="primary"
              size="sm"
              onClick={handleReconnectStored}
              className="mb-3"
            >
              <Wifi className="w-4 h-4 mr-1" />
              Подключить заново (сохранённый пароль)
            </Button>
          )}
          {reconnecting && (
            <Card>
              <div className="flex items-center gap-2 py-2 text-gray-500">
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Переподключение...</span>
              </div>
            </Card>
          )}
          {error && (
            <Card>
              <p className="text-sm text-red-600">{error}</p>
            </Card>
          )}
          <p className="text-xs text-gray-400">Если сохранённый пароль не подходит, введите новый ниже:</p>
          <EmailConnect
            onConnected={handleConnected}
            initialEmail={reconnectChannel.name}
          />
        </div>
      )}

      {reconnectChannel?.type === 'vk' && (
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-700">Переподключение ВКонтакте</h3>
          {!reconnecting && (
            <Button
              variant="primary"
              size="sm"
              onClick={handleReconnectVkStored}
              className="mb-3"
            >
              <Wifi className="w-4 h-4 mr-1" />
              Подключить заново (сохранённый токен)
            </Button>
          )}
          {reconnecting && (
            <Card>
              <div className="flex items-center gap-2 py-2 text-gray-500">
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Переподключение...</span>
              </div>
            </Card>
          )}
          {error && (
            <Card>
              <p className="text-sm text-red-600">{error}</p>
            </Card>
          )}
          <p className="text-xs text-gray-400">Если сохранённый токен не подходит, введите новый ниже:</p>
          <VkConnect onConnected={handleConnected} />
        </div>
      )}

      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-700">Добавить канал</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {!hasTelegram && !reconnectChannel && <TelegramConnect onConnected={handleConnected} />}
          {!hasEmail && !reconnectChannel && <EmailConnect onConnected={handleConnected} />}
          {!hasVk && !reconnectChannel && <VkConnect onConnected={handleConnected} />}
        </div>
        {hasTelegram && hasEmail && hasVk && !reconnectChannel && (
          <Card>
            <p className="text-gray-500 text-center py-4">Все каналы подключены</p>
          </Card>
        )}
      </div>
    </div>
  )
}

export default Channels
