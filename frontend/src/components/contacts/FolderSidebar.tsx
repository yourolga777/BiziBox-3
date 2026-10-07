import { useState } from 'react'
import { Folder, Plus, Star, Tag, ChevronRight, CircleDashed } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import Card from '../common/Card'
import { contactApi } from '../../api/client'
import { useFoldersQuery, useCreateFolderMutation } from '../../hooks/queries'
import { useToast } from '../common/Toast'
import FolderTree from '../common/FolderTree'
import FolderEditModal from '../common/FolderEditModal'
import { CONTACT_SPHERE_META } from '../../types/contactType'
import type { ContactFolder, ContactSphere } from '../../types/contact'

export type ContactFilter =
  | { kind: 'all' }
  | { kind: 'favorites' }
  | { kind: 'other' }
  | { kind: 'sphere'; sphere: ContactSphere }
  | { kind: 'folder'; folderId: number }

const SPHERE_ORDER: ContactSphere[] = ['work', 'personal', 'channels', 'spam']

export default function FolderSidebar({
  selected,
  onSelect,
  onDropContact,
}: {
  selected: ContactFilter
  onSelect: (filter: ContactFilter) => void
  onDropContact: (contactId: number, folderId: number | null) => void
}) {
  const { data: folders = [] } = useFoldersQuery()
  const createFolder = useCreateFolderMutation()
  const queryClient = useQueryClient()
  const { showToast } = useToast()
  const [isAdding, setIsAdding] = useState(false)
  const [newName, setNewName] = useState('')
  const [newSphere, setNewSphere] = useState<ContactSphere>('personal')
  const [newParent, setNewParent] = useState<number | null>(null)
  const [editingFolder, setEditingFolder] = useState<ContactFolder | null>(null)

  const foldersOfSphere = (sphere: ContactSphere) =>
    folders.filter(f => (f.sphere || 'personal') === sphere)

  const parentCandidates = folders.filter(
    f => (f.sphere || 'personal') === newSphere,
  )

  const handleCreate = async () => {
    if (!newName.trim()) return
    await createFolder.mutateAsync({
      name: newName.trim(),
      sphere: newSphere,
      parent_id: newParent,
    })
    setNewName('')
    setNewParent(null)
    setIsAdding(false)
  }

  const handleDropContact = (draggedContactId: number, folderId: number) => {
    onDropContact(draggedContactId, folderId)
  }

  const handleReorder = async (ids: number[]) => {
    try {
      await contactApi.reorderFolders(ids)
      queryClient.invalidateQueries({ queryKey: ['folders'] })
    } catch {
      showToast('Не удалось изменить порядок', 'error')
    }
  }

  const handleDeleteFolder = async (folder: { id: number; name: string }) => {
    if (!window.confirm(`Удалить папку «${folder.name}»? Контакты из неё не удалятся.`)) return
    try {
      await contactApi.deleteFolder(folder.id)
      queryClient.invalidateQueries({ queryKey: ['folders'] })
      queryClient.invalidateQueries({ queryKey: ['contacts'] })
      showToast('Папка удалена', 'success')
    } catch {
      showToast('Не удалось удалить папку', 'error')
    }
  }

  const isSphereSelected = (s: ContactSphere) =>
    selected.kind === 'sphere' && selected.sphere === s

  const folderIsInSphere = (s: ContactSphere) =>
    selected.kind === 'folder' && folders.some(f => (f.sphere || 'personal') === s && f.id === selected.folderId)

  const isSphereActive = (s: ContactSphere) => isSphereSelected(s) || folderIsInSphere(s)

  return (
    <div className="w-60 shrink-0">
      <Card>
        <div className="space-y-0.5">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-700">Контакты</h3>
            <button
              onClick={() => setIsAdding(true)}
              className="flex items-center gap-1 px-2 py-1 text-xs text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded"
            >
              <Plus className="w-3.5 h-3.5" />
              Создать папку
            </button>
          </div>

          <button
            onClick={() => onSelect({ kind: 'all' })}
            className={`w-full flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors ${
              selected.kind === 'all' ? 'bg-blue-100 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <Folder className="w-4 h-4" />
            Все контакты
          </button>

          <button
            onClick={() => onSelect({ kind: 'favorites' })}
            className={`w-full flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors ${
              selected.kind === 'favorites' ? 'bg-blue-100 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <Star className="w-4 h-4" />
            Избранное
          </button>

          <button
            onClick={() => onSelect({ kind: 'other' })}
            className={`w-full flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors ${
              selected.kind === 'other' ? 'bg-blue-100 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <CircleDashed className="w-4 h-4" />
            Другое
          </button>

          <div className="pt-1 mt-1 border-t border-gray-100">
            {SPHERE_ORDER.map(s => {
              const sphereFolders = foldersOfSphere(s)
              const showFolders = s === 'personal' || s === 'work' || s === 'channels'
              return (
                <div key={s}>
                  <button
                    onClick={() => onSelect({ kind: 'sphere', sphere: s })}
                    className={`w-full flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors ${
                      isSphereSelected(s) ? 'bg-blue-100 text-blue-700 font-medium' : 'text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    <Tag className="w-4 h-4" />
                    <span className="flex-1 text-left">{CONTACT_SPHERE_META[s].label}</span>
                    {showFolders && (
                      <ChevronRight className={`w-3.5 h-3.5 transition-transform ${isSphereActive(s) ? 'rotate-90' : ''}`} />
                    )}
                  </button>
                  {showFolders && isSphereActive(s) && (
                    <div className="ml-4 pl-2 border-l border-gray-200">
                      <FolderTree
                        folders={sphereFolders}
                        selectedFolderId={selected.kind === 'folder' ? selected.folderId : null}
                        onSelect={folderId => onSelect({ kind: 'folder', folderId })}
                        onEdit={setEditingFolder}
                        onDelete={handleDeleteFolder}
                        onDropContact={handleDropContact}
                        onReorder={handleReorder}
                      />
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {isAdding && (
            <div className="pt-2 mt-1 border-t border-gray-100 space-y-2">
              <input
                value={newName}
                onChange={e => setNewName(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleCreate(); if (e.key === 'Escape') { setIsAdding(false); setNewName('') } }}
                placeholder="Название папки"
                className="w-full px-2 py-1 text-sm border rounded"
              />
              <select
                value={newSphere}
                onChange={e => { setNewSphere(e.target.value as ContactSphere); setNewParent(null) }}
                className="w-full px-2 py-1 text-sm border rounded"
              >
                {(['personal', 'work', 'channels'] as ContactSphere[]).map(s => (
                  <option key={s} value={s}>{CONTACT_SPHERE_META[s].label}</option>
                ))}
              </select>
              {parentCandidates.length > 0 && (
                <select
                  value={newParent === null ? '' : String(newParent)}
                  onChange={e => setNewParent(e.target.value === '' ? null : Number(e.target.value))}
                  className="w-full px-2 py-1 text-sm border rounded"
                >
                  <option value="">Без родительской папки</option>
                  {parentCandidates.map(f => (
                    <option key={f.id} value={f.id}>Внутри «{f.name}»</option>
                  ))}
                </select>
              )}
              <div className="flex gap-2">
                <button
                  onClick={handleCreate}
                  disabled={!newName.trim()}
                  className="flex-1 px-2 py-1 text-xs font-medium text-white bg-blue-600 rounded disabled:opacity-50"
                >
                  Создать
                </button>
                <button
                  onClick={() => { setIsAdding(false); setNewName('') }}
                  className="px-2 py-1 text-xs border rounded text-gray-600"
                >
                  Отмена
                </button>
              </div>
            </div>
          )}
        </div>
      </Card>
      {editingFolder && (
        <FolderEditModal folder={editingFolder} onClose={() => setEditingFolder(null)} />
      )}
    </div>
  )
}
