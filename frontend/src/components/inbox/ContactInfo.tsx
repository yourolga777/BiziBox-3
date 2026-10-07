import { EyeOff, Eye, Info, Star, X, ShieldAlert } from 'lucide-react'
import { getChannelIcon } from '../../utils/channelIcons'
import { contactSphereMeta } from '../../types/contactType'
import type { Message } from '../../types/message'
import type { Contact } from '../../types/contact'

export default function ContactInfo({
  message, contactName, contact, contactLoading,
  messageStatus, isFlagged, onMarkUnread, onMarkRead, onToggleFlag, onClose, onOpenCard, onEditContact, onToggleSpam,
}: {
  message: Message
  contactName: string | null
  contact: Contact | null
  contactLoading: boolean
  messageStatus: 'read' | 'unread'
  isFlagged: boolean
  onMarkUnread: () => void
  onMarkRead: () => void
  onToggleFlag?: () => void
  onClose: () => void
  onOpenCard?: () => void
  onEditContact?: () => void
  onToggleSpam?: () => void
}) {
  const Icon = getChannelIcon(message.channel)
  const typeMeta = contactSphereMeta(contact?.life_sphere)
  const isSpam = contact?.life_sphere === 'spam'

  return (
    <div className="flex items-start justify-between p-4 border-b shrink-0 bg-white border-gray-200">
      <div className="flex items-start gap-3">
        <div className="p-2 bg-gray-100 rounded-lg mt-0.5">
          <Icon className="w-5 h-5 text-gray-600" />
        </div>
        <div>
          <div className="flex items-center gap-1.5 flex-wrap">
            {onEditContact ? (
              <div
                className="text-lg font-semibold cursor-pointer hover:text-blue-600"
                onClick={onEditContact}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onEditContact() }}
                role="button"
                tabIndex={0}
                title="Редактировать контакт"
              >
                {contactName || `Контакт #${message.contact_id}`}
              </div>
            ) : (
              <h3 className="text-lg font-semibold text-gray-900">
                {contactName || `Контакт #${message.contact_id}`}
              </h3>
            )}
            {contact && (
              <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium ${typeMeta.bg} ${typeMeta.color}`}>
                {typeMeta.label}
              </span>
            )}
          </div>
          {contactLoading ? (
            <p className="text-xs text-gray-400">Загрузка...</p>
          ) : contact ? (
            <div className="text-xs text-gray-500 space-y-0.5 mt-1">
              {contact.phone && <p>📞 {contact.phone}</p>}
              {contact.email && <p>✉ {contact.email}</p>}
              {contact.telegram_username && <p>✈ @{contact.telegram_username.replace(/^@/, '')}</p>}
              {contact.telegram_id && !contact.telegram_username && <p>✈ ID: {contact.telegram_id}</p>}
              <p className="capitalize text-gray-400">{message.channel}</p>
            </div>
          ) : null}
        </div>
      </div>
      <div className="flex items-center gap-1 shrink-0">
        {onToggleSpam && (
          <button
            onClick={onToggleSpam}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
            title={isSpam ? 'Убрать из спама' : 'Пометить как спам'}
          >
            <ShieldAlert className={`w-4 h-4 ${isSpam ? 'text-red-500' : 'text-gray-400'}`} />
          </button>
        )}
        {onOpenCard && (
          <button
            onClick={onOpenCard}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
            title="Карточка контакта"
          >
            <Info className="w-4 h-4 text-gray-400" />
          </button>
        )}
        {onToggleFlag && (
          <button
            onClick={onToggleFlag}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
            title={isFlagged ? 'Снять флаг' : 'Пометить флагом'}
          >
            <Star className={`w-4 h-4 ${isFlagged ? 'fill-amber-400 text-amber-400' : 'text-gray-400'}`} />
          </button>
        )}
        <button
          onClick={messageStatus === 'read' ? onMarkUnread : onMarkRead}
          className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          title={messageStatus === 'read' ? 'Пометить как непрочитанное' : 'Пометить как прочитанное'}
        >
          {messageStatus === 'read' ? (
            <EyeOff className="w-4 h-4 text-gray-400" />
          ) : (
            <Eye className="w-4 h-4 text-gray-400" />
          )}
        </button>
        <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg transition-colors">
          <X className="w-5 h-5 text-gray-500" />
        </button>
      </div>
    </div>
  )
}
