import { useState, useEffect, memo, useCallback, useMemo } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { Dialog } from '@headlessui/react'
import { CheckSquare, Square, ArrowUpDown } from 'lucide-react'
import Card from '../components/common/Card'
import BulkActionBar from '../components/contacts/BulkActionBar'
import ContactDetailPanel from '../components/contacts/ContactDetailPanel'
import ContactForm from '../components/contacts/ContactForm'
import ContactQuickActions from '../components/contacts/ContactQuickActions'
import MergeDialog from '../components/contacts/MergeDialog'
import FolderSidebar, { type ContactFilter } from '../components/contacts/FolderSidebar'
import DuplicatePanel from '../components/contacts/DuplicatePanel'
import BulkEditDialog from '../components/contacts/BulkEditDialog'
import ImportDialog from '../components/contacts/ImportDialog'
import { contactApi } from '../api/client'
import { useContactsQuery, useContactQuery, useCreateContactMutation, useUpdateContactMutation, useDeleteContactMutation } from '../hooks/queries'
import type { ContactFormData } from '../schemas'
import { toNullableString } from '../components/contacts/ContactForm'
import type { Contact, ContactSortBy, ContactSubsection } from '../types/contact'
import { contactSphereMeta } from '../types/contactType'
import { getChannelIcon } from '../utils/channelIcons'

const PAGE_SIZE = 20

type SubsectionTab = 'all' | ContactSubsection

const subsectionTabs: { key: SubsectionTab; label: string }[] = [
  { key: 'all', label: 'Все' },
  { key: 'new', label: 'Новые' },
]

const channelOptions: { key: string; label: string }[] = [
  { key: '', label: 'Все каналы' },
  { key: 'telegram', label: 'Telegram' },
  { key: 'email', label: 'Email' },
  { key: 'vk', label: 'VK' },
]

const sortOptions: { key: ContactSortBy; label: string }[] = [
  { key: 'name', label: 'По имени' },
  { key: 'created_at', label: 'По дате создания' },
  { key: 'message_count', label: 'По сообщениям' },
  { key: 'last_activity', label: 'По последнему сообщению' },
  { key: 'first_message', label: 'По первому сообщению' },
  { key: 'has_tasks', label: 'По задачам' },
]

