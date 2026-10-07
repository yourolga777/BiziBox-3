import { useEffect, useMemo, useRef, useState } from 'react'
import { Search, X } from 'lucide-react'
import type { Contact } from '../../types/contact'
import { displayName } from '../../utils/contactDisplayName'

interface ContactComboboxProps {
  contacts: Contact[]
  value: number | null
  onChange: (id: number | null) => void
  placeholder?: string
  id?: string
  label?: string
  excludeIds?: number[]
}

function matchesQuery(contact: Contact, query: string): boolean {
  const q = query.trim().toLowerCase()
  if (!q) return true
  const haystack = [
    contact.name,
    contact.phone,
    contact.email,
    contact.telegram_username,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
  return haystack.includes(q)
}

export default function ContactCombobox({
  contacts,
  value,
  onChange,
  placeholder = 'Поиск контакта...',
  id,
  label,
  excludeIds,
}: ContactComboboxProps) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  const selected = useMemo(
    () => contacts.find((c) => c.id === value) ?? null,
    [contacts, value],
  )

  const filtered = useMemo(() => {
    const excluded = new Set(excludeIds ?? [])
    return contacts
      .filter((c) => !excluded.has(c.id))
      .filter((c) => matchesQuery(c, query))
      .slice(0, 50)
  }, [contacts, query, excludeIds])

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  const clear = () => {
    onChange(null)
    setQuery('')
    setOpen(false)
  }

  return (
    <div ref={rootRef} className="relative">
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
          {label}
        </label>
      )}
      {selected ? (
        <div className="flex items-center justify-between gap-2 px-3 py-2 rounded-xl border border-gray-200 text-sm bg-gray-50">
          <span className="truncate text-gray-800">{displayName(selected)}</span>
          <button
            type="button"
            onClick={clear}
            className="shrink-0 text-gray-400 hover:text-red-500 transition-colors"
            title="Сбросить"
            aria-label="Сбросить выбор"
          >
            <X size={16} />
          </button>
        </div>
      ) : (
        <>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              id={id}
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value)
                setOpen(true)
              }}
              onFocus={() => setOpen(true)}
              placeholder={placeholder}
              className="w-full pl-9 pr-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>
          {open && (
            <ul className="absolute z-20 mt-1 w-full max-h-56 overflow-y-auto rounded-xl border border-gray-200 bg-white shadow-lg">
              {filtered.length === 0 ? (
                <li className="px-3 py-2 text-sm text-gray-400">Ничего не найдено</li>
              ) : (
                filtered.map((c) => (
                  <li key={c.id}>
                    <button
                      type="button"
                      onClick={() => {
                        onChange(c.id)
                        setQuery('')
                        setOpen(false)
                      }}
                      className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center justify-between gap-2"
                    >
                      <span className="truncate">{displayName(c)}</span>
                      {c.phone && <span className="text-xs text-gray-400 shrink-0">{c.phone}</span>}
                    </button>
                  </li>
                ))
              )}
            </ul>
          )}
        </>
      )}
    </div>
  )
}
