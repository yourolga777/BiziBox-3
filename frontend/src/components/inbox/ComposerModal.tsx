import { useEffect, useState } from 'react'
import { Send, MessageSquare, Mail, MessageCircle } from 'lucide-react'
import Modal from '../common/Modal'
import Button from '../common/Button'
import { sendNew } from '../../api/messages'
import { useChannelsQuery, useContactsQuery } from '../../hooks/queries'

type ChannelType = 'telegram' | 'email' | 'vk'

const CHANNELS: { key: ChannelType; label: string; icon: typeof MessageSquare }[] = [
  { key: 'telegram', label: 'Telegram', icon: MessageSquare },
  { key: 'email', label: 'Email', icon: Mail },
  { key: 'vk', label: 'VK', icon: MessageCircle },
]

const RECIPIENT_PLACEHOLDER: Record<ChannelType, string> = {
  telegram: '@username или +79991234567',
  email: 'name@example.com',
  vk: 'ID пользователя VK (число)',
}

interface ComposerModalProps {
  open: boolean
  onClose: () => void
  onSent?: () => void
}

export default function ComposerModal({ open, onClose, onSent }: ComposerModalProps) {
  const [channel, setChannel] = useState<ChannelType>('telegram')
  const [recipient, setRecipient] = useState('')
  const [content, setContent] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const channelsQuery = useChannelsQuery()
  const contactsQuery = useContactsQuery()
  const contacts = contactsQuery.data ?? []

  const connectedSet = new Set<string>()
  for (const ch of channelsQuery.data ?? []) {
    if (ch.is_connected) connectedSet.add(ch.type)
  }

  useEffect(() => {
    if (open) {
      setRecipient('')
      setContent('')
      setError(null)
      setSending(false)
      const first = CHANNELS.find((c) => connectedSet.has(c.key))
      if (first) setChannel(first.key)
    }
  }, [open, channelsQuery.data])

  const sendable = connectedSet.has(channel)

  const handleSend = async () => {
    if (!recipient.trim() || !content.trim() || !sendable || sending) return
    setSending(true)
    setError(null)
    try {
      await sendNew({ channel, recipient: recipient.trim(), content: content.trim() })
      onSent?.()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка отправки')
    } finally {
      setSending(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Написать новое" maxWidth="max-w-md">
      <div className="p-5 space-y-4">
        {connectedSet.size === 0 && (
          <p className="text-sm text-amber-600 bg-amber-50 border border-amber-200 rounded-lg p-3">
            Нет подключённых каналов. Подключите Telegram, Email или VK в разделе Каналы.
          </p>
        )}

        <div>
          <span className="block text-xs font-medium text-gray-500 mb-1.5">Канал</span>
          <div className="flex gap-2">
            {CHANNELS.map((c) => {
              const Icon = c.icon
              return (
                <button
                  key={c.key}
                  type="button"
                  disabled={!connectedSet.has(c.key)}
                  onClick={() => setChannel(c.key)}
                  className={`flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg border text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
                    channel === c.key
                      ? 'bg-primary text-white border-primary'
                      : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {c.label}
                </button>
              )
            })}
          </div>
        </div>

        <div>
          <label htmlFor="composer-recipient" className="block text-xs font-medium text-gray-500 mb-1.5">
            Получатель
          </label>
          <input
            id="composer-recipient"
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
            placeholder={RECIPIENT_PLACEHOLDER[channel]}
            className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors"
          />
          {channel === 'email' && contacts.some((c) => c.email) && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {contacts.filter((c) => c.email).slice(0, 10).map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setRecipient(c.email!)}
                  className="px-2 py-1 text-xs bg-gray-100 rounded-md text-gray-600 hover:bg-gray-200"
                >
                  {c.name || c.email}
                </button>
              ))}
            </div>
          )}
        </div>

        <div>
          <label htmlFor="composer-content" className="block text-xs font-medium text-gray-500 mb-1.5">Текст сообщения</label>
          <textarea
            id="composer-content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={4}
            placeholder="Введите сообщение..."
            className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors resize-none"
          />
        </div>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">{error}</p>
        )}

        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>Отмена</Button>
          <Button onClick={handleSend} disabled={!sendable || sending || !recipient.trim() || !content.trim()}>
            <Send className="w-4 h-4 mr-1" />
            {sending ? 'Отправка...' : 'Отправить'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
