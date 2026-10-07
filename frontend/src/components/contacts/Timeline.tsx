import { ShoppingCart, ListTodo, ExternalLink } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useTimelineQuery } from '../../hooks/queries'

const typeIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  order: ShoppingCart,
  task: ListTodo,
}

export default function Timeline({
  contactId,
}: {
  contactId: number
}) {
  const { data: events = [] } = useTimelineQuery(contactId)
  const navigate = useNavigate()

  const filtered = events.filter(e => e.type === 'order' || e.type === 'task')

  if (filtered.length === 0) return (
    <p className="text-xs text-gray-400 text-center py-4">Нет активности</p>
  )

  return (
    <div className="space-y-0">
      {filtered.map((event, idx) => {
        const Icon = typeIcons[event.type] || ShoppingCart
        return (
          <div key={idx} className="flex gap-2 py-1.5 border-b border-gray-50 last:border-0">
            <div className="mt-0.5 shrink-0">
              <Icon className="w-3.5 h-3.5 text-gray-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-gray-700">{event.title}</p>
              <p className="text-xs text-gray-400 truncate">{event.subtitle}</p>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <span className="text-xs text-gray-400">
                {event.created_at ? new Date(event.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
              </span>
              {event.link && (
                <button
                  onClick={() => navigate(event.link!)}
                  className="p-0.5 text-gray-400 hover:text-blue-600 rounded"
                >
                  <ExternalLink className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
