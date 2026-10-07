import { useEffect, useRef, useState } from 'react'
import { Dialog } from '@headlessui/react'
import { calendarApi } from '../../api/calendar'
import { useContactsQuery } from '../../hooks/queries'
import ContactCombobox from '../contacts/ContactCombobox'
import type { Contact } from '../../types/contact'

interface CalendarModalProps {
  isOpen: boolean
  onClose: () => void
  date: Date | null
  onCreated: () => void
  initialContactId?: number | null
}

function toDateInput(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function CalendarModal({ isOpen, onClose, date, onCreated, initialContactId }: CalendarModalProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [dateValue, setDateValue] = useState('')
  const [time, setTime] = useState('')
  const [reminder, setReminder] = useState<number | ''>('')
  const [recurrence, setRecurrence] = useState<string>('')
  const [contactId, setContactId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const prevOpen = useRef(false)

  const contactsQuery = useContactsQuery()
  const contacts = contactsQuery.data ?? []

  useEffect(() => {
    if (isOpen && !prevOpen.current) {
      setTitle('')
      setDescription('')
      setDateValue(date ? toDateInput(date) : '')
      setTime('')
      setReminder('')
      setRecurrence('')
      setContactId(initialContactId ?? null)
      setError(null)
    }
    prevOpen.current = isOpen
  }, [isOpen, date, initialContactId])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    if (!dateValue) {
      setError('Укажите дату события')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await calendarApi.createEvent({
        title: title.trim(),
        description: description.trim() || undefined,
        date: dateValue,
        time: time || undefined,
        reminder_minutes: reminder === '' ? undefined : reminder,
        recurrence: recurrence || undefined,
        contact_id: contactId || undefined,
      })
      onCreated()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать событие')
    } finally {
      setSaving(false)
    }
  }

  const contactOptions = contacts as Contact[]

  return (
    <Dialog open={isOpen} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="w-full max-w-md bg-white rounded-xl p-6">
          <Dialog.Title className="text-lg font-semibold mb-4">
            Новое событие {date ? `на ${date.toLocaleDateString('ru-RU')}` : ''}
          </Dialog.Title>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="event-title" className="block text-sm font-medium text-gray-700 mb-1">Заголовок *</label>
              <input
                id="event-title"
                type="text" value={title} onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                placeholder="Название события"
              />
            </div>
            <div>
              <label htmlFor="event-date" className="block text-sm font-medium text-gray-700 mb-1">Дата *</label>
              <input
                id="event-date"
                type="date" value={dateValue} onChange={(e) => setDateValue(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>
            <div>
              <label htmlFor="event-time" className="block text-sm font-medium text-gray-700 mb-1">Время</label>
              <input
                id="event-time"
                type="time" value={time} onChange={(e) => setTime(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>
            <div>
              <label htmlFor="event-description" className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
              <textarea
                id="event-description"
                value={description} onChange={(e) => setDescription(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none"
                rows={3}
                placeholder="Дополнительные детали..."
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="event-reminder" className="block text-sm font-medium text-gray-700 mb-1">Напоминание</label>
                <select
                  id="event-reminder"
                  value={reminder} onChange={(e) => setReminder(e.target.value === '' ? '' : Number(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
                >
                  <option value="">Без напоминания</option>
                  <option value="0">В срок</option>
                  <option value="15">За 15 минут</option>
                  <option value="30">За 30 минут</option>
                  <option value="60">За час</option>
                  <option value="1440">За день</option>
                </select>
              </div>
              <div>
                <label htmlFor="event-recurrence" className="block text-sm font-medium text-gray-700 mb-1">Повторение</label>
                <select
                  id="event-recurrence"
                  value={recurrence} onChange={(e) => setRecurrence(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
                >
                  <option value="">Не повторяется</option>
                  <option value="daily">Ежедневно</option>
                  <option value="weekly">Еженедельно</option>
                  <option value="monthly">Ежемесячно</option>
                </select>
              </div>
            </div>
            <div>
              <ContactCombobox
                id="event-contact"
                label="Контакт"
                contacts={contactOptions}
                value={contactId}
                onChange={setContactId}
                placeholder="Поиск контакта..."
              />
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={onClose} className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
                Отмена
              </button>
              <button type="submit" disabled={saving || !title.trim()} className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {saving ? 'Создание...' : 'Создать'}
              </button>
            </div>
          </form>
        </Dialog.Panel>
      </div>
    </Dialog>
  )
}
