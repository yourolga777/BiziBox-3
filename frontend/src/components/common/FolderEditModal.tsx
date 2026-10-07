import { useState } from 'react'
import { X } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { contactApi } from '../../api/client'
import { useToast } from './Toast'
import type { ContactFolder } from '../../types/contact'

const PRESET_COLORS = [
  '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
  '#ec4899', '#06b6d4', '#f97316', '#6366f1', '#14b8a6',
  '#84cc16', '#a855f7',
]

interface Props {
  folder: ContactFolder
  onClose: () => void
}

export default function FolderEditModal({ folder, onClose }: Props) {
  const { showToast } = useToast()
  const queryClient = useQueryClient()
  const [name, setName] = useState(folder.name)
  const [color, setColor] = useState(folder.color || '#6b7280')
  const [nameError, setNameError] = useState('')

  const handleSave = async () => {
    const trimmed = name.trim()
    if (!trimmed) {
      setNameError('Название не может быть пустым')
      return
    }
    try {
      await contactApi.updateFolder(folder.id, { name: trimmed, color: color || null })
      queryClient.invalidateQueries({ queryKey: ['folders'] })
      showToast('Папка обновлена', 'success')
      onClose()
    } catch {
      showToast('Ошибка при обновлении', 'error')
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/40" role="button" tabIndex={0} onClick={onClose} onKeyDown={(e) => e.key === 'Enter' && onClose()} />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-sm p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-gray-900">Редактировать папку</h3>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="color"
            value={color}
            onChange={(e) => setColor(e.target.value)}
            className="w-6 h-6 rounded border-0 p-0 cursor-pointer shrink-0"
          />
          <input
            type="text"
            value={name}
            onChange={(e) => { setName(e.target.value); setNameError('') }}
            className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-primary focus:ring-1 focus:ring-primary outline-none"
            onKeyDown={(e) => e.key === 'Enter' && handleSave()}
          />
        </div>
        <div className="flex items-center gap-1.5">
          {PRESET_COLORS.map((preset) => (
            <button
              key={preset}
              onClick={() => setColor(preset)}
              className={`w-5 h-5 rounded-full border-2 transition-colors ${color === preset ? 'border-gray-400 scale-110' : 'border-transparent'}`}
              style={{ backgroundColor: preset }}
              title={preset}
            />
          ))}
        </div>
        {nameError && <p className="text-xs text-red-500">{nameError}</p>}
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50"
          >
            Отмена
          </button>
          <button
            onClick={handleSave}
            className="px-3 py-1.5 text-sm font-medium rounded-lg bg-primary text-white hover:bg-primary/90"
          >
            Сохранить
          </button>
        </div>
      </div>
    </div>
  )
}
