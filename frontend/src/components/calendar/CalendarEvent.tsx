import { useDraggable } from '@dnd-kit/core'
import { AlertCircle, Cake, CheckCircle2, ClipboardList, CalendarClock } from 'lucide-react'
import type { CalendarEvent as CalendarEventType } from '../../types/calendar'

interface CalendarEventProps {
  event: CalendarEventType
}

function eventAppearance(event: CalendarEventType): { icon: React.ReactNode; bg: string } {
  if (event.type === 'birthday') {
    return { icon: <Cake size={12} className="text-pink-500 shrink-0" />, bg: 'bg-pink-50 text-pink-700' }
  }
  if (event.type === 'event') {
    return { icon: <CalendarClock size={12} className="text-indigo-500 shrink-0" />, bg: 'bg-indigo-50 text-indigo-700' }
  }
  if (event.status === 'completed') {
    return { icon: <CheckCircle2 size={12} className="text-gray-400 shrink-0" />, bg: 'bg-gray-100 text-gray-500' }
  }
  if (event.is_overdue) {
    return { icon: <AlertCircle size={12} className="text-red-500 shrink-0" />, bg: 'bg-red-50 text-red-700' }
  }
  return { icon: <ClipboardList size={12} className="text-blue-500 shrink-0" />, bg: 'bg-blue-50 text-blue-700' }
}

export function CalendarEvent({ event }: CalendarEventProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `task-${event.id}`,
    data: { taskId: event.id, date: event.date },
  })

  const style = transform ? {
    transform: `translate(${transform.x}px, ${transform.y}px)`,
    zIndex: 50,
  } : undefined

  const { icon, bg } = eventAppearance(event)

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      style={style}
      className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-xs cursor-grab active:cursor-grabbing truncate ${bg} ${isDragging ? 'opacity-50 shadow-lg' : ''}`}
    >
      {icon}
      {event.time && <span className="text-[10px] opacity-70 shrink-0">{event.time}</span>}
      <span className="truncate">{event.title}</span>
    </div>
  )
}
