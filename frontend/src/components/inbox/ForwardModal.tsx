import { useEffect, useState } from 'react'
import { Forward } from 'lucide-react'
import Modal from '../common/Modal'
import Button from '../common/Button'
import ContactCombobox from '../contacts/ContactCombobox'
import { useContactsQuery } from '../../hooks/queries'
import { forwardMessage } from '../../api/messages'
import type { Message } from '../../types/message'

interface ForwardModalProps {
  open: boolean
  message: Message | null
  onClose: () => void
  onSent?: () => void
}

export default function ForwardModal({ open, message, onClose, onSent }: ForwardModalProps) {
  const [contactId, setContactId] = useState<number | null>(null)
  const [content, setContent] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const contactsQuery = useContactsQuery()
  const contacts = contactsQuery.data ?? []

  useEffect(() => {
    if (open && message) {
      setContactId(null)
      setContent(message.content)
      setError(null)
      setSending(false)
    }
  }, [open, message])

  const handleSend = async () => {
    if (!message || !contactId || !content.trim() || sending) return
    setSending(true)
    setError(null)
    try {
      await forwardMessage({
        message_id: message.id,
        target_contact_id: contactId,
        content: content.trim(),
      })
      onSent?.()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка пересылки')
    } finally {
      setSending(false)
    }
  }

  if (!message) return null

  return (
    <Modal open={open} onClose={onClose} title="Переслать сообщение" maxWidth="max-w-md">
      <div className="p-5 space-y-4">
        <ContactCombobox
          id="forward-contact"
          label="Кому"
          contacts={contacts}
          value={contactId}
          onChange={setContactId}
          placeholder="Поиск контакта..."
          excludeIds={[message.contact_id]}
        />
        <div>
          <span className="block text-xs font-medium text-gray-500 mb-1.5">Текст</span>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={4}
            className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary resize-none"
          />
        </div>
        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">{error}</p>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>Отмена</Button>
          <Button onClick={handleSend} disabled={!contactId || !content.trim() || sending}>
            <Forward className="w-4 h-4 mr-1" />
            {sending ? 'Отправка...' : 'Переслать'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
