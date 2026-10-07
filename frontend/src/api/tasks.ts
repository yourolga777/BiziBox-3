import type { Task, TaskComment, TaskCreate, TaskDetail, TaskUpdate } from '../types/task'
import { request } from './client'

export const taskApi = {
  getAll: (params?: { status?: string; contact_id?: number; skip?: number; limit?: number }) => {
    const search = new URLSearchParams()
    if (params?.status) search.set('status', params.status)
    if (params?.contact_id) search.set('contact_id', String(params.contact_id))
    if (params?.skip) search.set('skip', String(params.skip))
    if (params?.limit) search.set('limit', String(params.limit))
    const qs = search.toString()
    return request<Task[]>(`/tasks${qs ? `?${qs}` : ''}`)
  },

  getArchived: (params?: { skip?: number; limit?: number }) => {
    const search = new URLSearchParams()
    if (params?.skip) search.set('skip', String(params.skip))
    if (params?.limit) search.set('limit', String(params.limit))
    const qs = search.toString()
    return request<Task[]>(`/tasks/archive${qs ? `?${qs}` : ''}`)
  },

  getById: (id: number) => request<TaskDetail>(`/tasks/${id}`),

  getComments: (taskId: number) => request<TaskComment[]>(`/tasks/${taskId}/comments`),

  addComment: (taskId: number, content: string) =>
    request<TaskComment>(`/tasks/${taskId}/comments`, { method: 'POST', body: JSON.stringify({ content }) }),

  deleteComment: (taskId: number, commentId: number) =>
    request<void>(`/tasks/${taskId}/comments/${commentId}`, { method: 'DELETE', _entityId: taskId }),

  create: (data: TaskCreate) =>
    request<Task>('/tasks/', { method: 'POST', body: JSON.stringify(data) }),

  update: (id: number, data: TaskUpdate) =>
    request<Task>(`/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(data), _entityId: id }),

  delete: (id: number) =>
    request<void>(`/tasks/${id}`, { method: 'DELETE', _entityId: id }),

  restore: (id: number) =>
    request<Task>(`/tasks/${id}/restore`, { method: 'POST' }),

  bulkDelete: (ids: number[]) =>
    request<{ deleted: number }>('/tasks/bulk-delete', { method: 'POST', body: JSON.stringify(ids) }),

  bulkRestore: (ids: number[]) =>
    request<{ restored: number }>('/tasks/bulk-restore', { method: 'POST', body: JSON.stringify(ids) }),
}
