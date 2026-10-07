import { Users } from 'lucide-react'
import { displayName } from '../../utils/contactDisplayName'
import type { Contact } from '../../types/contact'

export default function ContactSearchPopup({
  query, contacts, linking,
  onSearch, onSelect, onClose,
}: {
  query: string
  contacts: Contact[]
  linking: boolean
  onSearch: (q: string) => void
  onSelect: (contactId: number) => void
  onClose: () => void
}) {
  return (
    <div className="border-b border-gray-200 p-4 bg-gray-50 shrink-0">
      <p className="text-sm font-medium text-gray-700 mb-2">Поиск контакта для привязки</p>
      <input
        type="text"
        value={query}
        onChange={e => onSearch(e.target.value)}
        placeholder="Введите имя, телефон или email..."
        className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
        aria-label="Поиск контакта"
      />
      {contacts.length > 0 && (
        <div className="mt-2 max-h-40 overflow-y-auto space-y-1">
          {contacts.map(c => (
            <button
              key={c.id}
              onClick={() => onSelect(c.id)}
              disabled={linking}
              className="w-full text-left px-3 py-2 rounded-lg hover:bg-white text-sm flex items-center gap-2 transition-colors"
            >
              <Users className="w-4 h-4 text-gray-400 shrink-0" />
              <div className="min-w-0">
                <span className="font-medium text-gray-900">{displayName(c)}</span>
                {c.phone && <span className="text-gray-500 ml-2">{c.phone}</span>}
                {c.email && !c.phone && <span className="text-gray-500 ml-2">{c.email}</span>}
              </div>
            </button>
          ))}
        </div>
      )}
      {query && contacts.length === 0 && (
        <p className="text-xs text-gray-400 mt-2">Ничего не найдено</p>
      )}
      <button onClick={onClose} className="text-xs text-gray-400 hover:text-gray-600 mt-2">Отмена</button>
    </div>
  )
}
