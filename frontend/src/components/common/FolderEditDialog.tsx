import { useState, useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import { contactApi } from '../../api/client'
import { useToast } from '../../components/common/Toast'
import { useFoldersQuery } from '../../hooks/queries'
import { useQueryClient } from '@tanstack/react-query'
import { CONTACT_SPHERE_META } from '../../types/contactType'
import FolderTree from '../../components/common/FolderTree'
import FolderEditModal from './FolderEditModal'
import type { ContactFolder, ContactSphere } from '../../types/contact'

const PRESET_COLORS = [
  '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
  '#ec4899', '#06b6d4', '#f97316', '#6366f1', '#14b8a6',
  '#84cc16', '#a855f7',
]

interface Props {
  open: boolean
  onClose: () => void
  initialMode?: 'create' | 'manage'
}

export default function FolderEditDialog({ open, onClose, initialMode = 'manage' }: Props) {
  const { showToast } = useToast()
  const queryClient = useQueryClient()
  const { data: allFolders = [] } = useFoldersQuery()
  const [editingFolder, setEditingFolder] = useState<ContactFolder | null>(null)
  const [newName, setNewName] = useState('')
  const [newColor, setNewColor] = useState('#3b82f6')
  const [newType, setNewType] = useState<ContactSphere>('personal')
  const [newParent, setNewParent] = useState<number | null>(null)
  const [nameError, setNameError] = useState('')
  const [pendingDelete, setPendingDelete] = useState<ContactFolder | null>(null)
  const newNameRef = useRef<HTMLInputElement>(null)

  const mode = initialMode === 'create' ? 'create' : 'manage'

  const parentCandidates = allFolders.filter(
    f => (f.sphere || 'personal') === newType && !f.parent_id,
  )

  useEffect(() => {
    setNameError('')
    setNewName('')
    setNewParent(null)
    setEditingFolder(null)
    setPendingDelete(null)
  }, [open])

  useEffect(() => {
    if (open && mode === 'create') {
      newNameRef.current?.focus()
    }
  }, [open, mode])

  const handleDelete = async (folder: ContactFolder) => {
    if (folder.is_default) return
    setPendingDelete(folder)
  }

  const confirmDelete = async () => {
    if (!pendingDelete) return
    try {
      await contactApi.deleteFolder(pendingDelete.id)
      queryClient.invalidateQueries({ queryKey: ['folders'] })
      showToast('Папка удалена', 'success')
      setPendingDelete(null)
    } catch {
      showToast('Ошибка при удалении', 'error')
      setPendingDelete(null)
    }
  }

  const handleCreate = async () => {
    const trimmed = newName.trim()
    if (!trimmed) {
      setNameError('Введите название папки')
      return
    }
    setNameError('')
    try {
      await contactApi.createFolder({
        name: trimmed,
        color: newColor,
        sphere: newType,
        parent_id: newParent,
      })
      queryClient.invalidateQueries({ queryKey: ['folders'] })
      showToast('Папка создана', 'success')
      onClose()
    } catch {
      showToast('Ошибка при создании', 'error')
    }
  }

  const handleReorder = async (ids: number[]) => {
    try {
      await contactApi.reorderFolders(ids)
      queryClient.invalidateQueries({ queryKey: ['folders'] })
    } catch {
      showToast('Не удалось изменить порядок', 'error')
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]">
      <div className="absolute inset-0 bg-black/40" role="button" tabIndex={0} onClick={onClose} onKeyDown={(e) => e.key === 'Enter' && onClose()} />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">{mode === 'create' ? 'Новая папка' : 'Папки'}</h2>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        {mode === 'create' ? (
          <div className="px-5 py-4 space-y-3">
            <div className="flex items-center gap-2">
              <input
                type="text"
                ref={newNameRef}
                value={newName}
                onChange={(e) => { setNewName(e.target.value); setNameError('') }}
                placeholder="Название новой папки"
                className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              />
            </div>
            <div className="flex items-center gap-1.5">
              {PRESET_COLORS.map((color) => (
                <button
                  key={color}
                  onClick={() => setNewColor(color)}
                  className={`w-6 h-6 rounded-full border-2 transition-colors ${newColor === color ? 'border-gray-400 scale-110' : 'border-transparent'}`}
                  style={{ backgroundColor: color }}
                  title={color}
                />
              ))}
            </div>
            <div>
              <label htmlFor="folder-create-type" className="block text-xs font-medium text-gray-500 mb-1">Сфера</label>
              <select
                id="folder-create-type"
                value={newType}
                onChange={e => { setNewType(e.target.value as ContactSphere); setNewParent(null) }}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-primary focus:ring-1 focus:ring-primary outline-none"
              >
                <option value="personal">{CONTACT_SPHERE_META.personal.label}</option>
                <option value="work">{CONTACT_SPHERE_META.work.label}</option>
                <option value="channels">{CONTACT_SPHERE_META.channels.label}</option>
              </select>
            </div>
            {parentCandidates.length > 0 && (
              <div>
                <label htmlFor="folder-create-parent" className="block text-xs font-medium text-gray-500 mb-1">Внутри папки</label>
                <select
                  id="folder-create-parent"
                  value={newParent === null ? '' : String(newParent)}
                  onChange={e => setNewParent(e.target.value === '' ? null : Number(e.target.value))}
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                >
                  <option value="">Без родительской папки</option>
                  {parentCandidates.map(f => (
                    <option key={f.id} value={f.id}>{f.name}</option>
                  ))}
                </select>
              </div>
            )}
            {nameError && <p className="text-xs text-red-500">{nameError}</p>}
            <div className="flex justify-end gap-2 pt-1">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50"
              >
                Отмена
              </button>
              <button
                onClick={handleCreate}
                disabled={!newName.trim()}
                className="shrink-0 px-4 py-2 text-sm font-medium rounded-lg bg-primary text-white hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Создать
              </button>
            </div>
          </div>
        ) : (
        <>
        <div className="px-5 py-3 space-y-2 max-h-[50vh] overflow-y-auto">
          <FolderTree
            folders={allFolders}
            groupBySphere
            onEdit={setEditingFolder}
            onDelete={handleDelete}
            onReorder={handleReorder}
          />
        </div>

        <div className="px-5 py-3 border-t border-gray-200 space-y-2">
          <div className="flex items-center gap-2">
            <div className="relative">
              <input
                type="color"
                value={newColor}
                onChange={(e) => setNewColor(e.target.value)}
                className="w-5 h-5 rounded border-0 p-0 cursor-pointer shrink-0"
              />
            </div>
            <input
              type="text"
              value={newName}
              onChange={(e) => { setNewName(e.target.value); setNameError('') }}
              placeholder="Название новой папки"
              className="flex-1 px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:border-primary focus:ring-1 focus:ring-primary outline-none"
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            />
            <button
              onClick={handleCreate}
              disabled={!newName.trim()}
              className="shrink-0 px-3 py-1.5 text-sm font-medium rounded-lg bg-primary text-white hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Создать
            </button>
          </div>
          {nameError && <p className="text-xs text-red-500">{nameError}</p>}
          <div className="flex items-center gap-1.5">
            {PRESET_COLORS.map((color) => (
              <button
                key={color}
                onClick={() => setNewColor(color)}
                className={`w-5 h-5 rounded-full border-2 transition-colors ${newColor === color ? 'border-gray-400 scale-110' : 'border-transparent'}`}
                style={{ backgroundColor: color }}
              />
            ))}
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor="folder-manage-type" className="text-xs font-medium text-gray-500 shrink-0">Сфера</label>
            <select
              id="folder-manage-type"
              value={newType}
              onChange={e => { setNewType(e.target.value as ContactSphere); setNewParent(null) }}
              className="flex-1 px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:border-primary focus:ring-1 focus:ring-primary outline-none"
            >
              <option value="personal">{CONTACT_SPHERE_META.personal.label}</option>
              <option value="work">{CONTACT_SPHERE_META.work.label}</option>
              <option value="channels">{CONTACT_SPHERE_META.channels.label}</option>
            </select>
          </div>
          {parentCandidates.length > 0 && (
            <div className="flex items-center gap-2">
              <label htmlFor="folder-manage-parent" className="text-xs font-medium text-gray-500 shrink-0">Внутри</label>
              <select
                id="folder-manage-parent"
                value={newParent === null ? '' : String(newParent)}
                onChange={e => setNewParent(e.target.value === '' ? null : Number(e.target.value))}
                className="flex-1 px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:border-primary focus:ring-1 focus:ring-primary outline-none"
              >
                <option value="">Без родительской папки</option>
                {parentCandidates.map(f => (
                  <option key={f.id} value={f.id}>{f.name}</option>
                ))}
              </select>
            </div>
          )}
        </div>
        </>
        )}
      </div>

      {editingFolder && (
        <FolderEditModal folder={editingFolder} onClose={() => setEditingFolder(null)} />
      )}

      {pendingDelete && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center px-4">
          <div className="absolute inset-0 bg-black/40" role="button" tabIndex={0} onClick={() => setPendingDelete(null)} onKeyDown={(e) => e.key === 'Enter' && setPendingDelete(null)} />
          <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-sm p-5">
            <h3 className="text-base font-semibold text-gray-900">Удалить папку?</h3>
            <p className="mt-2 text-sm text-gray-600">
              Папка «{pendingDelete.name}» будет удалена. Контакты из неё не удалятся, но потеряют привязку к папке.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setPendingDelete(null)}
                className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50"
              >
                Отмена
              </button>
              <button
                onClick={confirmDelete}
                className="px-3 py-1.5 text-sm rounded-lg bg-red-600 text-white hover:bg-red-700"
              >
                Да, удалить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
