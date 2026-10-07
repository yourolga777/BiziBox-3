import { Merge, Trash2, Pencil } from 'lucide-react'

export default function BulkActionBar({
  selectedCount,
  onMerge,
  onDelete,
  onEdit,
  onClear,
}: {
  selectedCount: number
  onMerge: () => void
  onDelete: () => void
  onEdit: () => void
  onClear: () => void
}) {
  if (selectedCount === 0) return null

  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-blue-50 border border-blue-200 rounded-lg">
      <span className="text-sm font-medium text-blue-800">
        Выбрано: {selectedCount}
      </span>
      <button
        onClick={onEdit}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-green-700 bg-white border border-green-300 rounded-lg hover:bg-green-100"
      >
        <Pencil className="w-4 h-4" />
        Изменить
      </button>
      <button
        onClick={onMerge}
        disabled={selectedCount < 2}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-blue-700 bg-white border border-blue-300 rounded-lg hover:bg-blue-100 disabled:opacity-50"
      >
        <Merge className="w-4 h-4" />
        Объединить
      </button>
      <button
        onClick={onDelete}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-red-700 bg-white border border-red-300 rounded-lg hover:bg-red-100"
      >
        <Trash2 className="w-4 h-4" />
        Удалить
      </button>
      <button
        onClick={onClear}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-100 ml-auto"
      >
        Снять выделение
      </button>
    </div>
  )
}
