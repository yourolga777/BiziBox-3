export type TaskStatus = 'new' | 'in_progress' | 'completed' | 'cancelled'

export interface Task {
  id: number
  contact_id: number | null
  message_id?: number | null
  title: string
  description: string | null
  status: TaskStatus
  due_date: string | null
  reminder_minutes?: number | null
  recurrence?: string | null
  repeat_dates?: string[] | null
  repeat_until?: string | null
  created_at: string | null
  updated_at: string | null
}

export const TASK_STATUSES: TaskStatus[] = [
  'new',
  'in_progress',
  'completed',
  'cancelled',
]

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  new: 'Новая',
  in_progress: 'В работе',
  completed: 'Выполнена',
  cancelled: 'Отменена',
}

export interface TaskCreate {
  title: string
  description?: string | null
  contact_id?: number | null
  message_id?: number | null
  due_date?: string | null
  status?: TaskStatus
  reminder_minutes?: number | null
  recurrence?: string | null
  repeat_dates?: string[] | null
  repeat_until?: string | null
}

export interface TaskUpdate {
  title?: string
  description?: string | null
  contact_id?: number | null
  due_date?: string | null
  status?: TaskStatus
  reminder_minutes?: number | null
  recurrence?: string | null
  repeat_dates?: string[] | null
  repeat_until?: string | null
}

export interface TaskComment {
  id: number
  task_id: number
  content: string
  created_at: string | null
}

export interface TaskDetail extends Task {
  contact_name: string | null
  comments: TaskComment[]
}
