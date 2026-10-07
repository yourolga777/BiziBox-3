import { useEffect, useState } from 'react'
import { Dialog } from '@headlessui/react'
import { AlertCircle, Calendar, Cake, CheckCircle2, Pencil, User } from 'lucide-react'
import { calendarApi } from '../../api/calendar'
import { contactApi, taskApi } from '../../api/client'
import type { CalendarEvent as CalendarEventType } from '../../types/calendar'
import type { Contact } from '../../types/contact'
import type { Task, TaskStatus } from '../../types/task'

interface CalendarEventDetailProps {
  event: CalendarEventType | null
  isOpen: boolean
  onClose: () => void
  onUpdated: () => void
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr)
  const date = d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
  if (dateStr.includes('T')) {
    return `${date} ${d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`
  }
  return date
}

export function CalendarEventDetail({ event, isOpen, onClose, onUpdated }: CalendarEventDetailProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [editStatus, setEditStatus] = useState<TaskStatus>('new')
  const [editContactId, setEditContactId] = useState<number | ''>('')
  const [editDate, setEditDate] = useState('')
  const [contacts, setContacts] = useState<Contact[]>([])
  const [fullTask, setFullTask] = useState<Task | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (isOpen && event) {
      setIsEditing(false)
      setFullTask(null)
      if (event.type === 'task') {
        taskApi.getById(event.id).then(setFullTask).catch(() => {})
      }
      contactApi.getAll().then(setContacts).catch(() => {})
    }
  }, [isOpen, event])

  if (!event) return null

  if (event.type === 'birthday') {
    return (
      <Dialog open={isOpen} onClose={onClose} className="relative z-50">
        <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="w-full max-w-md bg-white rounded-xl p-6">
            <Dialog.Title className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Cake size={18} className="text-pink-500" />
              {event.title}
            </Dialog.Title>
            <div className="space-y-3 text-sm text-gray-600">
              <div className="flex items-center gap-2">
                <Calendar size={14} />
                <span>{formatDate(event.date)}</span>
              </div>
              {event.contact_name && (
                <div className="flex items-center gap-2">
                  <User size={14} />
                  <span>{event.contact_name}</span>
                </div>
              )}
            </div>
            <div className="flex justify-end mt-6">
              <button onClick={onClose} className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
                Закрыть
              </button>
            </div>
          </Dialog.Panel>
        </div>
      </Dialog>
    )
  }

  if (event.type === 'event') {
    const startEditing = () => {
      setEditTitle(event.title)
      setEditDescription(event.metadata?.description ? String(event.metadata.description) : '')
      setEditDate(event.date)
      setEditContactId('')
      setIsEditing(true)
    }

    const handleDelete = async () => {
      if (!confirm('Удалить событие?')) return
      await calendarApi.deleteEvent(event.id)
      onUpdated()
      onClose()
    }

    const handleSave = async () => {
      if (!editTitle.trim()) return
      setSaving(true)
      try {
        await calendarApi.updateEvent(event.id, {
          title: editTitle.trim(),
          description: editDescription.trim() || null,
          date: editDate,
        })
        onUpdated()
        onClose()
      } finally {
        setSaving(false)
      }
    }

    return (
      <Dialog open={isOpen} onClose={onClose} className="relative z-50">
        <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="w-full max-w-md bg-white rounded-xl p-6">
            <Dialog.Title className="text-lg font-semibold mb-4 flex items-center justify-between">
              <span>{isEditing ? 'Редактировать событие' : event.title}</span>
              {!isEditing && (
                <button onClick={startEditing} className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
                  <Pencil size={16} />
                </button>
              )}
            </Dialog.Title>

            {isEditing ? (
              <div className="space-y-4">
                <div>
                  <label htmlFor="ev-title" className="block text-sm font-medium text-gray-700 mb-1">Заголовок</label>
                  <input id="ev-title" type="text" value={editTitle} onChange={(e) => setEditTitle(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                </div>
                <div>
                  <label htmlFor="ev-date" className="block text-sm font-medium text-gray-700 mb-1">Дата</label>
                  <input id="ev-date" type="date" value={editDate} onChange={(e) => setEditDate(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                </div>
                <div>
                  <label htmlFor="ev-description" className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
                  <textarea id="ev-description" value={editDescription} onChange={(e) => setEditDescription(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none" rows={3} />
                </div>
                <div className="flex justify-between gap-2 pt-2">
                  <button onClick={handleDelete} className="px-3 py-2 text-sm text-red-600 border border-red-300 rounded-lg hover:bg-red-50">Удалить</button>
                  <div className="flex gap-2">
                    <button onClick={() => setIsEditing(false)} className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">Отмена</button>
                    <button onClick={handleSave} disabled={saving || !editTitle.trim()} className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">{saving ? 'Сохранение...' : 'Сохранить'}</button>
                  </div>
                </div>
              </div>
            ) : (
              <>
                <div className="space-y-3 text-sm">
                  {event.metadata.description != null ? (
                    <p className="text-gray-600">{String(event.metadata.description)}</p>
                  ) : null}
                  <div className="flex items-center gap-2 text-gray-500">
                    <Calendar size={14} />
                    <span>{formatDate(event.date)}{event.time ? ` ${event.time}` : ''}</span>
                  </div>
                  {event.contact_name && (
                    <div className="flex items-center gap-2 text-gray-500">
                      <User size={14} />
                      <span>{event.contact_name}</span>
                    </div>
                  )}
                </div>
                <div className="flex justify-between gap-2 mt-6">
                  <button onClick={handleDelete} className="px-3 py-2 text-sm text-red-600 border border-red-300 rounded-lg hover:bg-red-50">Удалить</button>
                  <button onClick={onClose} className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">Закрыть</button>
                </div>
              </>
            )}
          </Dialog.Panel>
        </div>
      </Dialog>
    )
  }

  const startEditing = () => {
    const dueDate = fullTask?.due_date || event.date
    setEditTitle(event.title)
    setEditDescription(event.metadata?.description ? String(event.metadata.description) : '')
    setEditStatus((event.status === 'completed' || event.status === 'cancelled' ? event.status : 'new') as TaskStatus)
    setEditContactId(fullTask?.contact_id ?? '')
    setEditDate(dueDate)
    setIsEditing(true)
  }

  const handleToggle = async () => {
    const newStatus = event.status === 'completed' ? 'in_progress' : 'completed'
    await taskApi.update(event.id, { status: newStatus })
    onUpdated()
    onClose()
  }

  const handleDelete = async () => {
    if (!confirm('Переместить задачу в архив?')) return
    await taskApi.delete(event.id)
    onUpdated()
    onClose()
  }

  const handleSave = async () => {
    if (!editTitle.trim()) return
    setSaving(true)
    try {
      await taskApi.update(event.id, {
        title: editTitle.trim(),
        description: editDescription.trim() || null,
        status: editStatus,
        contact_id: editContactId || null,
        due_date: editDate || null,
      })
      onUpdated()
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={isOpen} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="w-full max-w-md bg-white rounded-xl p-6">
          <Dialog.Title className="text-lg font-semibold mb-4 flex items-center justify-between">
            <span className="flex items-center gap-2">
              {event.is_overdue && <AlertCircle size={18} className="text-red-500" />}
              {event.status === 'completed' && <CheckCircle2 size={18} className="text-green-500" />}
              {isEditing ? 'Редактировать задачу' : event.title}
            </span>
            {!isEditing && (
              <button onClick={startEditing} className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
                <Pencil size={16} />
              </button>
            )}
          </Dialog.Title>

          {isEditing ? (
            <div className="space-y-4">
              <div>
                <label htmlFor="event-title" className="block text-sm font-medium text-gray-700 mb-1">Заголовок</label>
                <input id="event-title" type="text" value={editTitle} onChange={(e) => setEditTitle(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              </div>
              <div>
                <label htmlFor="event-description" className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
                <textarea id="event-description" value={editDescription} onChange={(e) => setEditDescription(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none" rows={3} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="event-status" className="block text-sm font-medium text-gray-700 mb-1">Статус</label>
                  <select id="event-status" value={editStatus} onChange={(e) => setEditStatus(e.target.value as TaskStatus)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                    <option value="new">Новая</option>
                    <option value="in_progress">В работе</option>
                    <option value="completed">Выполнена</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="event-datetime" className="block text-sm font-medium text-gray-700 mb-1">Дата и время</label>
                  <input id="event-datetime" type="datetime-local" value={editDate} onChange={(e) => setEditDate(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                </div>
              </div>
              <div>
                <label htmlFor="event-contact" className="block text-sm font-medium text-gray-700 mb-1">Контакт</label>
                <select id="event-contact" value={editContactId} onChange={(e) => setEditContactId(e.target.value ? Number(e.target.value) : '')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                  <option value="">Без контакта</option>
                  {contacts.map((c) => (
                    <option key={c.id} value={c.id}>{c.name || c.phone || `Контакт #${c.id}`}</option>
                  ))}
                </select>
              </div>
              <div className="flex justify-between gap-2 pt-2">
                <button onClick={handleDelete} className="px-3 py-2 text-sm text-red-600 border border-red-300 rounded-lg hover:bg-red-50">Удалить</button>
                <div className="flex gap-2">
                  <button onClick={() => setIsEditing(false)} className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">Отмена</button>
                  <button onClick={handleSave} disabled={saving || !editTitle.trim()} className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">{saving ? 'Сохранение...' : 'Сохранить'}</button>
                </div>
              </div>
            </div>
          ) : (
            <>
              <div className="space-y-3 text-sm">
                {event.metadata.description != null ? (
                  <p className="text-gray-600">{String(event.metadata.description)}</p>
                ) : null}
                <div className="flex items-center gap-2 text-gray-500">
                  <Calendar size={14} />
                  <span>{formatDate(event.date)}</span>
                </div>
                {event.contact_name && (
                  <div className="flex items-center gap-2 text-gray-500">
                    <User size={14} />
                    <span>{event.contact_name}</span>
                  </div>
                )}
                <div>
                  <span className="text-gray-500">Статус: </span>
                  <span className={`font-medium ${event.status === 'completed' ? 'text-green-600' : event.status === 'cancelled' ? 'text-gray-500' : event.is_overdue ? 'text-red-600' : 'text-blue-600'}`}>
                    {event.status === 'completed' ? 'Выполнена' : event.status === 'cancelled' ? 'Отменена' : event.is_overdue ? 'Просрочена' : 'Активна'}
                  </span>
                </div>
              </div>
              <div className="flex justify-between gap-2 mt-6">
                <button onClick={handleDelete} className="px-3 py-2 text-sm text-red-600 border border-red-300 rounded-lg hover:bg-red-50">Удалить</button>
                <div className="flex gap-2">
                  <button onClick={onClose} className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">Закрыть</button>
                  <button onClick={handleToggle} className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700">{event.status === 'completed' ? 'Вернуть в работу' : 'Выполнено'}</button>
                </div>
              </div>
            </>
          )}
        </Dialog.Panel>
      </div>
    </Dialog>
  )
}
