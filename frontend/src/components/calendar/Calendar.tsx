import { useCallback, useEffect, useMemo, useState } from 'react'
import { addDays, addMonths, eachDayOfInterval, endOfMonth, format, startOfMonth, startOfWeek, subMonths } from 'date-fns'
import { ru } from 'date-fns/locale'
import { DndContext, DragEndEvent, DragOverlay, DragStartEvent, PointerSensor, useSensor, useSensors } from '@dnd-kit/core'
import { ChevronLeft, ChevronRight, CalendarClock, ListTodo, Cake } from 'lucide-react'
import { taskApi, contactApi } from '../../api/client'
import { calendarApi } from '../../api/calendar'
import { useContactsQuery } from '../../hooks/queries'
import ContactCombobox from '../contacts/ContactCombobox'
import type { CalendarEvent as CalendarEventType } from '../../types/calendar'
import type { Contact } from '../../types/contact'
import { CalendarDay } from './CalendarDay'
import { CalendarEvent as CalendarEventComponent } from './CalendarEvent'
import { CalendarEventDetail } from './CalendarEventDetail'
import { CalendarFilters, type CalendarFilter } from './CalendarFilters'
import { CalendarModal } from './CalendarModal'
import TaskCreateModal from '../tasks/TaskCreateModal'

type ViewMode = 'month' | 'week' | 'day'

const VIEW_OPTIONS: { key: ViewMode; label: string }[] = [
  { key: 'month', label: 'Месяц' },
  { key: 'week', label: 'Неделя' },
  { key: 'day', label: 'День' },
]

