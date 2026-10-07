export type CalendarFilter = 'all' | 'active' | 'completed'

interface CalendarFiltersProps {
  filter: CalendarFilter
  onChange: (f: CalendarFilter) => void
}

const filters: { value: CalendarFilter; label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'active', label: 'Активные' },
  { value: 'completed', label: 'Выполненные' },
]

export function CalendarFilters({ filter, onChange }: CalendarFiltersProps) {
  return (
    <div className="flex items-center gap-2 mb-4">
      {filters.map((f) => (
        <button
          key={f.value}
          onClick={() => onChange(f.value)}
          className={`px-3 py-1.5 text-sm rounded-lg font-medium transition-colors ${
            filter === f.value
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          {f.label}
        </button>
      ))}
    </div>
  )
}
