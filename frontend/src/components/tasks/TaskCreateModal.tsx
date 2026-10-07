import { useEffect, useState } from 'react'
import Button from '../common/Button'
import Modal from '../common/Modal'
import ContactCombobox from '../contacts/ContactCombobox'
import { useContactsQuery, useCreateTaskMutation } from '../../hooks/queries'

function toDateInputValue(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function defaultRepeatUntil(recurrence: string): string {
  const d = new Date()
  if (recurrence === 'daily') d.setMonth(d.getMonth() + 1)
  else if (recurrence === 'weekly') d.setMonth(d.getMonth() + 3)
  else if (recurrence === 'monthly') d.setFullYear(d.getFullYear() + 1)
  return toDateInputValue(d)
}

interface TaskCreateModalProps {
  open: boolean
  onClose: () => void
  initialContactId?: number | null
  initialDate?: string | null
  initialTitle?: string
  initialDescription?: string
  onCreated?: () => void
}

export default function TaskCreateModal({
  open,
  onClose,
  initialContactId,
  initialDate,
  initialTitle,
  initialDescription,
  onCreated,
}: TaskCreateModalProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [reminder, setReminder] = useState<number | ''>('')
  const [recurrence, setRecurrence] = useState('')
  const [repeatUntil, setRepeatUntil] = useState('')
  const [repeatDates, setRepeatDates] = useState<string[]>([])
  const [repeatDateInput, setRepeatDateInput] = useState('')
  const [contactId, setContactId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)

  const createTask = useCreateTaskMutation()
  const contactsQuery = useContactsQuery()
  const contacts = contactsQuery.data ?? []

  useEffect(() => {
    if (open) {
      setTitle(initialTitle ?? '')
      setDescription(initialDescription ?? '')
      setDueDate(initialDate ?? '')
      setReminder('')
      setRecurrence('')
      setRepeatUntil('')
      setRepeatDates([])
      setRepeatDateInput('')
      setContactId(initialContactId ?? null)
    }
  }, [open, initialContactId, initialDate, initialTitle, initialDescription])

  const handleRecurrenceChange = (value: string) => {
    setRecurrence(value)
    if (value === 'daily' || value === 'weekly' || value === 'monthly') {
      setRepeatUntil(defaultRepeatUntil(value))
    } else {
      setRepeatUntil('')
    }
  }

  const addRepeatDate = () => {
    if (repeatDateInput && !repeatDates.includes(repeatDateInput)) {
      setRepeatDates(prev => [...prev, repeatDateInput].sort())
    }
    setRepeatDateInput('')
  }

  const handleCreate = async () => {
    if (!title.trim()) return
    setSaving(true)
    try {
      await createTask.mutateAsync({
        title: title.trim(),
        description: description.trim() || undefined,
        due_date: dueDate || undefined,
        reminder_minutes: reminder === '' ? undefined : reminder,
        recurrence: recurrence === 'custom' ? undefined : recurrence || undefined,
        repeat_dates: recurrence === 'custom' ? repeatDates : undefined,
        repeat_until: recurrence && recurrence !== 'custom' ? repeatUntil || undefined : undefined,
        contact_id: contactId ?? undefined,
        status: 'new',
      })
      onCreated?.()
      onClose()
    } catch {
      // mutation handles error state internally
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Новая задача" maxWidth="max-w-md">
      <div className="p-6 space-y-4">
        <div>
          <label htmlFor="task-modal-title" className="block text-sm font-medium text-gray-700 mb-1">Заголовок *</label>
          <input
            id="task-modal-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            placeholder="Купить офисные стулья"
          />
        </div>

        <div>
          <label htmlFor="task-modal-description" className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
          <textarea
            id="task-modal-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary resize-none"
            rows={3}
            placeholder="Дополнительные детали..."
          />
        </div>

        <div>
          <label htmlFor="task-modal-deadline" className="block text-sm font-medium text-gray-700 mb-1">Дедлайн</label>
          <input
            id="task-modal-deadline"
            type="datetime-local"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
          />
        </div>

        <div>
          <label htmlFor="task-modal-reminder" className="block text-sm font-medium text-gray-700 mb-1">Напоминание</label>
          <select
            id="task-modal-reminder"
            value={reminder}
            onChange={(e) => setReminder(e.target.value === '' ? '' : Number(e.target.value))}
            className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary bg-white"
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
          <label htmlFor="task-modal-recurrence" className="block text-sm font-medium text-gray-700 mb-1">Повтор</label>
          <select
            id="task-modal-recurrence"
            value={recurrence}
            onChange={(e) => handleRecurrenceChange(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary bg-white"
          >
            <option value="">Не повторяется</option>
            <option value="daily">Ежедневно</option>
            <option value="weekly">Еженедельно</option>
            <option value="monthly">Ежемесячно</option>
            <option value="custom">По конкретным датам</option>
          </select>
          {recurrence && recurrence !== 'custom' && !dueDate && (
            <p className="text-xs text-amber-600 mt-1">Для повторяющейся задачи укажите дедлайн</p>
          )}
          {recurrence && recurrence !== 'custom' && (
            <div className="mt-2">
              <label htmlFor="task-modal-repeat-until" className="block text-xs font-medium text-gray-700 mb-1">До какого срока</label>
              <input
                id="task-modal-repeat-until"
                type="date"
                value={repeatUntil}
                onChange={(e) => setRepeatUntil(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>
          )}
          {recurrence === 'custom' && (
            <div className="mt-2 space-y-2">
              <div className="flex gap-2">
                <input
                  type="date"
                  value={repeatDateInput}
                  onChange={(e) => setRepeatDateInput(e.target.value)}
                  className="flex-1 px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                />
                <Button type="button" variant="ghost" size="sm" onClick={addRepeatDate}>Добавить</Button>
              </div>
              {repeatDates.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {repeatDates.map((d) => (
                    <span key={d} className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs">
                      {d}
                      <button
                        type="button"
                        onClick={() => setRepeatDates(prev => prev.filter(x => x !== d))}
                        className="text-blue-400 hover:text-blue-700"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div>
          <ContactCombobox
            id="task-modal-contact"
            label="Контакт"
            contacts={contacts}
            value={contactId}
            onChange={(id) => setContactId(id)}
            placeholder="Поиск контакта..."
          />
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <Button variant="ghost" onClick={onClose}>Отмена</Button>
          <Button onClick={handleCreate} disabled={!title.trim() || saving || (recurrence !== '' && recurrence !== 'custom' && !dueDate)}>
            {saving ? 'Создание...' : 'Создать'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
