import { useState } from 'react'
import { ListTodo, CalendarPlus } from 'lucide-react'
import { Calendar } from '../components/calendar/Calendar'
import { CalendarModal } from '../components/calendar/CalendarModal'
import TaskCreateModal from '../components/tasks/TaskCreateModal'

export function CalendarPage() {
  const [eventOpen, setEventOpen] = useState(false)
  const [taskOpen, setTaskOpen] = useState(false)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Календарь</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setTaskOpen(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-lg hover:bg-amber-100 transition-colors"
          >
            <ListTodo className="w-4 h-4" />
            Задача
          </button>
          <button
            onClick={() => setEventOpen(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition-colors"
          >
            <CalendarPlus className="w-4 h-4" />
            Событие
          </button>
        </div>
      </div>
      <Calendar />

      <CalendarModal
        isOpen={eventOpen}
        onClose={() => setEventOpen(false)}
        date={new Date()}
        onCreated={() => setEventOpen(false)}
      />

      <TaskCreateModal
        open={taskOpen}
        onClose={() => setTaskOpen(false)}
        onCreated={() => setTaskOpen(false)}
      />
    </div>
  )
}
