import { useState } from 'react'
import { Dialog } from '@headlessui/react'
import { contactApi } from '../../api/client'
import type { Contact } from '../../types/contact'

export default function MergeDialog({
  open,
  onClose,
  selectedContact,
  onMerge,
}: {
  open: boolean
  onClose: () => void
  selectedContact: Contact | null
  onMerge: (targetId: number) => Promise<void>
}) {
  const [mergeTargetId, setMergeTargetId] = useState<number | null>(null)
  const [contactsList, setContactsList] = useState<Contact[]>([])

  return (
    <Dialog open={open} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="w-full max-w-md bg-white rounded-xl p-6">
          <Dialog.Title className="text-lg font-semibold mb-4">
            Объединить контакты
          </Dialog.Title>
          <p className="text-sm text-gray-600 mb-4">
            Выберите контакт для объединения с <strong>{selectedContact?.name}</strong>.
            Все данные будут перенесены на основной контакт.
          </p>
          <input
            type="text"
            placeholder="Поиск контакта для объединения..."
            onChange={async (e) => {
              if (e.target.value.length < 2) return
              const results = await contactApi.search(e.target.value)
              setContactsList(results.filter(c => c.id !== selectedContact?.id))
            }}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg mb-4"
          />
          <div className="max-h-40 overflow-y-auto space-y-2 mb-4">
            {contactsList.map(c => (
              <button
                key={c.id}
                onClick={() => setMergeTargetId(c.id)}
                className={`w-full text-left p-2 rounded ${mergeTargetId === c.id ? 'bg-blue-100' : 'hover:bg-gray-100'}`}
              >
                {c.name || 'Без имени'} {c.phone && `· ${c.phone}`}
              </button>
            ))}
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={onClose} className="px-4 py-2 text-sm border rounded-lg">Отмена</button>
            <button onClick={() => mergeTargetId && onMerge(mergeTargetId)} disabled={!mergeTargetId} className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg disabled:opacity-50">
              Объединить
            </button>
          </div>
        </Dialog.Panel>
      </div>
    </Dialog>
  )
}
