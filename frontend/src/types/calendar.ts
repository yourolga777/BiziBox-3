export interface CalendarEvent {
  id: number
  type: 'task' | 'event' | 'birthday'
  title: string
  date: string
  time: string | null
  status: string
  contact_name: string | null
  is_overdue: boolean
  metadata: Record<string, unknown>
}

export interface CalendarEventsResponse {
  events: CalendarEvent[]
}

export interface CalendarEventResponse {
  id: number
  contact_id: number | null
  contact_name?: string | null
  title: string
  date: string
  time: string | null
  description: string | null
  reminder_minutes: number | null
  recurrence: string | null
  created_at: string | null
  updated_at: string | null
}

export interface CalendarEventCreate {
  title: string
  date: string
  time?: string | null
  description?: string | null
  reminder_minutes?: number | null
  recurrence?: string | null
  contact_id?: number | null
}

export interface CalendarEventUpdate {
  title?: string
  date?: string
  time?: string | null
  description?: string | null
  reminder_minutes?: number | null
  recurrence?: string | null
  contact_id?: number | null
}
