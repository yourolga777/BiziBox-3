import { useState } from 'react'
import { Dialog } from '@headlessui/react'
import { useFoldersQuery } from '../../hooks/queries'
import { contactApi } from '../../api/client'
import type { BulkUpdateRequest } from '../../types/contact'

export default function BulkEditDialog({
  open,
  onClose,
  selectedIds,
}: {
  open: boolean
  onClose: () => void
  selectedIds: number[]
}) {
  const { data: folders = [] } = useFoldersQuery()
  const [folderId, setFolderId] = useState<number | null>(null)
  const [isFavorite, setIsFavorite] = useState<boolean | null>(null)
  const [saving, setSaving] = useState(false)

  const hasChanges = folderId !== null || isFavorite !== null

  const handleSave = async () => {
    if (!hasChanges) return
    setSaving(true)
    const data: BulkUpdateRequest = { ids: selectedIds }
    if (folderId !== null) data.folder_id = folderId
    if (isFavorite !== null) data.is_favorite = isFavorite
    await contactApi.bulkUpdate(data)
    setSaving(false)
    onClose()
  }

  return (
    <Dialog open={open} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="w-full max-w-sm bg-white rounded-xl p-6">
          <Dialog.Title className="text-lg font-semibold mb-4">
            Изменить {selectedIds.length} контактов
          </Dialog.Title>

          <div className="space-y-4">
            <div>
              <label htmlFor="bulk-folder" className="block text-sm font-medium text-gray-700 mb-1">Изменить папку</label>
              <select
                id="bulk-folder"
                value={folderId === null ? '' : String(folderId)}
                onChange={e => {
                  const v = e.target.value
                  setFolderId(v === '' ? null : Number(v))
                }}
                className="w-full px-3 py-2 border rounded-lg text-sm"
              >
                <option value="">Не менять</option>
                {folders.map(f => (
                  <option key={f.id} value={f.id}>{f.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="bulk-is-favorite" className="block text-sm font-medium text-gray-700 mb-1">Избранное</label>
              <select
                id="bulk-is-favorite"
                value={isFavorite === null ? '' : String(isFavorite)}
                onChange={e => {
                  const v = e.target.value
                  setIsFavorite(v === '' ? null : v === 'true')
                }}
                className="w-full px-3 py-2 border rounded-lg text-sm"
              >
                <option value="">Не менять</option>
                <option value="true">Добавить в избранное</option>
                <option value="false">Убрать из избранного</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <button onClick={onClose} className="px-4 py-2 text-sm border rounded-lg">Отмена</button>
            <button
              onClick={handleSave}
              disabled={!hasChanges || saving}
              className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg disabled:opacity-50"
            >
              {saving ? 'Сохранение...' : 'Применить'}
            </button>
          </div>
        </Dialog.Panel>
      </div>
    </Dialog>
  )
}
