import { ShieldAlert } from 'lucide-react'
import { contactApi } from '../../api/client'
import { useQueryClient } from '@tanstack/react-query'
import type { Contact } from '../../types/contact'
import type { Message } from '../../types/message'

interface MessageToolbarProps {
  message: Message
  contact: Contact | null
  onContactUpdate?: (contact: Contact) => void
}

export default function MessageToolbar({ message, contact, onContactUpdate }: MessageToolbarProps) {
  const isSpam = contact?.life_sphere === 'spam'
  const queryClient = useQueryClient()
  return (
    <div className="shrink-0 px-4 py-2.5 bg-gray-50 border-t border-gray-100">
      <div className="flex items-center gap-2 text-sm">
        <button
          type="button"
          onClick={() => {
            const next = !isSpam
            contactApi.setSpam(message.contact_id, next)
              .then(c => {
                if (onContactUpdate) onContactUpdate(c)
                queryClient.invalidateQueries({ queryKey: ['messages'] })
                queryClient.invalidateQueries({ queryKey: ['threads'] })
                queryClient.invalidateQueries({ queryKey: ['contacts'] })
                queryClient.invalidateQueries({ queryKey: ['contact', c.id] })
              })
              .catch(() => {})
          }}
          className={`inline-flex items-center gap-1 text-xs font-medium ${
            isSpam ? 'text-red-600 hover:text-red-700' : 'text-gray-500 hover:text-gray-700'
          }`}
          title={isSpam ? 'Убрать из спама' : 'Пометить как спам'}
        >
          <ShieldAlert className="w-3 h-3" />
          {isSpam ? 'Не спам' : 'Спам'}
        </button>
      </div>
    </div>
  )
}
