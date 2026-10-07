import { useState } from 'react'
import { useDroppable } from '@dnd-kit/core'
import { format, isToday } from 'date-fns'
import { ru } from 'date-fns/locale'
import type { CalendarEvent as CalendarEventType } from '../../types/calendar'
import { CalendarEvent } from './CalendarEvent'

interface CalendarDayProps {
  date: Date
  events: CalendarEventType[]
  onDayClick: (date: Date) => void
  onEventClick: (event: CalendarEventType) => void
}

export function CalendarDay({ date, events, onDayClick, onEventClick }: CalendarDayProps) {
  const [showAll, setShowAll] = useState(false)
  const dateStr = format(date, 'yyyy-MM-dd')
  const { setNodeRef, isOver } = useDroppable({ id: dateStr })

  const today = isToday(date)
  const visible = events.slice(0, 3)
  const hasMore = events.length > 3

  return (
    <div
      ref={setNodeRef}
      role="button"
      tabIndex={0}
      className={`min-h-[90px] p-1.5 border rounded cursor-pointer transition-colors relative ${
        isOver ? 'bg-blue-50 border-blue-400' : 'border-gray-200'
      } ${today ? 'bg-blue-50/50 border-blue-400' : ''}`}
      onClick={() => onDayClick(date)}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onDayClick(date) }}
    >
      <div className={`text-sm font-medium mb-1 ${today ? 'text-blue-600' : 'text-gray-700'}`}>
        {format(date, 'd', { locale: ru })}
      </div>
      <div role="none" className="space-y-0.5" onClick={(e) => e.stopPropagation()}>
        {visible.map((event) => (
          <div key={event.id} role="button" tabIndex={0} onClick={() => onEventClick(event)} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onEventClick(event) }}>
            <CalendarEvent event={event} />
          </div>
        ))}
        {hasMore && (
          <span
            role="button"
            tabIndex={0}
            className="text-xs text-gray-500 cursor-pointer hover:underline block mt-0.5"
            onClick={(e) => { e.stopPropagation(); setShowAll(!showAll) }}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.stopPropagation(); setShowAll(!showAll) } }}
          >
            +{events.length - 3} ещё
          </span>
        )}
        {showAll && (
          <div role="none" className="absolute z-20 bg-white border rounded-lg shadow-lg p-2 mt-1 left-0 right-0" onClick={(e) => e.stopPropagation()}>
            {events.map((event) => (
              <div key={event.id} className="mb-0.5" role="button" tabIndex={0} onClick={() => onEventClick(event)} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onEventClick(event) }}>
                <CalendarEvent event={event} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
