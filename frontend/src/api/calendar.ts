import { request } from './client'
import type { CalendarEventsResponse, CalendarEventCreate, CalendarEventUpdate, CalendarEventResponse } from '../types/calendar'

export const calendarApi = {
  getEvents: (start: string, end: string) => {
    const params = new URLSearchParams({ start, end })
    return request<CalendarEventsResponse>(`/calendar/events?${params}`)
  },

  createEvent: (data: CalendarEventCreate) =>
    request<CalendarEventResponse>('/calendar/events', { method: 'POST', body: JSON.stringify(data) }),

  updateEvent: (id: number, data: CalendarEventUpdate) =>
    request<CalendarEventResponse>(`/calendar/events/${id}`, { method: 'PATCH', body: JSON.stringify(data), _entityId: id }),

  deleteEvent: (id: number) =>
    request<void>(`/calendar/events/${id}`, { method: 'DELETE', _entityId: id }),
}
