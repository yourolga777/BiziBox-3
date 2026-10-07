import { useMemo, useState, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core'
import {
  ListTodo,
  Plus,
  RefreshCw,
  GripVertical,
} from 'lucide-react'
import Button from '../components/common/Button'
import Card from '../components/common/Card'
import Modal from '../components/common/Modal'
import { SkeletonList } from '../components/common/Skeleton'
import { displayNameShort } from '../utils/contactDisplayName'
import { taskApi } from '../api/client'
import ContactCombobox from '../components/contacts/ContactCombobox'
import {
  useContactsQuery,
  useCreateTaskMutation,
  useDeleteTaskMutation,
  useUpdateTaskMutation,
  useTasksQuery,
} from '../hooks/queries'
import TaskDetailModal from '../components/tasks/TaskDetailModal'
import type { TaskUpdateData } from '../components/tasks/TaskDetailModal'
import {
  DroppableColumn,
  DragOverlayCard,
  KANBAN_STATUSES,
  DraggableTaskCard,
  isOverdue,
} from '../components/tasks/KanbanCards'
import { TASK_STATUSES, TASK_STATUS_LABELS, type TaskStatus } from '../types/task'
import type { Task, TaskDetail } from '../types/task'

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

type ColumnKey = 'overdue' | TaskStatus
const COLUMN_ORDER_KEY = 'bizibox:kanban-column-order'
const DEFAULT_COLUMN_ORDER: ColumnKey[] = ['overdue', 'new', 'in_progress', 'completed']

function loadColumnOrder(): ColumnKey[] {
  try {
    const raw = localStorage.getItem(COLUMN_ORDER_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) {
        const valid = parsed.filter((k: ColumnKey) => DEFAULT_COLUMN_ORDER.includes(k))
        if (valid.length === DEFAULT_COLUMN_ORDER.length) return valid
      }
    }
  } catch {
    // ignore
  }
  return DEFAULT_COLUMN_ORDER
}

