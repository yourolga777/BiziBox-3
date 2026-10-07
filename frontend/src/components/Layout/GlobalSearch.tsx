import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, X, MessageSquare, User } from 'lucide-react'
import { messageApi, contactApi } from '../../api/client'
import { displayNameShort } from '../../utils/contactDisplayName'
import type { Message } from '../../types/message'
import type { Contact } from '../../types/contact'

interface Props {
  open: boolean
  onClose: () => void
}

export default function GlobalSearch({ open, onClose }: Props) {
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [contacts, setContacts] = useState<Contact[]>([])
  const [loading, setLoading] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (open) {
      setQuery('')
      setMessages([])
      setContacts([])
      setLoading(false)
      setTimeout(() => inputRef.current?.focus(), 0)
    }
  }, [open])

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    const q = query.trim()
    if (!q) {
      setMessages([])
      setContacts([])
      setLoading(false)
      return
    }
    setLoading(true)
    debounceRef.current = setTimeout(async () => {
      try {
        const [msgs, cts] = await Promise.all([
          messageApi.search(q, 10),
          contactApi.search(q, 10),
        ])
        setMessages(msgs)
        setContacts(cts)
      } catch {
        setMessages([])
        setContacts([])
      } finally {
        setLoading(false)
      }
    }, 250)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [query])

  const goToMessage = (m: Message) => {
    onClose()
    navigate(`/inbox?contact_id=${m.contact_id}`)
  }

  const goToContact = (c: Contact) => {
    onClose()
    navigate(`/contacts?contact_id=${c.id}`)
  }

  if (!open) return null

  const hasResults = messages.length > 0 || contacts.length > 0

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh]">
      <div className="absolute inset-0 bg-black/40" role="button" tabIndex={0} onClick={onClose} onKeyDown={(e) => e.key === 'Enter' && onClose()} />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4">
        <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-200">
          <Search className="w-4 h-4 text-gray-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Поиск по сообщениям и контактам..."
            className="flex-1 text-sm outline-none"
          />
          {loading && <span className="text-xs text-gray-400">Поиск...</span>}
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600" title="Закрыть">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="max-h-[55vh] overflow-y-auto py-2">
          {!hasResults && !loading && query.trim() && (
            <p className="px-4 py-3 text-sm text-gray-400">Ничего не найдено</p>
          )}
          {!query.trim() && (
            <p className="px-4 py-3 text-sm text-gray-400">Введите запрос для поиска</p>
          )}

          {contacts.length > 0 && (
            <div>
              <p className="px-4 pt-2 pb-1 text-xs uppercase tracking-wide text-gray-400">Контакты</p>
              {contacts.map((c) => (
                <button
                  key={c.id}
                  onClick={() => goToContact(c)}
                  className="w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-gray-50"
                >
                  <User className="w-4 h-4 text-gray-400 shrink-0" />
                  <span className="text-sm text-gray-800 truncate">{displayNameShort(c)}</span>
                  {c.phone && <span className="text-xs text-gray-400 shrink-0">{c.phone}</span>}
                </button>
              ))}
            </div>
          )}

          {messages.length > 0 && (
            <div>
              <p className="px-4 pt-2 pb-1 text-xs uppercase tracking-wide text-gray-400">Сообщения</p>
              {messages.map((m) => (
                <button
                  key={m.id}
                  onClick={() => goToMessage(m)}
                  className="w-full flex items-start gap-3 px-4 py-2 text-left hover:bg-gray-50"
                >
                  <MessageSquare className="w-4 h-4 text-gray-400 shrink-0 mt-0.5" />
                  <span className="text-sm text-gray-800 truncate min-w-0">{m.content}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
