import { useMemo, useState } from 'react'
import { Pencil, Trash2 } from 'lucide-react'
import { CONTACT_SPHERE_META } from '../../types/contactType'
import type { ContactFolder, ContactSphere } from '../../types/contact'

const FOLDER_DRAG_TYPE = 'application/x-bizibox-folder'
const SPHERE_GROUPS: ContactSphere[] = ['work', 'personal', 'channels']

export interface FolderTreeProps {
  folders: ContactFolder[]
  groupBySphere?: boolean
  selectedFolderId?: number | null
  onSelect?: (folderId: number) => void
  onEdit?: (folder: ContactFolder) => void
  onDelete?: (folder: ContactFolder) => void
  onDropContact?: (contactId: number, folderId: number) => void
  onReorder?: (orderedIds: number[]) => void
}

function buildTree(folders: ContactFolder[]): Map<number | 0, ContactFolder[]> {
  const map = new Map<number | 0, ContactFolder[]>()
  for (const folder of folders) {
    const key = folder.parent_id ?? 0
    const list = map.get(key)
    if (list) list.push(folder)
    else map.set(key, [folder])
  }
  for (const list of map.values()) {
    list.sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name))
  }
  return map
}

export default function FolderTree({
  folders,
  groupBySphere = false,
  selectedFolderId = null,
  onSelect,
  onEdit,
  onDelete,
  onDropContact,
  onReorder,
}: FolderTreeProps) {
  const [draggingId, setDraggingId] = useState<number | null>(null)
  const tree = useMemo(() => buildTree(folders), [folders])

  const flatOrder = useMemo(() => {
    const ids: number[] = []
    const walk = (parentId: number | 0) => {
      for (const folder of tree.get(parentId) ?? []) {
        ids.push(folder.id)
        walk(folder.id)
      }
    }
    walk(0)
    return ids
  }, [tree])

  const handleReorder = (draggedId: number, targetId: number, insertBefore: boolean) => {
    if (draggedId === targetId) return
    const dragged = folders.find(f => f.id === draggedId)
    const target = folders.find(f => f.id === targetId)
    if (!dragged || !target) return
    if ((dragged.parent_id ?? null) !== (target.parent_id ?? null)) return
    const order = [...flatOrder]
    const from = order.indexOf(draggedId)
    order.splice(from, 1)
    const to = order.indexOf(targetId)
    order.splice(insertBefore ? to : to + 1, 0, draggedId)
    onReorder?.(order)
  }

  const handleDrop = (e: React.DragEvent, folder: ContactFolder) => {
    const contactData = e.dataTransfer.getData('text/plain')
    if (contactData && /^\d+$/.test(contactData)) {
      if (!onDropContact) return
      e.preventDefault()
      onDropContact(Number(contactData), folder.id)
      return
    }
    const draggedRaw = e.dataTransfer.getData(FOLDER_DRAG_TYPE)
    if (draggedRaw && onReorder) {
      e.preventDefault()
      const rect = e.currentTarget.getBoundingClientRect()
      const insertBefore = e.clientY < rect.top + rect.height / 2
      handleReorder(Number(draggedRaw), folder.id, insertBefore)
    }
  }

  const renderRow = (folder: ContactFolder, depth: number) => {
    const children = tree.get(folder.id) ?? []
    const isSelected = selectedFolderId === folder.id
    return (
      <div key={folder.id}>
        <div
          draggable={!!onReorder}
          onDragStart={e => {
            e.dataTransfer.setData(FOLDER_DRAG_TYPE, String(folder.id))
            e.dataTransfer.effectAllowed = 'move'
            setDraggingId(folder.id)
          }}
          onDragEnd={() => setDraggingId(null)}
          onDragOver={e => {
            if (onDropContact || onReorder) {
              e.preventDefault()
              e.dataTransfer.dropEffect = 'move'
            }
          }}
          onDrop={e => handleDrop(e, folder)}
          onClick={() => onSelect?.(folder.id)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              onSelect?.(folder.id)
            }
          }}
          className={`group flex items-center gap-2 -mx-1 px-2 py-1.5 rounded-md cursor-pointer text-sm transition-colors ${
            isSelected
              ? 'bg-primary/10 text-primary font-medium'
              : 'text-gray-700 hover:bg-gray-100'
          } ${draggingId === folder.id ? 'opacity-40' : ''}`}
          style={{ paddingLeft: 8 + depth * 14 }}
        >
          <span
            className="w-2.5 h-2.5 rounded-full shrink-0"
            style={{ backgroundColor: folder.color || '#6b7280' }}
          />
          <span className="flex-1 truncate">{folder.name}</span>
          {onEdit && (
            <button
              onClick={e => { e.stopPropagation(); onEdit(folder) }}
              className="p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-200 opacity-0 group-hover:opacity-100 shrink-0"
              title="Переименовать"
            >
              <Pencil className="w-3.5 h-3.5" />
            </button>
          )}
          {onDelete && (
            <button
              onClick={e => { e.stopPropagation(); onDelete(folder) }}
              disabled={folder.is_default}
              className={`p-1 rounded shrink-0 opacity-0 group-hover:opacity-100 ${
                folder.is_default
                  ? 'text-gray-200 cursor-not-allowed'
                  : 'text-gray-400 hover:text-red-500 hover:bg-red-50'
              }`}
              title={folder.is_default ? 'Системные папки нельзя удалить' : 'Удалить'}
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
        {children.map(child => renderRow(child, depth + 1))}
      </div>
    )
  }

  const rootFolders = tree.get(0) ?? []

  if (!groupBySphere) {
    return <>{rootFolders.map(folder => renderRow(folder, 0))}</>
  }

  return (
    <>
      {SPHERE_GROUPS.map(sphere => {
        const roots = rootFolders.filter(f => (f.sphere || 'personal') === sphere)
        if (roots.length === 0) return null
        return (
          <div key={sphere} className="pt-1.5 first:pt-0">
            <div className="px-1 pb-1 text-[11px] font-semibold uppercase tracking-wide text-gray-400">
              {CONTACT_SPHERE_META[sphere].label}
            </div>
            {roots.map(folder => renderRow(folder, 0))}
          </div>
        )
      })}
    </>
  )
}