function Tasks() {
  const [searchParams] = useSearchParams()
  const [contactIdFilter] = useState<number | null>(() => {
    const cid = searchParams.get('contact_id')
    return cid ? parseInt(cid, 10) || null : null
  })
  const [showModal, setShowModal] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newDescription, setNewDescription] = useState('')
  const [newDueDate, setNewDueDate] = useState('')
  const [newReminder, setNewReminder] = useState<number | ''>('')
  const [newRecurrence, setNewRecurrence] = useState<string>('')
  const [newRepeatUntil, setNewRepeatUntil] = useState('')
  const [newRepeatDates, setNewRepeatDates] = useState<string[]>([])
  const [newRepeatDateInput, setNewRepeatDateInput] = useState('')
  const [newContactId, setNewContactId] = useState<number | ''>('')
  const [selectedTask, setSelectedTask] = useState<TaskDetail | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [activeTask, setActiveTask] = useState<Task | null>(null)
  const [columnOrder, setColumnOrder] = useState<ColumnKey[]>(loadColumnOrder)
  const [dragColumn, setDragColumn] = useState<ColumnKey | null>(null)
  const justDroppedRef = useRef(false)

  const tasksQuery = useTasksQuery({ contact_id: contactIdFilter || undefined, limit: 200 })
  const contactsQuery = useContactsQuery()
  const updateTask = useUpdateTaskMutation()
  const deleteTask = useDeleteTaskMutation()
  const createTask = useCreateTaskMutation()

  const tasks = tasksQuery.data ?? []
  const loading = tasksQuery.isLoading
  const error = tasksQuery.error

  const contacts = contactsQuery.data ?? []

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  )

  const grouped = useMemo(() => {
    const overdueIds = new Set(tasks.filter(isOverdue).map(t => t.id))
    const map: Record<TaskStatus, Task[]> = {
      new: [],
      in_progress: [],
      completed: [],
      cancelled: [],
    }
    for (const task of tasks) {
      if (overdueIds.has(task.id)) continue
      if (map[task.status]) {
        map[task.status].push(task)
      } else {
        map.new.push(task)
      }
    }
    return map
  }, [tasks])

  const overdueTasks = useMemo(() => tasks.filter(isOverdue), [tasks])

  const handleDragStart = useCallback((event: DragStartEvent) => {
    const task = event.active.data.current?.task as Task | undefined
    if (task) {
      setActiveTask(task)
      justDroppedRef.current = false
    }
  }, [])

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setActiveTask(null)
      const { active, over } = event
      if (!over) {
        setTimeout(() => { justDroppedRef.current = false }, 0)
        return
      }

      const task = active.data.current?.task as Task | undefined
      if (!task) {
        setTimeout(() => { justDroppedRef.current = false }, 0)
        return
      }

      const targetStatus = String(over.id).replace('column-', '') as TaskStatus
      if (targetStatus === task.status || !TASK_STATUSES.includes(targetStatus) || targetStatus === 'cancelled') {
        setTimeout(() => { justDroppedRef.current = false }, 0)
        return
      }

      justDroppedRef.current = true
      updateTask.mutate(
        { id: task.id, data: { status: targetStatus } },
        {
          onSettled: () => {
            setTimeout(() => { justDroppedRef.current = false }, 100)
          },
        }
      )
    },
    [updateTask]
  )

  const handleDragCancel = useCallback(() => {
    setActiveTask(null)
    setTimeout(() => { justDroppedRef.current = false }, 0)
  }, [])

  const handleColumnDrop = (target: ColumnKey) => {
    if (!dragColumn || dragColumn === target) return
    const next = [...columnOrder]
    const from = next.indexOf(dragColumn)
    const to = next.indexOf(target)
    if (from === -1 || to === -1) return
    next.splice(from, 1)
    next.splice(to, 0, dragColumn)
    setColumnOrder(next)
    try {
      localStorage.setItem(COLUMN_ORDER_KEY, JSON.stringify(next))
    } catch (err) {
      console.warn('Не удалось сохранить порядок колонок', err)
    }
    setDragColumn(null)
  }

  const columnDragProps = (key: ColumnKey) => ({
    draggable: true,
    onDragStart: () => setDragColumn(key),
    onDragOver: (e: React.DragEvent) => e.preventDefault(),
    onDrop: () => handleColumnDrop(key),
    onDragEnd: () => setDragColumn(null),
  })

  const columnDragHandle = (key: ColumnKey) => (
    <span
      {...columnDragProps(key)}
      className="cursor-grab active:cursor-grabbing text-gray-300 hover:text-gray-500 transition-colors shrink-0"
      title="Перетащить колонку"
    >
      <GripVertical size={14} />
    </span>
  )

  const handleTaskClick = async (task: Task) => {
    if (justDroppedRef.current) return
    try {
      const detail = await taskApi.getById(task.id)
      setSelectedTask(detail)
      setDetailOpen(true)
    } catch {
      // ignore error — modal won't open
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Переместить задачу в архив?')) return
    await deleteTask.mutateAsync(id)
  }

  const handleAddComment = async (taskId: number, content: string) => {
    const comment = await taskApi.addComment(taskId, content)
    setSelectedTask((prev) => prev ? { ...prev, comments: [...prev.comments, comment] } : prev)
    return comment
  }

  const handleDeleteComment = async (taskId: number, commentId: number) => {
    await taskApi.deleteComment(taskId, commentId)
    setSelectedTask((prev) => prev ? { ...prev, comments: prev.comments.filter(c => c.id !== commentId) } : prev)
  }

  const handleToggleStatus = async (task: TaskDetail) => {
    const newStatus = task.status === 'completed' ? 'in_progress' : 'completed'
    await updateTask.mutateAsync({ id: task.id, data: { status: newStatus } })
    setSelectedTask({ ...task, status: newStatus })
  }

  const handleStatusChange = async (task: TaskDetail, status: TaskStatus) => {
    await updateTask.mutateAsync({ id: task.id, data: { status } })
    setSelectedTask({ ...task, status })
  }

  const handleFieldChange = async (task: TaskDetail, field: 'contact_id', value: number | null) => {
    await updateTask.mutateAsync({ id: task.id, data: { [field]: value } })
    setSelectedTask((prev) => prev ? { ...prev, [field]: value } : prev)
  }

  const handleUpdateTask = async (task: TaskDetail, data: TaskUpdateData) => {
    await updateTask.mutateAsync({ id: task.id, data })
    try {
      const detail = await taskApi.getById(task.id)
      setSelectedTask(detail)
    } catch {
      // ignore — query invalidation обновит список
    }
  }

  const handleCreate = async () => {
    if (!newTitle.trim()) return
    await createTask.mutateAsync({
      title: newTitle.trim(),
      description: newDescription.trim() || undefined,
      due_date: newDueDate || undefined,
      reminder_minutes: newReminder === '' ? undefined : newReminder,
      recurrence: newRecurrence === 'custom' ? undefined : newRecurrence || undefined,
      repeat_dates: newRecurrence === 'custom' ? newRepeatDates : undefined,
      repeat_until: newRecurrence && newRecurrence !== 'custom' ? newRepeatUntil || undefined : undefined,
      contact_id: newContactId || undefined,
      status: 'new',
    })
    setShowModal(false)
    setNewTitle('')
    setNewDescription('')
    setNewDueDate('')
    setNewReminder('')
    setNewRecurrence('')
    setNewRepeatUntil('')
    setNewRepeatDates([])
    setNewRepeatDateInput('')
    setNewContactId('')
  }

  const handleRecurrenceChange = (value: string) => {
    setNewRecurrence(value)
    if (value === 'daily' || value === 'weekly' || value === 'monthly') {
      setNewRepeatUntil(defaultRepeatUntil(value))
    } else {
      setNewRepeatUntil('')
    }
  }

  const getContactName = (contactId: number | null): string | null => {
    if (!contactId) return null
    const c = contacts?.find((item) => item.id === contactId)
    return c ? displayNameShort(c) : null
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <ListTodo className="w-6 h-6 text-primary" />
          <h2 className="text-2xl font-semibold text-gray-900">Задачи</h2>
        </div>
        <SkeletonList count={4} />
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold text-gray-900">Задачи</h2>
        <Card>
          <div className="text-center py-8">
            <p className="text-red-500 mb-4">{error instanceof Error ? error.message : 'Ошибка загрузки'}</p>
            <Button onClick={() => tasksQuery.refetch()}>Повторить</Button>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-4 h-[calc(100vh-4rem)] flex flex-col">
      <div className="flex items-center justify-between flex-wrap gap-3 shrink-0">
        <div className="flex items-center gap-3">
          <ListTodo className="w-6 h-6 text-primary" />
          <h2 className="text-2xl font-semibold text-gray-900">Задачи</h2>
          <span className="text-sm text-gray-400">{tasks.length} задач</span>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => tasksQuery.refetch()}>
            <RefreshCw className="w-4 h-4 mr-1" />
            Обновить
          </Button>
          <Button size="sm" onClick={() => setShowModal(true)}>
            <Plus className="w-4 h-4 mr-1" />
            Создать
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3 shrink-0">
        <div className="bg-white border rounded-xl p-3"><p className="text-xs text-gray-500">Всего</p><p className="text-xl font-bold">{tasks.length}</p></div>
        <div className="bg-white border rounded-xl p-3"><p className="text-xs text-gray-500">Новых</p><p className="text-xl font-bold text-blue-600">{grouped.new.length}</p></div>
        <div className="bg-white border rounded-xl p-3"><p className="text-xs text-gray-500">В работе</p><p className="text-xl font-bold text-amber-600">{grouped.in_progress.length}</p></div>
        <div className="bg-white border rounded-xl p-3"><p className="text-xs text-gray-500">Выполнено</p><p className="text-xl font-bold text-green-600">{grouped.completed.length}</p></div>
        <div className="bg-white border rounded-xl p-3"><p className="text-xs text-gray-500">Просрочено</p><p className="text-xl font-bold text-red-600">{tasks.filter(t => t.status !== 'completed' && t.due_date && new Date(t.due_date) < new Date()).length}</p></div>
      </div>

      <DndContext
        sensors={sensors}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onDragCancel={handleDragCancel}
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 flex-1 min-h-0">
          {columnOrder.map((key) => {
            if (key === 'overdue') {
              return (
                <div key="overdue" className="flex flex-col rounded-xl border border-red-200 bg-red-50/30 min-h-[300px]">
                  <div className="px-3 pt-3">
                    <div className="flex items-center justify-between mb-3 px-0.5">
                      <div className="flex items-center gap-2">
                        {columnDragHandle('overdue')}
                        <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
                        <h4 className="text-sm font-semibold text-red-600 uppercase tracking-wide">Просроченные</h4>
                      </div>
                      <span className="text-xs font-bold text-red-500 bg-red-100 px-2 py-0.5 rounded-full">
                        {overdueTasks.length}
                      </span>
                    </div>
                  </div>
                  <div className="flex-1 px-3 pb-3 space-y-2 overflow-y-auto max-h-[calc(100vh-22rem)]">
                    {overdueTasks.length === 0 ? (
                      <div className="flex items-center justify-center h-32 text-xs text-gray-400">Нет задач</div>
                    ) : (
                      overdueTasks.map((task) => (
                        <DraggableTaskCard key={task.id} task={task} onClick={handleTaskClick} getContactName={getContactName} />
                      ))
                    )}
                  </div>
                </div>
              )
            }
            const s = KANBAN_STATUSES.find((x) => x.status === key)!
            return (
              <DroppableColumn
                key={key}
                status={s.status}
                label={TASK_STATUS_LABELS[s.status]}
                dot={s.dot}
                tasks={grouped[s.status]}
                isLoading={loading}
                onTaskClick={handleTaskClick}
                getContactName={getContactName}
                dragHandle={columnDragHandle(key)}
              />
            )
          })}
        </div>
        <DragOverlay>
          {activeTask ? <DragOverlayCard task={activeTask} /> : null}
        </DragOverlay>
      </DndContext>

      <Modal open={showModal} onClose={() => setShowModal(false)} title="Новая задача" maxWidth="max-w-md">
        <div className="p-6 space-y-4">
          <div>
            <label htmlFor="task-title" className="block text-sm font-medium text-gray-700 mb-1">Заголовок *</label>
            <input
              id="task-title"
              type="text"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              placeholder="Купить офисные стулья"
            />
          </div>

          <div>
            <label htmlFor="task-description" className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
            <textarea
              id="task-description"
              value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary resize-none"
              rows={3}
              placeholder="Дополнительные детали..."
            />
          </div>

          <div>
            <label htmlFor="task-deadline" className="block text-sm font-medium text-gray-700 mb-1">Дедлайн</label>
            <input
              id="task-deadline"
              type="datetime-local"
              value={newDueDate}
              onChange={(e) => setNewDueDate(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>

          <div>
            <label htmlFor="task-reminder" className="block text-sm font-medium text-gray-700 mb-1">Напоминание</label>
            <select
              id="task-reminder"
              value={newReminder}
              onChange={(e) => setNewReminder(e.target.value === '' ? '' : Number(e.target.value))}
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
            <label htmlFor="task-recurrence" className="block text-sm font-medium text-gray-700 mb-1">Повтор</label>
            <select
              id="task-recurrence"
              value={newRecurrence}
              onChange={(e) => handleRecurrenceChange(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary bg-white"
            >
              <option value="">Не повторяется</option>
              <option value="daily">Ежедневно</option>
              <option value="weekly">Еженедельно</option>
              <option value="monthly">Ежемесячно</option>
              <option value="custom">По конкретным датам</option>
            </select>
            {newRecurrence && newRecurrence !== 'custom' && !newDueDate && (
              <p className="text-xs text-amber-600 mt-1">Для повторяющейся задачи укажите дедлайн</p>
            )}
            {newRecurrence && newRecurrence !== 'custom' && (
              <div className="mt-2">
                <label htmlFor="task-repeat-until" className="block text-xs font-medium text-gray-700 mb-1">До какого срока</label>
                <input
                  id="task-repeat-until"
                  type="date"
                  value={newRepeatUntil}
                  onChange={(e) => setNewRepeatUntil(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                />
              </div>
            )}
            {newRecurrence === 'custom' && (
              <div className="mt-2 space-y-2">
                <div className="flex gap-2">
                  <input
                    type="date"
                    value={newRepeatDateInput}
                    onChange={(e) => setNewRepeatDateInput(e.target.value)}
                    className="flex-1 px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      if (newRepeatDateInput && !newRepeatDates.includes(newRepeatDateInput)) {
                        setNewRepeatDates(prev => [...prev, newRepeatDateInput].sort())
                      }
                      setNewRepeatDateInput('')
                    }}
                  >
                    Добавить
                  </Button>
                </div>
                {newRepeatDates.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {newRepeatDates.map((d) => (
                      <span key={d} className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs">
                        {d}
                        <button
                          type="button"
                          onClick={() => setNewRepeatDates(prev => prev.filter(x => x !== d))}
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
              id="task-contact"
              label="Контакт"
              contacts={contacts}
              value={newContactId === '' ? null : newContactId}
              onChange={(id) => setNewContactId(id === null ? '' : id)}
              placeholder="Поиск контакта..."
            />
          </div>
          <div className="flex justify-end gap-2 mt-6">
            <Button variant="ghost" onClick={() => setShowModal(false)}>Отмена</Button>
            <Button onClick={handleCreate} disabled={newRecurrence !== '' && newRecurrence !== 'custom' && !newDueDate}>Создать</Button>
          </div>
        </div>
      </Modal>

      <TaskDetailModal
        open={detailOpen}
        onClose={() => { setDetailOpen(false); setSelectedTask(null) }}
        task={selectedTask}
        contacts={contacts}
        onAddComment={handleAddComment}
        onDeleteComment={handleDeleteComment}
        onToggleStatus={handleToggleStatus}
        onStatusChange={handleStatusChange}
        onFieldChange={handleFieldChange}
        onDelete={handleDelete}
        onUpdateTask={handleUpdateTask}
      />
    </div>
  )
}

export default Tasks
