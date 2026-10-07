import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { useNotesQuery, useCreateNoteMutation, useDeleteNoteMutation } from '../../hooks/queries'

export default function NoteList({
  contactId,
}: {
  contactId: number
}) {
  const [content, setContent] = useState('')
  const [isAdding, setIsAdding] = useState(false)

  const { data: notes = [] } = useNotesQuery(contactId)
  const createNote = useCreateNoteMutation()
  const deleteNote = useDeleteNoteMutation()

  const handleAdd = async () => {
    if (!content.trim()) return
    createNote.mutate({ contactId, data: { content: content.trim() } })
    setContent('')
    setIsAdding(false)
  }

  const handleDelete = (id: number) => {
    deleteNote.mutate({ contactId, noteId: id })
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">Заметки</span>
        <button
          onClick={() => setIsAdding(!isAdding)}
          className="p-0.5 text-gray-400 hover:text-blue-600 rounded"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {isAdding && (
        <div className="space-y-1">
          <textarea
            value={content}
            onChange={e => setContent(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && e.ctrlKey) handleAdd() }}
            placeholder="Текст заметки... (Ctrl+Enter — сохранить)"
            rows={2}
            className="w-full px-2 py-1 text-xs border rounded resize-none"
          />
          <div className="flex justify-end gap-1">
            <button onClick={() => setIsAdding(false)} className="px-2 py-0.5 text-xs border rounded">Отмена</button>
            <button onClick={handleAdd} className="px-2 py-0.5 text-xs text-white bg-blue-600 rounded">Добавить</button>
          </div>
        </div>
      )}

      <div className="space-y-2 max-h-40 overflow-y-auto">
        {notes.length === 0 && !isAdding && (
          <p className="text-xs text-gray-400 text-center py-2">Нет заметок</p>
        )}
        {notes.map(note => (
          <div key={note.id} className="group border border-gray-100 rounded p-2">
            <div className="flex items-start justify-between">
              <p className="text-xs text-gray-700 whitespace-pre-wrap flex-1">{note.content}</p>
              <button
                onClick={() => handleDelete(note.id)}
                className="p-0.5 text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              {note.created_at ? new Date(note.created_at).toLocaleString() : ''}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
