import { useState } from 'react'
import { Dialog } from '@headlessui/react'
import { contactApi } from '../../api/client'
import ContactDetailPanel from './ContactDetailPanel'
import type { Contact } from '../../types/contact'

interface ContactNameLinkProps {
  contactId: number
  children: React.ReactNode
  className?: string
}

export default function ContactNameLink({ contactId, children, className }: ContactNameLinkProps) {
  const [open, setOpen] = useState(false)
  const [contact, setContact] = useState<Contact | null>(null)
  const [loading, setLoading] = useState(false)

  const handleClick = () => {
    let cancelled = false
    setLoading(true)
    setOpen(true)
    contactApi.getById(contactId).then(c => {
      if (!cancelled) { setContact(c); setLoading(false) }
    }).catch(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }

  return (
    <>
      <span
        className={`cursor-pointer hover:text-blue-600 transition-colors ${className || ''}`}
        onClick={(e) => { e.stopPropagation(); handleClick() }}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.stopPropagation(); handleClick() } }}
        role="button"
        tabIndex={0}
      >
        {children}
      </span>

      <Dialog open={open} onClose={() => setOpen(false)} className="relative z-[60]">
        <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="w-full max-w-md" onClick={e => e.stopPropagation()}>
            {loading ? (
              <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
                <p className="text-sm text-gray-400">Загрузка...</p>
              </div>
            ) : contact ? (
              <ContactDetailPanel
                contact={contact}
                onEdit={() => {}}
                onDelete={() => setOpen(false)}
              />
            ) : (
              <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
                <p className="text-sm text-gray-400">Контакт не найден</p>
              </div>
            )}
          </Dialog.Panel>
        </div>
      </Dialog>
    </>
  )
}
