import { useDroppable, useDraggable } from '@dnd-kit/core'
import { CalendarIcon, GripVertical, Bell } from 'lucide-react'
import MessagePreview from '../common/MessagePreview'
import type { TaskStatus } from '../../types/task'
import type { Task } from '../../types/task'

export const KANBAN_STATUSES: { status: TaskStatus; color: string; dot: string }[] = [
  { status: 'new', color: 'bg-blue-50', dot: 'bg-blue-500' },
  { status: 'in_progress', color: 'bg-amber-50', dot: 'bg-amber-500' },
  { status: 'completed', color: 'bg-green-50', dot: 'bg-green-500' },
]

export function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const date = d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' })
  if (dateStr.includes('T') || dateStr.includes(':')) {
    return `${date} ${d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`
  }
  return date
}

export function isOverdue(task: Task): boolean {
  return task.status !== 'completed' && !!task.due_date && new Date(task.due_date) < new Date()
}

interface ColumnProps {
  status: TaskStatus
  label: string
  dot: string
  tasks: Task[]
  isLoading: boolean
  onTaskClick: (task: Task) => void
  getContactName: (id: number | null) => string | null
  dragHandle?: React.ReactNode
}

export function DroppableColumn({ status, label, dot, tasks, isLoading, onTaskClick, getContactName, dragHandle }: ColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: `column-${status}` })

  return (
    <div
      ref={setNodeRef}
      className={`flex flex-col rounded-xl border min-h-[300px] transition-colors duration-150 ${
        isOver ? 'border-primary bg-primary/5' : 'border-gray-200 bg-gray-50/50'
      }`}
    >
      <div className="px-3 pt-3">
        <div className="flex items-center justify-between mb-3 px-0.5">
          <div className="flex items-center gap-2">
            {dragHandle}
            <span className={`w-2.5 h-2.5 rounded-full ${dot}`} />
            <h4 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">{label}</h4>
          </div>
          <span className="text-xs font-bold text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
            {tasks.length}
          </span>
        </div>
      </div>
      <div className="flex-1 px-3 pb-3 space-y-2 overflow-y-auto max-h-[calc(100vh-22rem)]">
        {isLoading ? (
          <div className="space-y-2 animate-pulse">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-lg" />
            ))}
          </div>
        ) : tasks.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-xs text-gray-400">Нет задач</div>
        ) : (
          tasks.map((task) => (
            <DraggableTaskCard key={task.id} task={task} onClick={onTaskClick} getContactName={getContactName} />
          ))
        )}
      </div>
    </div>
  )
}

interface DraggableTaskCardProps {
  task: Task
  onClick: (task: Task) => void
  getContactName: (id: number | null) => string | null
}

export function DraggableTaskCard({ task, onClick, getContactName }: DraggableTaskCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `task-${task.id}`,
    data: { task },
  })

  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`, zIndex: 50 }
    : undefined

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      role="button"
      tabIndex={0}
      onClick={() => {
        if (isDragging) return
        onClick(task)
      }}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick(task)
        }
      }}
      className={`block bg-white rounded-lg border border-gray-200 p-3 shadow-sm transition-all duration-150 cursor-grab active:cursor-grabbing
        ${isDragging ? 'opacity-50 shadow-lg ring-2 ring-primary/30' : 'hover:shadow-md hover:border-gray-300'}
      `}
    >
      <div className="flex items-start gap-2">
        <GripVertical size={14} className="mt-0.5 text-gray-300" />
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-semibold text-gray-900 truncate ${task.status === 'completed' ? 'line-through text-gray-400' : ''}`}>
            {task.title}
          </p>
          <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
            {task.contact_id ? (
              <span className="truncate text-gray-500">
                {getContactName(task.contact_id) || `Контакт #${task.contact_id}`}
              </span>
            ) : null}
            {task.due_date ? (
              <span className={`flex items-center gap-1 ${isOverdue(task) ? 'text-red-500 font-medium' : ''}`}>
                <CalendarIcon size={12} />
                {formatDate(task.due_date)}
              </span>
            ) : null}
          </div>
          {task.message_id != null && (
            <MessagePreview messageId={task.message_id} className="text-[10px] text-gray-400 mt-1 line-clamp-2 italic" />
          )}
          <div className="flex items-center gap-1.5 mt-2">
            {task.reminder_minutes != null && (
              <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-purple-50 text-purple-600" title="Напоминание">
                <Bell size={10} />
                {task.reminder_minutes === 0 ? 'в срок' : `${task.reminder_minutes} мин`}
              </span>
            )}
            {task.status === 'completed' && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-100 text-green-600">Выполнена</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export function DragOverlayCard({ task }: { task: Task }) {
  return (
    <div className="bg-white rounded-lg border-2 border-primary border-dashed p-3 shadow-xl">
      <div className="flex items-start gap-2">
        <GripVertical size={14} className="mt-0.5 text-gray-300" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-900 truncate">{task.title}</p>
        </div>
      </div>
    </div>
  )
}
