import { useState, useEffect } from 'react'
import { CalendarIcon, CheckCircle2, Circle, Clock, Plus, Trash2, User, X } from 'lucide-react'
import Modal from '../common/Modal'
import Button from '../common/Button'
import MessagePreview from '../common/MessagePreview'
import ContactCombobox from '../contacts/ContactCombobox'
import { TASK_STATUS_LABELS, type TaskStatus } from '../../types/task'
import type { TaskDetail, TaskComment } from '../../types/task'
import type { Contact } from '../../types/contact'

export interface TaskUpdateData {
  due_date?: string | null
  recurrence?: string | null
  repeat_until?: string | null
  repeat_dates?: string[] | null
}

interface TaskDetailModalProps {
  open: boolean
  onClose: () => void
  task: TaskDetail | null
  contacts: Contact[]
  onAddComment: (taskId: number, content: string) => Promise<TaskComment>
  onDeleteComment: (taskId: number, commentId: number) => Promise<void>
  onToggleStatus: (task: TaskDetail) => void
  onStatusChange?: (task: TaskDetail, status: TaskStatus) => void
  onFieldChange?: (task: TaskDetail, field: 'contact_id', value: number | null) => void
  onDelete?: (id: number) => void
  onUpdateTask?: (task: TaskDetail, data: TaskUpdateData) => Promise<void>
}

const STATUS_META: Record<TaskStatus, { color: string }> = {
  new: { color: 'bg-blue-100 text-blue-700' },
  in_progress: { color: 'bg-amber-100 text-amber-700' },
  completed: { color: 'bg-green-100 text-green-700' },
  cancelled: { color: 'bg-red-100 text-red-700' },
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' })
}

