import { useMemo } from 'react'
import { AlertCircle, CalendarIcon, CheckCircle2, Circle, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'
import Card from '../common/Card'
import MessagePreview from '../common/MessagePreview'
import { useTasksQuery, useUpdateTaskMutation } from '../../hooks/queries'
import { TASK_STATUS_LABELS, type TaskStatus } from '../../types/task'
import type { Task } from '../../types/task'

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const date = d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
  if (dateStr.includes('T')) {
    return `${date} ${d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`
  }
  return date
}

function isOverdue(task: Task): boolean {
  return task.status !== 'completed' && !!task.due_date && new Date(task.due_date) < new Date()
}

const DASHBOARD_STATUSES = [
  { status: 'new' as const, label: TASK_STATUS_LABELS.new, color: 'text-blue-600', dot: 'bg-blue-500' },
  { status: 'in_progress' as const, label: TASK_STATUS_LABELS.in_progress, color: 'text-amber-600', dot: 'bg-amber-500' },
  { status: 'completed' as const, label: TASK_STATUS_LABELS.completed, color: 'text-green-600', dot: 'bg-green-500' },
  { status: 'cancelled' as const, label: TASK_STATUS_LABELS.cancelled, color: 'text-red-600', dot: 'bg-red-500' },
]

const MAX_CARDS = 4

function TaskCard({ task }: { task: Task }) {
  const updateTask = useUpdateTaskMutation()
  const toggle = () => {
    updateTask.mutate({ id: task.id, data: { status: task.status === 'completed' ? 'new' : 'completed' } })
  }

  return (
    <div className="flex items-start gap-2 bg-white rounded-lg border border-gray-200 p-2.5 shadow-sm">
      <button
        onClick={toggle}
        className="mt-0.5 shrink-0 text-gray-400 hover:text-primary transition-colors"
        aria-label={task.status === 'completed' ? 'Вернуть в работу' : 'Выполнено'}
      >
        {task.status === 'completed' ? (
          <CheckCircle2 size={16} className="text-green-500" />
        ) : (
          <Circle size={16} />
        )}
      </button>
      <Link to={`/tasks/${task.id}`} className="flex-1 min-w-0">
        <p className={`text-sm font-semibold text-gray-900 truncate ${task.status === 'completed' ? 'line-through text-gray-400' : ''}`}>
          {task.title}
        </p>
        <div className="flex items-center gap-2 mt-1 text-xs text-gray-400">
          {task.contact_id ? (
            <span>Контакт #{task.contact_id}</span>
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
      </Link>
    </div>
  )
}

function StatusColumn({ status, label, color, dot, tasks, isLoading }: { status: TaskStatus; label: string; color: string; dot: string; tasks: Task[]; isLoading: boolean }) {
  const visible = tasks.slice(0, MAX_CARDS)
  const hasMore = tasks.length > MAX_CARDS

  return (
    <div className="flex flex-col rounded-xl border border-gray-200 bg-gray-50/50 min-h-[140px]">
      <div className="px-2.5 pt-2.5">
        <div className="flex items-center justify-between mb-2 px-0.5">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${dot}`} />
            <h4 className={`text-sm font-semibold uppercase tracking-wide ${color}`}>{label}</h4>
          </div>
          <span className="text-xs font-bold text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
            {tasks.length}
          </span>
        </div>
      </div>
      <div className="flex-1 px-2.5 pb-2.5 space-y-2 overflow-y-auto max-h-[280px]">
        {isLoading ? (
          <div className="space-y-2 animate-pulse">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-14 bg-gray-200 rounded-lg" />
            ))}
          </div>
        ) : visible.length === 0 ? (
          <div className="flex items-center justify-center h-20 text-xs text-gray-400">Нет задач</div>
        ) : (
          visible.map((task) => <TaskCard key={task.id} task={task} />)
        )}
      </div>
      {hasMore && (
        <div className="px-2.5 pb-2.5">
          <Link to={`/tasks?status=${status}`} className="text-xs text-primary hover:underline">
            Все →
          </Link>
        </div>
      )}
    </div>
  )
}

function TasksBoard() {
  const { data: tasks, isLoading, isError, error, refetch } = useTasksQuery({ limit: 100 })

  const grouped = useMemo(() => {
    const all = tasks ?? []
    const map: Record<TaskStatus, Task[]> = {
      new: [],
      in_progress: [],
      completed: [],
      cancelled: [],
    }
    for (const task of all) {
      if (map[task.status]) map[task.status].push(task)
    }
    return map
  }, [tasks])

  if (isError) {
    return (
      <Card title="Задачи">
        <div className="flex flex-col items-center gap-3 py-6 text-center">
          <AlertCircle className="text-red-500" size={32} />
          <p className="text-gray-600">{error instanceof Error ? error.message : 'Ошибка загрузки задач'}</p>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 text-sm text-primary hover:underline"
          >
            <RefreshCw size={14} />
            Повторить
          </button>
        </div>
      </Card>
    )
  }

  return (
    <Card title="Задачи">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {DASHBOARD_STATUSES.map((s) => (
          <StatusColumn
            key={s.status}
            status={s.status}
            label={s.label}
            color={s.color}
            dot={s.dot}
            tasks={grouped[s.status]}
            isLoading={isLoading}
          />
        ))}
      </div>
      <div className="text-right mt-2">
        <Link to="/tasks" className="text-xs text-primary hover:underline">
          Все задачи →
        </Link>
      </div>
    </Card>
  )
}

export default TasksBoard
