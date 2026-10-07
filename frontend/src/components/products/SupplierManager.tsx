import { useEffect, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import Modal from '../common/Modal'
import Button from '../common/Button'
import ContactCombobox from '../contacts/ContactCombobox'
import type { Contact } from '../../types/contact'
import type { Supplier } from '../../types/supplier'

interface SupplierManagerProps {
  open: boolean
  onClose: () => void
  suppliers: Supplier[]
  contacts: Contact[]
  onCreate: (data: { contact_id: number; company_name?: string }) => Promise<unknown>
  onDelete: (id: number) => Promise<unknown>
}

function SupplierManager({ open, onClose, suppliers, contacts, onCreate, onDelete }: SupplierManagerProps) {
  const [contactId, setContactId] = useState<number | null>(null)
  const [companyName, setCompanyName] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setContactId(null)
    setCompanyName('')
    setError(null)
  }, [open])

  const usedContactIds = suppliers.map((s) => s.contact_id)

  const handleAdd = async () => {
    if (!contactId) {
      setError('Выберите контакт')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await onCreate({ contact_id: contactId, company_name: companyName.trim() || undefined })
      setContactId(null)
      setCompanyName('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось добавить поставщика')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Поставщики" maxWidth="max-w-2xl">
      <div className="p-5 space-y-4">
        <div>
          <label htmlFor="supplier-contact" className="block text-sm font-medium text-gray-700 mb-1">Контакт</label>
          <ContactCombobox
            id="supplier-contact"
            contacts={contacts}
            value={contactId}
            onChange={setContactId}
            excludeIds={usedContactIds}
            placeholder="Поиск контакта для поставщика..."
          />
        </div>
        <div>
          <label htmlFor="supplier-company" className="block text-sm font-medium text-gray-700 mb-1">Название компании</label>
          <input
            id="supplier-company"
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            placeholder="ООО Ромашка"
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex justify-end">
          <Button onClick={handleAdd} disabled={saving}>
            <Plus className="w-4 h-4 mr-1" />
            {saving ? 'Добавление…' : 'Добавить поставщика'}
          </Button>
        </div>

        <div className="border-t border-gray-100 pt-3">
          {suppliers.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-4">Поставщиков пока нет</p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {suppliers.map((s) => (
                <li key={s.id} className="flex items-center justify-between py-2">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">
                      {s.contact_name || `Поставщик #${s.id}`}
                    </p>
                    {s.company_name && (
                      <p className="text-xs text-gray-400 truncate">{s.company_name}</p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      if (window.confirm('Удалить поставщика?')) onDelete(s.id)
                    }}
                    className="shrink-0 text-gray-400 hover:text-red-500 transition-colors"
                    title="Удалить"
                    aria-label={`Удалить поставщика ${s.contact_name ?? s.id}`}
                  >
                    <Trash2 size={16} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </Modal>
  )
}

export default SupplierManager
