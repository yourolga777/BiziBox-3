import { useState } from 'react'
import { CheckCircle, X } from 'lucide-react'
import Button from '../common/Button'
import { taskApi } from '../../api/client'

interface TaskFormProps {
  contactId: number
  contactName: string | null
  onTaskCreated: () => void
  onClose: () => void
  initialTitle?: string
  initialDescription?: string
  messageId?: number | null
}

function TaskForm({ contactId, contactName, onTaskCreated, onClose, initialTitle, initialDescription, messageId }: TaskFormProps) {
  const [title, setTitle] = useState(initialTitle ?? '')
  const [description, setDescription] = useState(initialDescription ?? '')
  const [dueDate, setDueDate] = useState('')
  const [reminder, setReminder] = useState<number | ''>('')
  const [recurrence, setRecurrence] = useState<string>('')
  const [saving, setSaving] = useState(false)
  const [created, setCreated] = useState(false)

  const handleCreate = async () => {
    if (!title.trim()) return
    setSaving(true)
    try {
      await taskApi.create({
        title: title.trim(),
        description: description.trim() || undefined,
        due_date: dueDate || undefined,
        reminder_minutes: reminder === '' ? undefined : reminder,
        recurrence: recurrence || undefined,
        contact_id: contactId,
        message_id: messageId ?? undefined,
      })
      setCreated(true)
      onTaskCreated()
    } catch {
      setSaving(false)
    }
  }

  if (created) {
    return (
      <div className="p-4 rounded-xl bg-green-50 border border-green-200">
        <p className="text-sm font-medium text-green-700">✓ Задача создана</p>
      </div>
    )
  }

  return (
    <div className="p-4 rounded-xl bg-purple-50 border border-purple-200">
      <div className="flex items-start gap-3">
        <div className="p-1.5 rounded-lg bg-purple-100">
          <CheckCircle className="w-4 h-4 text-purple-600" />
        </div>
        <div className="flex-1 min-w-0">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full px-3 py-1.5 mb-2 rounded-lg border border-purple-200 text-sm outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400"
            placeholder="Заголовок задачи"
          />

          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="w-full px-3 py-1.5 mb-2 rounded-lg border border-purple-200 text-sm outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400 resize-none"
            placeholder="Описание задачи (необязательно)..."
          />

          <div className="flex items-center gap-2 mb-3">
              <input
                type="datetime-local"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="flex-1 px-3 py-1.5 rounded-lg border border-purple-200 text-sm outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400"
              />
            {contactName && (
              <span className="text-xs text-purple-500 shrink-0">{contactName}</span>
            )}
          </div>

          <div className="flex items-center gap-2 mb-3">
            <select
              value={reminder}
              onChange={(e) => setReminder(e.target.value === '' ? '' : Number(e.target.value))}
              className="flex-1 px-3 py-1.5 rounded-lg border border-purple-200 text-sm outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400 bg-white"
              aria-label="Напоминание"
            >
              <option value="">Без напоминания</option>
              <option value="0">В срок</option>
              <option value="15">За 15 минут</option>
              <option value="30">За 30 минут</option>
              <option value="60">За час</option>
              <option value="1440">За день</option>
            </select>
            <select
              value={recurrence}
              onChange={(e) => setRecurrence(e.target.value)}
              className="flex-1 px-3 py-1.5 rounded-lg border border-purple-200 text-sm outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400 bg-white"
              aria-label="Повторение"
            >
              <option value="">Не повторяется</option>
              <option value="daily">Ежедневно</option>
              <option value="weekly">Еженедельно</option>
              <option value="monthly">Ежемесячно</option>
            </select>
          </div>
          {recurrence && !dueDate && (
            <p className="text-xs text-amber-600 mb-2">Для повторяющейся задачи укажите дедлайн</p>
          )}

          <div className="flex items-center gap-2">
            <Button size="sm" onClick={handleCreate} disabled={!title.trim() || saving}>
              {saving ? 'Создание...' : 'Создать задачу'}
            </Button>
            <Button size="sm" variant="ghost" onClick={onClose}>
              <X className="w-4 h-4 mr-1" />
              Отмена
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default TaskForm