function toDateTimeLocal(value: string | null): string {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`
}

function toDateInputValue(d: Date): string {
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function defaultRepeatUntil(recurrence: string): string {
  const d = new Date()
  if (recurrence === 'daily') d.setMonth(d.getMonth() + 1)
  else if (recurrence === 'weekly') d.setMonth(d.getMonth() + 3)
  else if (recurrence === 'monthly') d.setFullYear(d.getFullYear() + 1)
  return toDateInputValue(d)
}

function TaskDetailModal({ open, onClose, task, contacts, onAddComment, onDeleteComment, onToggleStatus, onStatusChange, onFieldChange, onDelete, onUpdateTask }: TaskDetailModalProps) {
  const [commentText, setCommentText] = useState('')
  const [adding, setAdding] = useState(false)
  const [editDueDate, setEditDueDate] = useState('')
  const [editRecurrence, setEditRecurrence] = useState('')
  const [editRepeatUntil, setEditRepeatUntil] = useState('')
  const [editRepeatDates, setEditRepeatDates] = useState<string[]>([])
  const [editRepeatDateInput, setEditRepeatDateInput] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (task) {
      setEditDueDate(toDateTimeLocal(task.due_date ?? null))
      setEditRecurrence(task.recurrence ?? (task.repeat_dates?.length ? 'custom' : ''))
      setEditRepeatUntil(task.repeat_until ? (task.repeat_until.slice(0, 10)) : '')
      setEditRepeatDates(task.repeat_dates ?? [])
      setEditRepeatDateInput('')
      setCommentText('')
    }
  }, [task])

  if (!task) return null

  const status = STATUS_META[task.status] || STATUS_META.new
  const isOverdue = task.status !== 'completed' && task.due_date && new Date(task.due_date) < new Date()

  const handleAddComment = async () => {
    if (!commentText.trim() || adding) return
    setAdding(true)
    try {
      await onAddComment(task.id, commentText.trim())
      setCommentText('')
    } finally {
      setAdding(false)
    }
  }

  const handleRecurrenceChange = (value: string) => {
    setEditRecurrence(value)
    if (value === 'daily' || value === 'weekly' || value === 'monthly') {
      setEditRepeatUntil(defaultRepeatUntil(value))
    } else {
      setEditRepeatUntil('')
    }
  }

  const addRepeatDate = () => {
    if (editRepeatDateInput && !editRepeatDates.includes(editRepeatDateInput)) {
      setEditRepeatDates(prev => [...prev, editRepeatDateInput].sort())
    }
    setEditRepeatDateInput('')
  }

  const handleSave = async () => {
    if (!onUpdateTask || saving) return
    setSaving(true)
    try {
      await onUpdateTask(task, {
        due_date: editDueDate || null,
        recurrence: editRecurrence === 'custom' ? null : (editRecurrence || null),
        repeat_until: editRecurrence && editRecurrence !== 'custom' ? (editRepeatUntil || null) : null,
        repeat_dates: editRecurrence === 'custom' ? editRepeatDates : null,
      })
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={task.title} maxWidth="max-w-2xl">
      <div className="p-6 space-y-6">
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => onToggleStatus(task)}
            className="shrink-0 text-gray-400 hover:text-primary transition-colors"
            title={task.status === 'completed' ? 'Вернуть в работу' : 'Отметить выполненной'}
          >
            {task.status === 'completed' ? (
              <CheckCircle2 className="w-5 h-5 text-green-500" />
            ) : (
              <Circle className="w-5 h-5" />
            )}
          </button>
          <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${status.color}`}>
            {TASK_STATUS_LABELS[task.status]}
          </span>
          {onStatusChange && (
            <select
              value={task.status}
              onChange={(e) => onStatusChange(task, e.target.value as TaskStatus)}
              className="text-xs border border-gray-200 rounded-lg px-2 py-1 outline-none focus:border-primary"
            >
              {Object.entries(TASK_STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          )}
        </div>

        {task.description && (
          <div>
            <p className="text-sm text-gray-600">{task.description}</p>
          </div>
        )}

        {task.message_id != null && (
          <MessagePreview messageId={task.message_id} className="text-xs text-gray-500 italic line-clamp-3" />
        )}

        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
              <User className="w-3.5 h-3.5" />
              Контакт
            </p>
            {onFieldChange ? (
              <ContactCombobox
                contacts={contacts}
                value={task.contact_id}
                onChange={(id) => onFieldChange(task, 'contact_id', id)}
                placeholder="Поиск контакта..."
              />
            ) : (
              <p className="text-sm text-gray-600">{task.contact_name || '—'}</p>
            )}
          </div>
          {task.due_date && (
            <div className={`flex items-center gap-2 text-sm ${isOverdue ? 'text-red-500' : 'text-gray-500'}`}>
              <CalendarIcon className="w-4 h-4" />
              <span>Дедлайн: {formatDate(task.due_date)}</span>
              {isOverdue && <span className="text-xs text-red-400">(просрочено)</span>}
            </div>
          )}
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Clock className="w-4 h-4" />
            <span>Создана: {formatDate(task.created_at)}</span>
          </div>
        </div>

        {onUpdateTask && (
          <div className="border-t pt-4 space-y-3">
            <h4 className="text-sm font-medium text-gray-700">Дедлайн и повтор</h4>
            <div>
              <label htmlFor="task-detail-deadline" className="block text-xs font-medium text-gray-500 mb-1">Дедлайн</label>
              <input
                id="task-detail-deadline"
                type="datetime-local"
                value={editDueDate}
                onChange={(e) => setEditDueDate(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>
            <div>
              <label htmlFor="task-detail-recurrence" className="block text-xs font-medium text-gray-500 mb-1">Повтор</label>
              <select
                id="task-detail-recurrence"
                value={editRecurrence}
                onChange={(e) => handleRecurrenceChange(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary bg-white"
              >
                <option value="">Не повторяется</option>
                <option value="daily">Ежедневно</option>
                <option value="weekly">Еженедельно</option>
                <option value="monthly">Ежемесячно</option>
                <option value="custom">По конкретным датам</option>
              </select>
              {editRecurrence && editRecurrence !== 'custom' && (
                <div className="mt-2">
                  <label htmlFor="task-detail-repeat-until" className="block text-xs font-medium text-gray-500 mb-1">До какого срока</label>
                  <input
                    id="task-detail-repeat-until"
                    type="date"
                    value={editRepeatUntil}
                    onChange={(e) => setEditRepeatUntil(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                  />
                </div>
              )}
              {editRecurrence === 'custom' && (
                <div className="mt-2 space-y-2">
                  <div className="flex gap-2">
                    <input
                      type="date"
                      value={editRepeatDateInput}
                      onChange={(e) => setEditRepeatDateInput(e.target.value)}
                      className="flex-1 px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                    />
                    <Button type="button" variant="ghost" size="sm" onClick={addRepeatDate}>Добавить</Button>
                  </div>
                  {editRepeatDates.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {editRepeatDates.map((d) => (
                        <span key={d} className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs">
                          {d}
                          <button
                            type="button"
                            onClick={() => setEditRepeatDates(prev => prev.filter(x => x !== d))}
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
            <div className="flex justify-end">
              <Button onClick={handleSave} disabled={saving} size="sm">
                {saving ? 'Сохранение...' : 'Сохранить'}
              </Button>
            </div>
          </div>
        )}

        <div className="border-t pt-4">
          <h4 className="text-sm font-medium text-gray-700 mb-3">Комментарии</h4>
          {task.comments.length === 0 ? (
            <p className="text-sm text-gray-400">Нет комментариев</p>
          ) : (
            <div className="space-y-2 mb-4">
              {task.comments.map((comment) => (
                <div key={comment.id} className="bg-gray-50 rounded-xl p-3 flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">{comment.content}</p>
                    <p className="text-xs text-gray-400 mt-1">{formatDate(comment.created_at)}</p>
                  </div>
                  <button
                    onClick={() => onDeleteComment(task.id, comment.id)}
                    className="shrink-0 p-1 text-gray-300 hover:text-red-500 transition-colors"
                    title="Удалить комментарий"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <input
              type="text"
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleAddComment() }}
              placeholder="Добавить комментарий..."
              className="flex-1 px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
            <Button onClick={handleAddComment} disabled={adding || !commentText.trim()} size="sm">
              <Plus className="w-4 h-4 mr-1" />
              {adding ? '...' : 'Добавить'}
            </Button>
          </div>
        </div>

        <div className="flex justify-between items-center">
          {onDelete ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(task.id)}
              className="text-red-600 hover:text-red-700 hover:bg-red-50"
            >
              <Trash2 className="w-4 h-4 mr-1" />
              В архив
            </Button>
          ) : (
            <div />
          )}
          <div className="flex gap-2">
            <Button variant="ghost" onClick={onClose}>Закрыть</Button>
          </div>
        </div>
      </div>
    </Modal>
  )
}

export default TaskDetailModal
