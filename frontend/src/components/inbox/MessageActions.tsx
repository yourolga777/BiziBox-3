import { useState } from 'react'
import { CheckCircle, Clock, Copy, CalendarPlus, PackagePlus } from 'lucide-react'
import { messageApi } from '../../api/client'
import { useToast } from '../common/Toast'
import { useContactsQuery } from '../../hooks/queries'
import { useCreateOrderMutation } from '../../hooks/orders'
import TaskForm from './TaskForm'
import QuickOrderModal from './QuickOrderModal'
import { CalendarModal } from '../calendar/CalendarModal'
import type { Message } from '../../types/message'

interface MessageActionsProps {
  message: Message
  contactName: string | null
  isAnonymous: boolean
  onActionComplete: () => void
}

const SNOOZE_OPTIONS: { label: string; hours: number }[] = [
  { label: '1 час', hours: 1 },
  { label: 'До вечера', hours: 4 },
  { label: 'До завтра', hours: 24 },
]

function MessageActions({ message, contactName, isAnonymous, onActionComplete }: MessageActionsProps) {
  const [expanded, setExpanded] = useState(false)
  const [snoozeOpen, setSnoozeOpen] = useState(false)
  const [eventModalOpen, setEventModalOpen] = useState(false)
  const [orderModalOpen, setOrderModalOpen] = useState(false)
  const { showToast } = useToast()
  const contactsQuery = useContactsQuery()
  const createOrder = useCreateOrderMutation()

  const handleSnooze = async (hours: number) => {
    const until = new Date(Date.now() + hours * 60 * 60 * 1000).toISOString()
    try {
      await messageApi.snooze(message.id, until)
      showToast('Сообщение отложено', 'success')
      setSnoozeOpen(false)
      onActionComplete()
    } catch {
      showToast('Не удалось отложить', 'error')
    }
  }

  const handleCopyCode = async () => {
    if (!message.extracted_code) return
    try {
      await navigator.clipboard.writeText(message.extracted_code)
      showToast('Код скопирован', 'success')
    } catch {
      showToast('Не удалось скопировать', 'error')
    }
  }

  if (isAnonymous) {
    return (
      <div className="shrink-0 px-4 pb-2 space-y-2">
        {message.extracted_code && (
          <button
            type="button"
            onClick={handleCopyCode}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
            title="Скопировать код"
          >
            <Copy className="w-3.5 h-3.5" />
            Код: {message.extracted_code}
          </button>
        )}
        <p className="text-xs text-gray-400 text-center">Заполните данные контакта выше, чтобы создать задачу</p>
      </div>
    )
  }

  return (
    <div className="shrink-0 px-4 pb-2 space-y-2">
      <div className="flex items-center gap-2 flex-wrap">
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-purple-600 bg-purple-50 border border-purple-200 rounded-lg hover:bg-purple-100 transition-colors"
        >
          <CheckCircle className="w-3.5 h-3.5" />
          {expanded ? 'Свернуть' : '+ Задача'}
        </button>

        <button
          type="button"
          onClick={() => setOrderModalOpen(true)}
          className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-orange-600 bg-orange-50 border border-orange-200 rounded-lg hover:bg-orange-100 transition-colors"
        >
          <PackagePlus className="w-3.5 h-3.5" />
          + Заказ
        </button>

        <button
          type="button"
          onClick={() => setEventModalOpen(true)}
          className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition-colors"
        >
          <CalendarPlus className="w-3.5 h-3.5" />
          + Событие
        </button>

        <div className="relative">
          <button
            type="button"
            onClick={() => setSnoozeOpen(!snoozeOpen)}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-lg hover:bg-amber-100 transition-colors"
          >
            <Clock className="w-3.5 h-3.5" />
            Snooze
          </button>
          {snoozeOpen && (
            <div className="absolute left-0 top-full mt-1 bg-white border border-gray-200 rounded-xl shadow-lg z-20 min-w-[140px] p-1">
              {SNOOZE_OPTIONS.map((opt) => (
                <button
                  key={opt.hours}
                  onClick={() => handleSnooze(opt.hours)}
                  className="w-full text-left px-3 py-1.5 rounded-lg text-sm text-gray-700 hover:bg-gray-50"
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {message.extracted_code && (
          <button
            type="button"
            onClick={handleCopyCode}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
            title="Скопировать код"
          >
            <Copy className="w-3.5 h-3.5" />
            Код: {message.extracted_code}
          </button>
        )}
      </div>

      {expanded && (
        <TaskForm
          contactId={message.contact_id}
          contactName={contactName}
          initialTitle={contactName ?? undefined}
          initialDescription={message.content}
          messageId={message.id}
          onTaskCreated={onActionComplete}
          onClose={() => setExpanded(false)}
        />
      )}

      <CalendarModal
        isOpen={eventModalOpen}
        onClose={() => setEventModalOpen(false)}
        date={new Date()}
        initialContactId={message.contact_id}
        onCreated={() => {
          setEventModalOpen(false)
          onActionComplete()
        }}
      />

      <QuickOrderModal
        open={orderModalOpen}
        onClose={() => setOrderModalOpen(false)}
        messageId={message.id}
        contactId={message.contact_id}
        contactName={contactName}
        contacts={contactsQuery.data ?? []}
        onCreate={async (data) => {
          await createOrder.mutateAsync(data)
        }}
        onCreated={() => {
          setOrderModalOpen(false)
          showToast('Заказ создан', 'success')
          onActionComplete()
        }}
      />
    </div>
  )
}

export default MessageActions
