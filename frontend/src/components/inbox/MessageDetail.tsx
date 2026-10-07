import { useEffect, useState, useRef, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Dialog } from '@headlessui/react'
import { messageApi, contactApi, sendReply as sendReplyApi } from '../../api/client'
import { sendFileReply, sendFileMessage, sendMessage } from '../../api/messages'
import ContactInfo from './ContactInfo'
import NewContactBanner from './NewContactBanner'
import ContactSearchPopup from './ContactSearchPopup'
import { ThreadList } from './ThreadList'
import ReplyBar, { type RecipientOption } from './ReplyBar'
import MessageActions from './MessageActions'
import ContactDetailPanel from '../contacts/ContactDetailPanel'
import ContactForm, { toNullableString } from '../contacts/ContactForm'
import TaskCreateModal from '../tasks/TaskCreateModal'
import { CalendarModal } from '../calendar/CalendarModal'
import ForwardModal from './ForwardModal'
import QuickOrderModal from './QuickOrderModal'
import { useContactsQuery } from '../../hooks/queries'
import { useCreateOrderMutation } from '../../hooks/orders'
import { getMessagesFromCache, saveMessages, getDraft, saveDraft, clearDraft, type DraftAttachment } from '../../offline/db'
import { SYNC_COMPLETE } from '../../offline/sync'
import type { ContactFormData } from '../../schemas'
import type { Message } from '../../types/message'
import type { Contact } from '../../types/contact'
interface MessageDetailProps {
  message: Message
  contactName: string | null
  onClose: () => void
  onReplied: () => void
  onMessageUpdate?: (msg: Message) => void
}
function MessageDetail({ message, contactName, onClose, onReplied, onMessageUpdate }: MessageDetailProps) {
  const queryClient = useQueryClient()
  const [thread, setThread] = useState<Message[]>([])
  const [replyText, setReplyText] = useState('')
  const [replyTarget, setReplyTarget] = useState<Message | null>(null)
  const [attachments, setAttachments] = useState<File[]>([])
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState<string | null>(null)
  const [contact, setContact] = useState<Contact | null>(null)
  const [recipientOverride, setRecipientOverride] = useState('')
  const displayName = contact?.name || message.contact_name || contactName || 'Неизвестный'
  const [localStatus, setLocalStatus] = useState<'read' | 'unread'>(message.status === 'unread' ? 'unread' : 'read')
  const [localFlag, setLocalFlag] = useState<boolean>(message.is_flagged ?? false)
  const [contactLoading, setContactLoading] = useState(false)
  const [showContactSearch, setShowContactSearch] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Contact[]>([])
  const [initialContacts, setInitialContacts] = useState<Contact[]>([])
  const [linking, setLinking] = useState(false)
  const [showEditForm, setShowEditForm] = useState(false)
  const [isCreatingContact, setIsCreatingContact] = useState(false)
  const [showContactCard, setShowContactCard] = useState(false)
  const [taskModalOpen, setTaskModalOpen] = useState(false)
  const [eventModalOpen, setEventModalOpen] = useState(false)
  const [orderModalOpen, setOrderModalOpen] = useState(false)
  const [orderMessage, setOrderMessage] = useState<Message | null>(null)
  const [forwardTarget, setForwardTarget] = useState<Message | null>(null)
  const [taskMessage, setTaskMessage] = useState<Message | null>(null)
  const contactsQuery = useContactsQuery()
  const createOrder = useCreateOrderMutation()
  const [hasMore, setHasMore] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const threadEndRef = useRef<HTMLDivElement>(null)
  const threadRef = useRef<Message[]>([])
  const replyInputRef = useRef<HTMLInputElement>(null)
  const AUTO_READ_DELAY_MS = 800
  const PAGE_SIZE = 20

  useEffect(() => {
    threadRef.current = thread
  }, [thread])

  const attachmentsToDraft = useCallback((files: File[]): DraftAttachment[] =>
    files.map((f) => ({ name: f.name, type: f.type, size: f.size, data: f })), [])

  const draftToFiles = useCallback((draft: DraftAttachment[]): File[] =>
    draft
      .map((a) => {
        try {
          return new File([a.data], a.name, { type: a.type })
        } catch {
          return null
        }
      })
      .filter((f): f is File => f !== null), [])

  useEffect(() => {
    let cancelled = false
    getDraft(message.contact_id)
      .then((draft) => {
        if (cancelled || !draft) return
        if (draft.text) setReplyText(draft.text)
        const files = draftToFiles(draft.attachments)
        if (files.length > 0) setAttachments(files)
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [message.contact_id])

  const persistDraft = useCallback(() => {
    saveDraft({
      contactId: message.contact_id,
      text: replyText,
      attachments: attachmentsToDraft(attachments),
    }).catch(() => {})
  }, [message.contact_id, replyText, attachments])

  useEffect(() => {
    const timer = setTimeout(persistDraft, 400)
    return () => clearTimeout(timer)
  }, [persistDraft])

  useEffect(() => {
    const handleBeforeUnload = () => {
      saveDraft({
        contactId: message.contact_id,
        text: replyText,
        attachments: attachmentsToDraft(attachments),
      }).catch(() => {})
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
      handleBeforeUnload()
    }
  }, [message.contact_id, replyText, attachments, attachmentsToDraft])

  const loadThreadFromCacheOrServer = () => {
    messageApi.getDialog(message.contact_id, PAGE_SIZE)
      .then((data) => {
        const msgs = [...(data ?? [])].reverse()
        setThread(msgs)
        setHasMore(msgs.length >= PAGE_SIZE)
      })
      .catch(() => {
        getMessagesFromCache()
          .then((cached) => {
            const msgs = (cached as Message[]).filter((m) => m.contact_id === message.contact_id)
            setThread([...msgs].reverse())
            setHasMore(false)
          })
          .catch(() => {})
      })
  }

  const handleLoadMore = useCallback(async () => {
    if (loadingMore || !hasMore || thread.length === 0) return
    setLoadingMore(true)
    try {
      const older = await messageApi.loadPrevious(message.contact_id, PAGE_SIZE)
      const olderReversed = [...(older ?? [])].reverse()
      if (olderReversed.length === 0) {
        setHasMore(false)
      } else {
        loadingMoreAtStartRef.current = true
        setThread((prev) => [...olderReversed, ...prev])
        setHasMore(olderReversed.length >= PAGE_SIZE)
      }
    } catch {
      try {
        const oldest = thread[0]
        if (!oldest) {
          setHasMore(false)
          return
        }
        const older = await messageApi.getDialog(message.contact_id, PAGE_SIZE, {
          createdAt: oldest.created_at,
          id: oldest.id,
        })
        const olderReversed = [...(older ?? [])].reverse()
        if (olderReversed.length === 0) {
          setHasMore(false)
        } else {
          loadingMoreAtStartRef.current = true
          setThread((prev) => [...olderReversed, ...prev])
          setHasMore(olderReversed.length >= PAGE_SIZE)
        }
      } catch {
        // ignore
      }
    } finally {
      setLoadingMore(false)
    }
  }, [loadingMore, hasMore, thread, message.contact_id])

  useEffect(() => {
    messageApi.syncDialog(message.contact_id).catch(() => {}).finally(() => {
      loadThreadFromCacheOrServer()
    })
  }, [message.contact_id])

  useEffect(() => {
    const handleSyncComplete = () => {
      loadThreadFromCacheOrServer()
    }
    window.addEventListener(SYNC_COMPLETE, handleSyncComplete)
    return () => window.removeEventListener(SYNC_COMPLETE, handleSyncComplete)
  }, [message.contact_id])

  useEffect(() => {
    const timer = setTimeout(() => {
      messageApi.markContactRead(message.contact_id)
        .then(() => {
          setThread((prev) => prev.map((m) => (
            m.direction === 'incoming' && m.status === 'unread' ? { ...m, status: 'read' } : m
          )))
          setLocalStatus('read')
          if (onMessageUpdate) {
            onMessageUpdate({ ...message, status: 'read' })
          }
          // Оптимистичное обновление всех списков сообщений: инвалидация не помогает,
          // т.к. incrementalFetch запрашивает только id > maxId и не вернёт изменённые статусы.
          queryClient.setQueriesData<Message[]>({ queryKey: ['messages'] }, (old) =>
            old?.map((m) => (
              m.contact_id === message.contact_id && m.status === 'unread' ? { ...m, status: 'read' } : m
            )),
          )
          // Синхронизируем IndexedDB, чтобы оффлайн-кэш не отдавал устаревшие статусы.
          const incomingUnread = threadRef.current.filter(
            (m) => m.direction === 'incoming' && m.status === 'unread',
          )
          saveMessages(incomingUnread.map((m) => ({ ...m, status: 'read' }))).catch(() => {})
          queryClient.invalidateQueries({ queryKey: ['dashboard', 'metrics'] })
          queryClient.invalidateQueries({ queryKey: ['threads'] })
        })
        .catch(() => {})
    }, AUTO_READ_DELAY_MS)

    return () => clearTimeout(timer)
  }, [message.id, message.contact_id, thread])

  useEffect(() => {
    setLocalFlag(message.is_flagged ?? false)
  }, [message.id, message.is_flagged])

  const loadingMoreAtStartRef = useRef(false)
  const prevLastIdRef = useRef<number | null>(null)

  useEffect(() => {
    if (loadingMoreAtStartRef.current) {
      loadingMoreAtStartRef.current = false
      prevLastIdRef.current = thread.length ? thread[thread.length - 1].id : null
      return
    }
    const last = thread[thread.length - 1]
    if (last && last.id !== prevLastIdRef.current) {
      threadEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
    prevLastIdRef.current = last ? last.id : null
  }, [thread])

  useEffect(() => {
    setContactLoading(true)
    setRecipientOverride('')
    contactApi.getById(message.contact_id).then(setContact).catch(() => setContact(null))
      .finally(() => setContactLoading(false))
  }, [message.contact_id])

  useEffect(() => {
    if (showContactSearch) {
      contactApi.getAll({ limit: 20 }).then((data) => {
        setInitialContacts(Array.isArray(data) ? data.filter((c) => c.id !== message.contact_id) : [])
      }).catch(() => {})
    }
  }, [showContactSearch, message.contact_id])

  const recipientOptions: RecipientOption[] = (() => {
    if (!contact) return []
    const seen = new Set<string>()
    const options: RecipientOption[] = []
    const add = (value: string | null | undefined, label: string) => {
      const v = (value ?? '').trim()
      if (!v || seen.has(v)) return
      seen.add(v)
      options.push({ value: v, label: `${label}: ${v}` })
    }
    if (message.channel === 'telegram') {
      add(contact.telegram_id, 'TG ID')
      add(contact.telegram_username, 'TG @')
      for (const ident of contact.identifiers ?? []) {
        if (ident.channel === 'telegram_id') add(ident.value, 'TG ID')
        else if (ident.channel === 'telegram_username') add(ident.value, 'TG @')
      }
    } else if (message.channel === 'email') {
      add(contact.email, 'Email')
      for (const ident of contact.identifiers ?? []) {
        if (ident.channel === 'email') add(ident.value, 'Email')
      }
    }
    return options
  })()
  const activeRecipient = recipientOverride || undefined

  const handleSend = async () => {
    const content = replyText.trim()
    if (!content && attachments.length === 0) return
    setSending(true)
    setSendError(null)
    try {
      let sent: Message
      if (attachments.length > 0) {
        if (replyTarget) {
          sent = await sendFileReply(replyTarget.id, content, attachments, message.contact_id, activeRecipient)
        } else {
          sent = await sendFileMessage(message.contact_id, message.channel, content, attachments, activeRecipient)
        }
        setAttachments([])
      } else {
        if (replyTarget) {
          sent = await sendReplyApi(
            { message_id: replyTarget.id, content, ...(activeRecipient ? { recipient: activeRecipient } : {}) },
            message.contact_id,
          )
        } else {
          sent = await sendMessage(
            { contact_id: message.contact_id, channel: message.channel, content, ...(activeRecipient ? { recipient: activeRecipient } : {}) },
          )
        }
      }
      setReplyText('')
      setReplyTarget(null)
      setThread(prev => [...prev, sent])
      clearDraft(message.contact_id).catch(() => {})
      onReplied()
    } catch (err) {
      setSendError(err instanceof Error ? err.message : 'Ошибка отправки')
    } finally {
      setSending(false)
    }
  }

  const handleDeleteMessage = async (msg: Message) => {
    if (!confirm('Удалить сообщение?')) return
    try {
      await messageApi.delete(msg.id)
      setThread(prev => prev.filter(m => m.id !== msg.id))
      if (replyTarget?.id === msg.id) setReplyTarget(null)
      onReplied()
    } catch (err) {
      console.error('Delete message failed', err)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleToggleFlag = () => {
    const next = !localFlag
    setLocalFlag(next)
    messageApi.update(message.id, { is_flagged: next })
      .then((updated) => {
        if (updated && onMessageUpdate) onMessageUpdate(updated)
        queryClient.invalidateQueries({ queryKey: ['messages'] })
      })
      .catch(() => setLocalFlag(!next))
  }

  const handleToggleSpam = () => {
    const isSpam = contact?.life_sphere === 'spam'
    contactApi.setSpam(message.contact_id, !isSpam)
      .then(c => {
        setContact(c)
        queryClient.invalidateQueries({ queryKey: ['messages'] })
        queryClient.invalidateQueries({ queryKey: ['threads'] })
        queryClient.invalidateQueries({ queryKey: ['contacts'] })
        queryClient.invalidateQueries({ queryKey: ['contact', c.id] })
      })
      .catch(() => {})
  }

  const handleSearchContacts = async (q: string) => {
    setSearchQuery(q)
    if (!q.trim()) {
      setSearchResults([])
      return
    }
    try {
      const results = await contactApi.search(q)
      setSearchResults(Array.isArray(results) ? results.filter((c) => c.id !== message.contact_id) : [])
    } catch {
      setSearchResults([])
    }
  }

  const handleLinkContact = async (newContactId: number) => {
    setLinking(true)
    try {
      await messageApi.update(message.id, { contact_id: newContactId })
      const updatedContact = await contactApi.getById(newContactId)
      setContact(updatedContact)
      setShowContactSearch(false)
      onReplied()
    } catch {
      setShowContactSearch(false)
    } finally {
      setLinking(false)
    }
  }

  const handleCreateNewContact = () => {
    setIsCreatingContact(true)
    setShowEditForm(true)
  }

  const handleConfirmContact = async (data: ContactFormData) => {
    try {
      if (isCreatingContact) {
        const newContact = await contactApi.create({
          name: toNullableString(data.name),
          phone: toNullableString(data.phone),
          email: toNullableString(data.email),
          telegram_username: toNullableString(data.telegram_username),
          notes: toNullableString(data.notes),
          is_known: true,
          is_favorite: data.is_favorite ?? undefined,
          life_sphere: toNullableString(data.life_sphere) as Contact['life_sphere'],
          birthday: toNullableString(data.birthday),
          folder_ids: data.folder_ids,
        })
        await messageApi.update(message.id, { contact_id: newContact.id })
        const updated = await contactApi.getById(newContact.id)
        setContact(updated)
        queryClient.invalidateQueries({ queryKey: ['contacts'] })
        queryClient.invalidateQueries({ queryKey: ['contact', newContact.id] })
      } else {
        await contactApi.update(message.contact_id, {
          name: toNullableString(data.name),
          phone: toNullableString(data.phone),
          email: toNullableString(data.email),
          telegram_username: toNullableString(data.telegram_username),
          notes: toNullableString(data.notes),
          is_known: true,
          is_favorite: data.is_favorite ?? undefined,
          life_sphere: toNullableString(data.life_sphere) as Contact['life_sphere'],
          birthday: toNullableString(data.birthday),
          folder_ids: data.folder_ids,
        })
        const updated = await contactApi.getById(message.contact_id)
        setContact(updated)
        queryClient.invalidateQueries({ queryKey: ['contacts'] })
        queryClient.invalidateQueries({ queryKey: ['contact', message.contact_id] })
      }
      setShowEditForm(false)
      setIsCreatingContact(false)
      onReplied()
    } catch (err) {
      console.error('Contact save failed', err)
    }
  }

  const handleMergeContact = async (targetId: number) => {
    if (!contact) return
    if (!confirm('Объединить контакты? Это действие нельзя отменить.')) return
    try {
      const merged = await contactApi.merge(contact.id, targetId)
      await messageApi.update(message.id, { contact_id: merged.id })
      const updated = await contactApi.getById(merged.id)
      setContact(updated)
      queryClient.invalidateQueries({ queryKey: ['contacts'] })
      queryClient.invalidateQueries({ queryKey: ['contact', merged.id] })
      setShowEditForm(false)
      setIsCreatingContact(false)
      onReplied()
    } catch (e) {
      console.error('Merge failed', e)
    }
  }

  const isAnonymous = !!(contact && !contact.name && !contact.phone && !contact.email)
  const displayedContacts = searchQuery.trim() ? searchResults : initialContacts
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" role="button" tabIndex={0} onClick={(e) => { if (e.target === e.currentTarget) onClose() }} onKeyDown={e => { if (e.key === 'Escape') onClose() }}>
      <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden" role="dialog" aria-modal="true">
        <ContactInfo
          message={message}
          contactName={displayName}
          contact={contact}
          contactLoading={contactLoading}
          messageStatus={localStatus}
          isFlagged={localFlag}
                  onMarkUnread={() => {
            messageApi.update(message.id, { status: 'unread' })
              .then((updated) => {
                setLocalStatus('unread')
                if (updated && onMessageUpdate) onMessageUpdate(updated)
                queryClient.setQueriesData<Message[]>({ queryKey: ['messages'] }, (old) =>
                  old?.map((m) => (m.id === message.id ? { ...m, status: 'unread' } : m)),
                )
                queryClient.invalidateQueries({ queryKey: ['dashboard', 'metrics'] })
                onReplied()
              })
              .catch(() => {})
          }}
          onMarkRead={() => {
            messageApi.update(message.id, { status: 'read' })
              .then((updated) => {
                setLocalStatus('read')
                if (updated && onMessageUpdate) onMessageUpdate(updated)
                queryClient.setQueriesData<Message[]>({ queryKey: ['messages'] }, (old) =>
                  old?.map((m) => (m.id === message.id ? { ...m, status: 'read' } : m)),
                )
                queryClient.invalidateQueries({ queryKey: ['dashboard', 'metrics'] })
                onReplied()
              })
              .catch(() => {})
          }}
          onToggleFlag={handleToggleFlag}
          onToggleSpam={handleToggleSpam}
          onClose={onClose}
          onOpenCard={contact && !isAnonymous ? () => setShowContactCard(true) : undefined}
          onEditContact={contact && !isAnonymous ? () => { setIsCreatingContact(false); setShowEditForm(true) } : undefined}
        />

        {contact && isAnonymous && !showEditForm && !showContactSearch && (
          <NewContactBanner
            onFillData={() => { setIsCreatingContact(false); setShowEditForm(true) }}
            onLinkExisting={() => setShowContactSearch(true)}
            onCreateNew={handleCreateNewContact}
          />
        )}

        {showEditForm && (
          <div className="border-b border-gray-200 p-4 bg-gray-50 shrink-0 max-h-[50vh] overflow-y-auto">
            <ContactForm
              initial={isCreatingContact ? null : contact}
              onSubmit={handleConfirmContact}
              onCancel={() => { setShowEditForm(false); setIsCreatingContact(false) }}
              onMerge={contact ? handleMergeContact : undefined}
            />
          </div>
        )}

        {showContactSearch && (
          <ContactSearchPopup
            query={searchQuery}
            contacts={displayedContacts}
            linking={linking}
            onSearch={handleSearchContacts}
            onSelect={handleLinkContact}
            onClose={() => setShowContactSearch(false)}
          />
        )}

        <ThreadList
          ref={threadEndRef}
          messages={thread}
          hasMore={hasMore}
          loadingMore={loadingMore}
          onLoadMore={handleLoadMore}
          onReply={(msg) => { setReplyTarget(msg); replyInputRef.current?.focus() }}
          onCreateTask={(msg) => { setTaskMessage(msg); setTaskModalOpen(true) }}
          onCreateEvent={() => setEventModalOpen(true)}
          onCreateOrder={(msg) => { setOrderMessage(msg); setOrderModalOpen(true) }}
          onDeleteMessage={handleDeleteMessage}
          onForward={(msg) => setForwardTarget(msg)}
        />

        <MessageActions
          message={message}
          contactName={displayName}
          isAnonymous={isAnonymous}
          onActionComplete={onReplied}
        />

        <ReplyBar
          text={replyText}
          sending={sending}
          error={sendError}
          replyTarget={replyTarget}
          attachments={attachments}
          onTextChange={setReplyText}
          onSend={handleSend}
          onKeyDown={handleKeyDown}
          onAttachmentsChange={setAttachments}
          onCancelReply={() => setReplyTarget(null)}
          inputRef={replyInputRef}
          recipientOptions={recipientOptions}
          recipientValue={recipientOverride}
          onRecipientChange={setRecipientOverride}
        />
      </div>

      <Dialog open={showContactCard} onClose={() => setShowContactCard(false)} className="relative z-[60]">
        <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="w-full max-w-md max-h-[90vh] overflow-y-auto rounded-xl" onClick={(e) => e.stopPropagation()}>
            {contact && (
              <ContactDetailPanel
                contact={contact}
                onEdit={() => { setShowContactCard(false); setIsCreatingContact(false); setShowEditForm(true) }}
                onDelete={() => setShowContactCard(false)}
              />
            )}
          </Dialog.Panel>
        </div>
      </Dialog>

      <TaskCreateModal
        open={taskModalOpen}
        onClose={() => setTaskModalOpen(false)}
        initialContactId={message.contact_id}
        initialTitle={displayName}
        initialDescription={taskMessage?.content ?? message.content}
        onCreated={onReplied}
      />

      <CalendarModal
        isOpen={eventModalOpen}
        onClose={() => setEventModalOpen(false)}
        date={new Date()}
        initialContactId={message.contact_id}
        onCreated={() => {
          setEventModalOpen(false)
          onReplied()
        }}
      />

      {orderMessage && (
        <QuickOrderModal
          open={orderModalOpen}
          onClose={() => setOrderModalOpen(false)}
          messageId={orderMessage.id}
          contactId={orderMessage.contact_id}
          contactName={displayName}
          contacts={contactsQuery.data ?? []}
          onCreate={async (data) => { await createOrder.mutateAsync(data) }}
          onCreated={() => { setOrderModalOpen(false); onReplied() }}
        />
      )}

      <ForwardModal
        open={forwardTarget !== null}
        message={forwardTarget}
        onClose={() => setForwardTarget(null)}
        onSent={onReplied}
      />
    </div>
  )
}

export default MessageDetail