const ContactRow = memo(function ContactRow({
  contact,
  isSelected,
  isActive,
  onSelect,
  onToggle,
  onDragStart,
}: {
  contact: Contact
  isSelected: boolean
  isActive: boolean
  onSelect: (contact: Contact) => void
  onToggle: (id: number) => void
  onDragStart: (e: React.DragEvent, contact: Contact) => void
}) {
  const channelBadges = contact.channel_types || []
  const sphereMeta = contactSphereMeta(contact.life_sphere)
  const hasSphere = !!contact.life_sphere

  return (
    <div
      className={`flex items-center gap-3 p-4 hover:bg-gray-50 ${isActive ? 'bg-blue-50' : ''}`}
      draggable
      onDragStart={(e) => onDragStart(e, contact)}
    >
      <button onClick={e => { e.stopPropagation(); onToggle(contact.id) }} className="text-gray-400 hover:text-gray-600 shrink-0">
        {isSelected ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
      </button>
      <div
        className="flex-1 min-w-0 cursor-pointer"
        role="button"
        tabIndex={0}
        onClick={() => onSelect(contact)}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') onSelect(contact) }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex -space-x-1">
              {channelBadges.map(ch => {
                const Icon = getChannelIcon(ch)
                return (
                  <span key={ch} className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-gray-100" title={ch}>
                    <Icon className="w-3 h-3 text-gray-500" />
                  </span>
                )
              })}
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="font-medium text-gray-900 truncate">{contact.name || contact.telegram_username?.replace(/^@/, '') || `#${contact.id}`}</p>
                {hasSphere && (
                  <span className={`shrink-0 text-xs px-1.5 py-0.5 rounded-full ${sphereMeta.bg} ${sphereMeta.color}`}>
                    {sphereMeta.label}
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-500 truncate">
                {contact.phone && `${contact.phone} `}
                {contact.email && `· ${contact.email}`}
                {contact.telegram_username && `· @${contact.telegram_username.replace(/^@/, '')}`}
              </p>
            </div>
          </div>
          <div className="flex gap-2 text-xs text-gray-400 shrink-0">
            <span>{contact.message_count} сообщ.</span>
            <span>{contact.task_count} задач</span>
          </div>
        </div>
      </div>
      <ContactQuickActions contact={contact} />
    </div>
  )
})

function Contacts() {
  const [searchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')
  const [subsection, setSubsection] = useState<SubsectionTab>('all')
  const [channel, setChannel] = useState('')
  const [filter, setFilter] = useState<ContactFilter>({ kind: 'all' })
  const [sortBy, setSortBy] = useState<ContactSortBy>('name')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
  const [page, setPage] = useState(0)
  const [selectedContactId, setSelectedContactId] = useState<number | null>(null)
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [isMergeOpen, setIsMergeOpen] = useState(false)
  const [isBulkEditOpen, setIsBulkEditOpen] = useState(false)
  const [isImportOpen, setIsImportOpen] = useState(false)
  const [editContact, setEditContact] = useState<Contact | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [accumulatedContacts, setAccumulatedContacts] = useState<Contact[]>([])
  const [hasMore, setHasMore] = useState(true)

  const queryParams = {
    search: searchQuery || undefined,
    channel: channel || undefined,
    subsection: subsection !== 'all' ? subsection : undefined,
    life_sphere: filter.kind === 'sphere' ? filter.sphere : undefined,
    folder_id: filter.kind === 'folder' ? filter.folderId : undefined,
    is_favorite: filter.kind === 'favorites' ? true : undefined,
    unclassified: filter.kind === 'other' ? true : undefined,
    sort_by: sortBy,
    sort_order: sortOrder,
    skip: page * PAGE_SIZE,
    limit: PAGE_SIZE,
  }

  const { data, isLoading } = useContactsQuery(queryParams)

  const { data: selectedContact } = useContactQuery(selectedContactId ?? undefined)

  const createContact = useCreateContactMutation()
  const updateContact = useUpdateContactMutation()
  const deleteContact = useDeleteContactMutation()

  useEffect(() => {
    const cidParam = searchParams.get('contact_id')
    if (cidParam) {
      const cid = parseInt(cidParam, 10)
      if (!isNaN(cid)) setSelectedContactId(cid)
    }
  }, [searchParams])

  useEffect(() => {
    if (data !== undefined) {
      setAccumulatedContacts(prev => page === 0 ? data : [...prev, ...data])
      setHasMore(data.length === PAGE_SIZE)
    }
  }, [data, page])

  const resetFilters = useCallback(() => {
    setPage(0)
    setAccumulatedContacts([])
  }, [])

  const handleSearch = useCallback((val: string) => {
    setSearchQuery(val)
    setPage(0)
    setAccumulatedContacts([])
  }, [])

  const handleSubsectionChange = useCallback((sub: SubsectionTab) => {
    setSubsection(sub)
    setPage(0)
    setAccumulatedContacts([])
  }, [])

  const handleChannelChange = useCallback((ch: string) => {
    setChannel(ch)
    setPage(0)
    setAccumulatedContacts([])
  }, [])

  const handleSelectFilter = useCallback((next: ContactFilter) => {
    setFilter(next)
    setPage(0)
    setAccumulatedContacts([])
  }, [])

  const visibleContacts = useMemo(() => {
    return accumulatedContacts
  }, [accumulatedContacts])

  const handleSortChange = useCallback((sort: ContactSortBy) => {
    if (sort === sortBy) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(sort)
      setSortOrder(sort === 'name' ? 'asc' : 'desc')
    }
    setPage(0)
    setAccumulatedContacts([])
  }, [sortBy])

  const handleDropContact = useCallback(async (contactId: number, folderId: number | null) => {
    await updateContact.mutateAsync({
      id: contactId,
      data: { folder_id: folderId },
    })
  }, [updateContact])

  const handleDragStart = useCallback((e: React.DragEvent, contact: Contact) => {
    e.dataTransfer.setData('text/plain', String(contact.id))
    e.dataTransfer.effectAllowed = 'move'
  }, [])

  const handleCreate = async (formData: ContactFormData) => {
    await createContact.mutateAsync({
      name: toNullableString(formData.name),
      phone: toNullableString(formData.phone),
      email: toNullableString(formData.email),
      telegram_username: toNullableString(formData.telegram_username),
      notes: toNullableString(formData.notes),
      is_known: true,
      is_favorite: formData.is_favorite ?? undefined,
      life_sphere: toNullableString(formData.life_sphere) as Contact['life_sphere'],
      birthday: toNullableString(formData.birthday),
      folder_ids: formData.folder_ids,
    })
    resetFilters()
    setIsFormOpen(false)
  }

  const handleUpdate = async (id: number, formData: ContactFormData) => {
    await updateContact.mutateAsync({
      id,
      data: {
        name: toNullableString(formData.name),
        phone: toNullableString(formData.phone),
        email: toNullableString(formData.email),
        telegram_username: toNullableString(formData.telegram_username),
        notes: toNullableString(formData.notes),
        is_known: true,
        is_favorite: formData.is_favorite ?? undefined,
        life_sphere: toNullableString(formData.life_sphere) as Contact['life_sphere'],
        birthday: toNullableString(formData.birthday),
        folder_ids: formData.folder_ids,
      },
    })
    setEditContact(null)
    setIsFormOpen(false)
  }

  const handleMergeFromForm = async (targetId: number) => {
    if (!editContact) return
    if (!confirm('Объединить контакты? Это действие нельзя отменить.')) return
    try {
      await contactApi.merge(editContact.id, targetId)
      queryClient.invalidateQueries({ queryKey: ['contacts'] })
      setEditContact(null)
      setIsFormOpen(false)
      setSelectedContactId(targetId)
    } catch (e) {
      console.error('Merge failed', e)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Переместить контакт в архив?')) return
    await deleteContact.mutateAsync(id)
    if (selectedContactId === id) setSelectedContactId(null)
  }

  const handleMerge = async (targetId: number) => {
    if (!selectedContact) return
    if (!confirm('Объединить контакты? Это действие нельзя отменить.')) return
    try {
      await contactApi.merge(selectedContact.id, targetId)
      queryClient.invalidateQueries({ queryKey: ['contacts'] })
      setIsMergeOpen(false)
      setSelectedContactId(targetId)
    } catch (e) {
      console.error('Merge failed', e)
    }
  }

  const handleBulkMerge = async (primaryId: number, secondaryIds: number[]) => {
    if (secondaryIds.length === 0) return
    await contactApi.bulkMerge(primaryId, secondaryIds)
    queryClient.invalidateQueries({ queryKey: ['contacts'] })
    setAccumulatedContacts([])
    setPage(0)
  }

  const toggleSelect = useCallback((id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const toggleSelectAll = () => {
    if (selectedIds.size === visibleContacts.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(visibleContacts.map(c => c.id)))
    }
  }

  const handleBulkMergeAction = async () => {
    const ids = Array.from(selectedIds)
    if (ids.length < 2) return
    const primaryId = ids[0]
    const secondaryIds = ids.slice(1)
    if (!confirm(`Объединить ${secondaryIds.length} контактов с основным?`)) return
    try {
      await contactApi.bulkMerge(primaryId, secondaryIds)
      setSelectedIds(new Set())
      queryClient.invalidateQueries({ queryKey: ['contacts'] })
      setAccumulatedContacts([])
      setPage(0)
    } catch (e) {
      console.error('Bulk merge failed', e)
    }
  }

  const handleBulkDelete = async () => {
    const ids = Array.from(selectedIds)
    if (!ids.length) return
    if (!confirm(`Переместить ${ids.length} контактов в архив?`)) return
    try {
      await contactApi.bulkDelete(ids)
      setSelectedIds(new Set())
      queryClient.invalidateQueries({ queryKey: ['contacts'] })
      setAccumulatedContacts([])
      setPage(0)
    } catch (e) {
      console.error('Bulk delete failed', e)
    }
  }

  return (
    <div className="flex gap-6 h-[calc(100vh-4rem)] overflow-hidden">
      <div className="flex flex-col gap-3 shrink-0 overflow-y-auto max-h-full">
        <FolderSidebar
          selected={filter}
          onSelect={handleSelectFilter}
          onDropContact={handleDropContact}
        />
        <DuplicatePanel onMerge={handleBulkMerge} />
      </div>

      <div className="flex-1 flex flex-col min-w-0 min-h-0">
        <div className="sticky top-0 z-10 bg-white/95 backdrop-blur-sm border-b border-gray-200 pb-4 space-y-3">
          <div className="flex items-center justify-between pt-1">
            <h2 className="text-2xl font-semibold text-gray-900">Контакты</h2>
            <div className="flex gap-2">
              {selectedContact && (
                <button
                  onClick={() => setIsMergeOpen(true)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Объединить
                </button>
              )}
              <button
                onClick={() => setIsImportOpen(true)}
                className="px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Импорт / Экспорт
              </button>
              <button
                onClick={() => { setEditContact(null); setIsFormOpen(true) }}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
              >
                + Создать
              </button>
            </div>
          </div>

          <BulkActionBar
            selectedCount={selectedIds.size}
            onMerge={handleBulkMergeAction}
            onDelete={handleBulkDelete}
            onEdit={() => setIsBulkEditOpen(true)}
            onClear={() => setSelectedIds(new Set())}
          />

          <div className="flex gap-2">
            {subsectionTabs.map(tab => (
              <button
                key={tab.key}
                onClick={() => handleSubsectionChange(tab.key)}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                  subsection === tab.key
                    ? 'bg-blue-100 text-blue-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Поиск по имени, телефону, email, тексту сообщений..."
              value={searchQuery}
              onChange={e => handleSearch(e.target.value)}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />

            <select
              value={channel}
              onChange={e => handleChannelChange(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
            >
              {channelOptions.map(opt => (
                <option key={opt.key} value={opt.key}>{opt.label}</option>
              ))}
            </select>

            <select
              value={sortBy}
              onChange={(e) => handleSortChange(e.target.value as ContactSortBy)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
            >
              {sortOptions.map(opt => (
                <option key={opt.key} value={opt.key}>{opt.label}</option>
              ))}
            </select>

            <button
              onClick={() => handleSortChange(sortBy)}
              className="flex items-center gap-1 px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 whitespace-nowrap"
              title={sortOrder === 'asc' ? 'По возрастанию' : 'По убыванию'}
              aria-label={sortOrder === 'asc' ? 'По возрастанию' : 'По убыванию'}
            >
              <ArrowUpDown className="w-4 h-4" />
              <span className="text-gray-400">{sortOrder === 'asc' ? '↑' : '↓'}</span>
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto pt-4">
          <Card>
            <div className="divide-y divide-gray-100">
              {visibleContacts.length > 0 && (
                <div className="px-4 py-2 flex items-center gap-3 border-b border-gray-200 bg-gray-50">
                  <button onClick={toggleSelectAll} className="text-gray-400 hover:text-gray-600">
                    {selectedIds.size === visibleContacts.length ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
                  </button>
                  <span className="text-xs text-gray-500">
                    {selectedIds.size > 0 ? `Выбрано ${selectedIds.size}` : 'Выбрать все'}
                  </span>
                </div>
              )}
              {visibleContacts.length === 0 && !isLoading && (
                <div className="p-8 text-center text-gray-400">
                  {searchQuery ? 'Ничего не найдено' : 'Нет контактов'}
                </div>
              )}
              {visibleContacts.map(c => (
                <ContactRow
                  key={c.id}
                  contact={c}
                  isSelected={selectedIds.has(c.id)}
                  isActive={selectedContactId === c.id}
                  onSelect={(contact) => setSelectedContactId(contact.id)}
                  onToggle={toggleSelect}
                  onDragStart={handleDragStart}
                />
              ))}
            </div>
            {hasMore && (
              <button
                onClick={() => setPage(p => p + 1)}
                className="w-full py-2 text-sm text-blue-600 hover:text-blue-800"
              >
                {isLoading ? 'Загрузка...' : 'Загрузить ещё'}
              </button>
            )}
          </Card>
        </div>
      </div>

      {selectedContact && (
        <ContactDetailPanel
          contact={selectedContact}
          onEdit={() => { setEditContact(selectedContact); setIsFormOpen(true) }}
          onDelete={() => handleDelete(selectedContact.id)}
        />
      )}

      <Dialog open={isFormOpen} onClose={() => setIsFormOpen(false)} className="relative z-50">
        <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="w-full max-w-md bg-white rounded-xl p-6 max-h-[90vh] overflow-y-auto">
            <Dialog.Title className="text-lg font-semibold mb-4">
              {editContact ? 'Редактировать контакт' : 'Создать контакт'}
            </Dialog.Title>
            <ContactForm
              initial={editContact}
              onSubmit={async (data) => {
                if (editContact) await handleUpdate(editContact.id, data)
                else await handleCreate(data)
              }}
              onCancel={() => setIsFormOpen(false)}
              onMerge={handleMergeFromForm}
            />
          </Dialog.Panel>
        </div>
      </Dialog>

      <MergeDialog
        open={isMergeOpen}
        onClose={() => setIsMergeOpen(false)}
        selectedContact={selectedContact ?? null}
        onMerge={handleMerge}
      />

      <BulkEditDialog
        open={isBulkEditOpen}
        onClose={() => setIsBulkEditOpen(false)}
        selectedIds={Array.from(selectedIds)}
      />

      <ImportDialog
        open={isImportOpen}
        onClose={() => setIsImportOpen(false)}
      />
    </div>
  )
}

export default Contacts
