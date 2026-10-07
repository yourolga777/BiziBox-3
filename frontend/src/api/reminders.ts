import { request } from './client'

export interface Reminder {
  kind: 'task' | 'event'
  id: number
  title: string
  fired_at: string | null
  recurrence: string | null
  when: string | null
}

export const reminderApi = {
  getReminders: () => request<Reminder[]>('/reminders/'),
  ackReminder: (kind: string, id: number) =>
    request<{ acked: boolean }>(`/reminders/${kind}/${id}/ack`, { method: 'POST' }),
}