export function Calendar() {
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [selectedDate, setSelectedDate] = useState<Date>(new Date())
  const [view, setView] = useState<ViewMode>('month')
  const [events, setEvents] = useState<CalendarEventType[]>([])
  const [filter, setFilter] = useState<CalendarFilter>('all')
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [selectedEvent, setSelectedEvent] = useState<CalendarEventType | null>(null)
  const [isDetailOpen, setIsDetailOpen] = useState(false)
  const [draggedEvent, setDraggedEvent] = useState<CalendarEventType | null>(null)
  const [dayMenu, setDayMenu] = useState<Date | null>(null)
  const [isTaskOpen, setIsTaskOpen] = useState(false)
  const [isBirthdayOpen, setIsBirthdayOpen] = useState(false)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
  )

  const start = startOfMonth(currentMonth)
  const end = endOfMonth(currentMonth)
  const days = eachDayOfInterval({ start, end })

  const monthPadStart = start.getDay() === 0 ? 6 : start.getDay() - 1
  const padStart = Array.from({ length: monthPadStart }, (_, i) => {
    const d = new Date(start)
    d.setDate(d.getDate() - (monthPadStart - i))
    return d
  })

  const loadEvents = useCallback(async () => {
    try {
      const s = format(start, 'yyyy-MM-dd')
      const e = format(end, 'yyyy-MM-dd')
      const data = await calendarApi.getEvents(s, e)
      setEvents(data.events)
    } catch (err) {
      console.error('Failed to load calendar events', err)
    }
  }, [start, end])

  useEffect(() => { loadEvents() }, [loadEvents])

  const filteredEvents = events.filter((ev) => {
    if (filter === 'active') return ev.status !== 'completed' && ev.status !== 'cancelled'
    if (filter === 'completed') return ev.status === 'completed'
    return true
  })

  const eventsByDate = useMemo(() => {
    const map = new Map<string, CalendarEventType[]>()
    filteredEvents.forEach((ev) => {
      const existing = map.get(ev.date) || []
      existing.push(ev)
      map.set(ev.date, existing)
    })
    return map
  }, [filteredEvents])

  const weekDays = useMemo(() => {
    const ws = startOfWeek(selectedDate, { weekStartsOn: 1 })
    return eachDayOfInterval({ start: ws, end: addDays(ws, 6) })
  }, [selectedDate])

  const handlePrev = () => {
    if (view === 'month') setCurrentMonth((m) => subMonths(m, 1))
    if (view === 'week') setSelectedDate((d) => addDays(d, -7))
    if (view === 'day') setSelectedDate((d) => addDays(d, -1))
  }

  const handleNext = () => {
    if (view === 'month') setCurrentMonth((m) => addMonths(m, 1))
    if (view === 'week') setSelectedDate((d) => addDays(d, 7))
    if (view === 'day') setSelectedDate((d) => addDays(d, 1))
  }

  const handleToday = () => {
    setCurrentMonth(new Date())
    setSelectedDate(new Date())
  }

  const handleDayClick = (date: Date) => {
    setSelectedDate(date)
    setDayMenu(date)
  }

  const handleEventClick = (event: CalendarEventType) => {
    setSelectedEvent(event)
    setIsDetailOpen(true)
  }

  const handleDragStart = (event: DragStartEvent) => {
    const taskId = Number(event.active.id.toString().replace('task-', ''))
    const ev = events.find((e) => e.id === taskId)
    if (ev) setDraggedEvent(ev)
  }

  const handleDragEnd = async (event: DragEndEvent) => {
    setDraggedEvent(null)
    const { active, over } = event
    if (!over) return

    const taskId = Number(active.id.toString().replace('task-', ''))
    const newDate = over.id.toString()
    if (!newDate) return

    try {
      await taskApi.update(taskId, { due_date: newDate })
      loadEvents()
    } catch (err) {
      console.error('Failed to update task date', err)
    }
  }

  const allDays = [...padStart, ...days]

  const renderDayEvents = (day: Date) => {
    const key = format(day, 'yyyy-MM-dd')
    return eventsByDate.get(key) || []
  }

  return (
    <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
      <div className="space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <button onClick={handlePrev} className="p-2 hover:bg-gray-100 rounded-lg">
              <ChevronLeft size={18} />
            </button>
            <h2 className="text-xl font-bold text-gray-900 min-w-[200px] text-center">
              {view === 'month' && format(currentMonth, 'LLLL yyyy', { locale: ru })}
              {view === 'week' && `${format(weekDays[0], 'd MMM', { locale: ru })} — ${format(weekDays[6], 'd MMM yyyy', { locale: ru })}`}
              {view === 'day' && format(selectedDate, 'd MMMM yyyy', { locale: ru })}
            </h2>
            <button onClick={handleNext} className="p-2 hover:bg-gray-100 rounded-lg">
              <ChevronRight size={18} />
            </button>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
              {VIEW_OPTIONS.map((opt) => (
                <button
                  key={opt.key}
                  onClick={() => setView(opt.key)}
                  className={`px-3 py-1.5 text-sm rounded-md font-medium transition-colors ${
                    view === opt.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <button onClick={handleToday} className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100">
              Сегодня
            </button>
          </div>
        </div>

        <CalendarFilters filter={filter} onChange={setFilter} />

        {view === 'month' && (
          <div className="grid grid-cols-7 gap-1">
            {['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].map((day) => (
              <div key={day} className="text-center text-sm font-medium text-gray-500 py-2">
                {day}
              </div>
            ))}
            {allDays.map((day) => (
              <CalendarDay
                key={day.toISOString()}
                date={day}
                events={renderDayEvents(day)}
                onDayClick={handleDayClick}
                onEventClick={handleEventClick}
              />
            ))}
          </div>
        )}

        {view === 'week' && (
          <div className="grid grid-cols-7 gap-1">
            {weekDays.map((day) => (
              <CalendarDay
                key={day.toISOString()}
                date={day}
                events={renderDayEvents(day)}
                onDayClick={handleDayClick}
                onEventClick={handleEventClick}
              />
            ))}
          </div>
        )}

        {view === 'day' && (
          <div className="space-y-2">
            <CalendarDay
              date={selectedDate}
              events={renderDayEvents(selectedDate)}
              onDayClick={handleDayClick}
              onEventClick={handleEventClick}
            />
          </div>
        )}

        <CalendarModal
          isOpen={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
          date={selectedDate}
          onCreated={loadEvents}
        />

        <TaskCreateModal
          open={isTaskOpen}
          onClose={() => setIsTaskOpen(false)}
          initialDate={format(selectedDate, "yyyy-MM-dd") + 'T09:00'}
          onCreated={loadEvents}
        />

        {isBirthdayOpen && (
          <BirthdayDialog
            date={selectedDate}
            onClose={() => setIsBirthdayOpen(false)}
            onCreated={loadEvents}
          />
        )}

        {dayMenu && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <button type="button" aria-label="Закрыть" tabIndex={-1} className="fixed inset-0 bg-black/30" onClick={() => setDayMenu(null)} />
            <div className="relative bg-white rounded-xl shadow-xl p-4 w-full max-w-xs">
              <p className="text-sm font-semibold text-gray-900 mb-3">
                {format(dayMenu, 'd MMMM yyyy', { locale: ru })}
              </p>
              <div className="space-y-1">
                <button
                  onClick={() => { setIsCreateOpen(true); setDayMenu(null) }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left rounded-lg hover:bg-indigo-50 text-gray-700"
                >
                  <CalendarClock className="w-4 h-4 text-indigo-500" />
                  Создать событие
                </button>
                <button
                  onClick={() => { setIsTaskOpen(true); setDayMenu(null) }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left rounded-lg hover:bg-amber-50 text-gray-700"
                >
                  <ListTodo className="w-4 h-4 text-amber-500" />
                  Создать задачу
                </button>
                <button
                  onClick={() => { setIsBirthdayOpen(true); setDayMenu(null) }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left rounded-lg hover:bg-pink-50 text-gray-700"
                >
                  <Cake className="w-4 h-4 text-pink-500" />
                  Добавить день рождения
                </button>
              </div>
            </div>
          </div>
        )}

        <CalendarEventDetail
          event={selectedEvent}
          isOpen={isDetailOpen}
          onClose={() => setIsDetailOpen(false)}
          onUpdated={loadEvents}
        />

        <DragOverlay>
          {draggedEvent ? (
            <div className="opacity-80">
              <CalendarEventComponent event={draggedEvent} />
            </div>
          ) : null}
        </DragOverlay>
      </div>
    </DndContext>
  )
}

function toDateInput(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function BirthdayDialog({
  date,
  onClose,
  onCreated,
}: {
  date: Date
  onClose: () => void
  onCreated: () => void
}) {
  const [contactId, setContactId] = useState<number | null>(null)
  const [dateValue, setDateValue] = useState(toDateInput(date))
  const [saving, setSaving] = useState(false)
  const { data: contacts = [] } = useContactsQuery()

  const handleSave = async () => {
    if (!contactId) return
    setSaving(true)
    try {
      await contactApi.update(contactId, { birthday: dateValue })
      onCreated()
      onClose()
    } catch {
      // ignore
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button type="button" aria-label="Закрыть" tabIndex={-1} className="fixed inset-0 bg-black/30" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-xl p-5 w-full max-w-sm">
        <p className="text-lg font-semibold text-gray-900 mb-4">День рождения</p>
        <div className="space-y-4">
          <ContactCombobox
            id="birthday-contact"
            label="Контакт"
            contacts={contacts as Contact[]}
            value={contactId}
            onChange={setContactId}
            placeholder="Поиск контакта..."
          />
          <div>
            <label htmlFor="birthday-date" className="block text-sm font-medium text-gray-700 mb-1">Дата рождения</label>
            <input
              id="birthday-date"
              type="date"
              value={dateValue}
              onChange={(e) => setDateValue(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={onClose} className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">Отмена</button>
            <button
              onClick={handleSave}
              disabled={!contactId || saving}
              className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Сохранение...' : 'Сохранить'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
