import { memo, useState, useRef, useCallback, useMemo, useEffect } from 'react'
import type { ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { InboxIcon, RefreshCw, MessageSquare, MessageCircle, Clock, Mail, ArrowUpDown, CheckSquare, Star, UserPlus, ShieldAlert, Search, Plus, Pencil, Tag, Check, X } from 'lucide-react'
import MessageDetail from '../components/inbox/MessageDetail'
import ContactQuickActions from '../components/contacts/ContactQuickActions'
import Button from '../components/common/Button'
import Card from '../components/common/Card'
import { SkeletonList } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { useThreadsQuery, useSpamCountQuery, useSpamMessagesQuery, useContactsQuery, useChannelsQuery, useFoldersQuery, useMessageSearchQuery } from '../hooks/queries'
import { channelApi, messageApi, contactApi } from '../api/client'
import { displayNameShort } from '../utils/contactDisplayName'
import { formatRelativeTime, formatLastPolled } from '../utils/format'
import { getChannelIcon } from '../utils/channelIcons'
import FolderEditDialog from '../components/common/FolderEditDialog'
import ComposerModal from '../components/inbox/ComposerModal'
import { filterChats } from '../utils/filterChats'
import { CONTACT_SPHERES, CONTACT_SPHERE_META } from '../types/contactType'
import type { Contact, ContactFolder } from '../types/contact'
import type { ContactSphere } from '../types/contact'
import type { Message } from '../types/message'
import type { ChatItem, Thread } from '../types/inbox'

const POLL_INTERVAL = 10000

type SortMode = 'date' | 'unread'

type InboxTab = 'all' | 'favorites' | 'new' | 'other' | ContactSphere

const TABS: { key: InboxTab; label: string; icon?: typeof Star }[] = [
  { key: 'favorites', label: 'Избранное', icon: Star },
  { key: 'new', label: 'Новое', icon: UserPlus },
  { key: 'work', label: 'Работа', icon: Tag },
  { key: 'personal', label: 'Личное', icon: Tag },
  { key: 'channels', label: 'Каналы', icon: Tag },
  { key: 'other', label: 'Другое', icon: InboxIcon },
  { key: 'spam', label: 'Спам', icon: ShieldAlert },
  { key: 'all', label: 'Все' },
]

const TAB_ORDER_KEY = 'bizibox:tab-order'

function loadTabOrder(): InboxTab[] {
  try {
    const raw = localStorage.getItem(TAB_ORDER_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) {
        const keys = TABS.map(t => t.key)
        const valid = parsed.filter((k: InboxTab) => keys.includes(k))
        if (valid.length === keys.length) return valid
      }
    }
  } catch {
    // ignore
  }
  return TABS.map(t => t.key)
}

const SPHERES_WITH_FOLDERS: ContactSphere[] = ['personal', 'work', 'channels']

const SORT_OPTIONS: { key: SortMode; label: string; icon: typeof ArrowUpDown }[] = [
  { key: 'date', label: 'По дате', icon: ArrowUpDown },
  { key: 'unread', label: 'Непрочитанные', icon: ArrowUpDown },
]

const CHANNEL_FILTERS: { key: string | null; label: string; icon: typeof MessageSquare | null }[] = [
  { key: null, label: 'Все', icon: null },
  { key: 'telegram', label: 'Telegram', icon: MessageSquare },
  { key: 'email', label: 'Email', icon: Mail },
  { key: 'vk', label: 'VK', icon: MessageCircle },
]

const ChatItemButton = memo(function ChatItemButton({
  chat, isSelected, onSelect, onToggle,
}: {
  chat: ChatItem
  isSelected?: boolean
  onSelect: (chat: ChatItem) => void
  onToggle?: (id: number) => void
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect(chat)}
      onKeyDown={(e) => e.key === 'Enter' && onSelect(chat)}
      className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition-colors cursor-pointer hover:bg-gray-50 ${isSelected ? 'bg-primary/5 border-primary/20 ring-1 ring-primary/10' : 'bg-white border-gray-100'}`}
    >
      {onToggle && (
        <div className="shrink-0" role="button" tabIndex={0} onClick={(e) => { e.stopPropagation(); onToggle(chat.contact.id) }} onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); onToggle(chat.contact.id) } }}>
          <CheckSquare className={`w-5 h-5 ${isSelected ? 'text-primary' : 'text-gray-300'}`} />
        </div>
      )}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold truncate text-gray-900">
            {displayNameShort(chat.contact)}
          </span>
          {chat.unreadCount > 0 && (
            <span className="shrink-0 w-5 h-5 flex items-center justify-center rounded-full bg-primary text-white text-xs font-bold">
              {chat.unreadCount}
            </span>
          )}
        </div>
        <p className={`text-sm truncate mt-0.5 ${chat.unreadCount > 0 ? 'text-gray-800 font-medium' : 'text-gray-500'}`}>
          {chat.lastMessage.content}
        </p>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-xs text-gray-400">
            {formatRelativeTime(chat.lastMessage.created_at)}
          </span>
          <div className="flex gap-1">
            {Array.from(chat.channels).map((ch) => {
              const Icon = getChannelIcon(ch)
              return Icon ? <Icon key={ch} className="w-3 h-3 text-gray-400" /> : null
            })}
          </div>
        </div>
      </div>
      <div className="shrink-0 flex items-center gap-1">
        <ContactQuickActions contact={chat.contact} />
      </div>
    </div>
  )
})

function Inbox() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedContactId, setSelectedContactId] = useState<number | null>(null)
  const [selectedMessage, setSelectedMessage] = useState<Message | null>(null)
  const searchQuery = searchParams.get('q') || ''
  const activeChannel: string | null = searchParams.get('channel') || null
  const [tab, setTab] = useState<InboxTab>('all')
  const [folderId, setFolderId] = useState<number | null>(null)
  const [selectedChatIds, setSelectedChatIds] = useState<Set<number>>(new Set())
  const [tabOrder, setTabOrder] = useState<InboxTab[]>(loadTabOrder)
  const [dragTab, setDragTab] = useState<InboxTab | null>(null)
  const [bulkBusy, setBulkBusy] = useState(false)
  const sortMode: SortMode = (searchParams.get('sort') as SortMode) || 'unread'
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const [spamLoading, setSpamLoading] = useState(false)
  const [folderEditOpen, setFolderEditOpen] = useState(false)
  const [composerOpen, setComposerOpen] = useState(false)
  const [folderEditMode, setFolderEditMode] = useState<'create' | 'manage'>('manage')
  const [localSearch, setLocalSearch] = useState(searchQuery)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const contactsRef = useRef<Map<number, Contact>>(new Map())
  const { showToast } = useToast()
  const queryClient = useQueryClient()

  const threadsQuery = useThreadsQuery({ refetchInterval: POLL_INTERVAL })
  const { data: spamCountData } = useSpamCountQuery(POLL_INTERVAL)
  const spamCount = spamCountData?.count ?? 0
  const spamMessagesQuery = useSpamMessagesQuery({ enabled: tab === 'spam' })

  const threads: Thread[] = threadsQuery.data ?? []
  const isLoading = threadsQuery.isLoading
  const error = threadsQuery.error
  const refetch = threadsQuery.refetch

  const { data: channels = [] } = useChannelsQuery()
  const { data: contacts = [] } = useContactsQuery(undefined)
  const { data: folders = [] } = useFoldersQuery()

  const showFavorites = tab === 'favorites'
  const showOnlyNew = tab === 'new'
  const activeSphere: ContactSphere | null =
    tab === 'personal' || tab === 'work' || tab === 'channels' ? tab : null
  const activeFolder: number | null = activeSphere ? folderId : null

  const foldersOfSphere = useMemo(() => {
    return folders.filter(
      (f) => !f.parent_id && (f.sphere || 'personal') === tab,
    )
  }, [folders, tab])

  const searchActive = searchQuery.trim().length > 0
  const { data: searchResults = [] } = useMessageSearchQuery(searchActive ? searchQuery : '')

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      updateSearchParams({ q: localSearch })
    }, 300)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [localSearch])

  const contactsMap = useMemo(() => {
    const map = new Map<number, Contact>()
    if (Array.isArray(contacts)) {
      contacts.forEach((c: Contact) => map.set(c.id, c))
    }
    contactsRef.current = map
    return map
  }, [contacts])

  const contactIdFromUrl = searchParams.get('contact_id')
  const urlSelectionAppliedRef = useRef<string | null>(null)

  useEffect(() => {
    if (!contactIdFromUrl || urlSelectionAppliedRef.current === contactIdFromUrl) return
    const cid = parseInt(contactIdFromUrl, 10)
    if (isNaN(cid)) return
    const thread = threads.find((t) => t.contact_id === cid)
    if (thread) {
      setSelectedContactId(cid)
      setSelectedMessage(thread.last_message)
      urlSelectionAppliedRef.current = contactIdFromUrl
    }
  }, [contactIdFromUrl, threads])

  const newChatCount = useMemo(() => {
    return threads.filter((t) => t.unread_count > 0).length
  }, [threads])

  const allChats = useMemo<ChatItem[]>(() => {
    if (searchActive) {
      const grouped = new Map<number, Message[]>()
      for (const msg of searchResults) {
        const contact = contactsMap.get(msg.contact_id)
        if (!contact) continue
        const list = grouped.get(msg.contact_id)
        if (list) list.push(msg)
        else grouped.set(msg.contact_id, [msg])
      }

      const result: ChatItem[] = []
      for (const [contactId, msgs] of grouped) {
        const contact = contactsMap.get(contactId)!
        const sorted = [...msgs].sort((a, b) => {
          const da = new Date(a.created_at || 0).getTime()
          const db = new Date(b.created_at || 0).getTime()
          return db - da
        })
        result.push({
          contact,
          lastMessage: sorted[0],
          unreadCount: msgs.filter((m) => m.status === 'unread').length,
          channels: new Set(msgs.map((m) => m.channel)),
        })
      }
      return result
    }

    const result: ChatItem[] = []
    for (const t of threads) {
      const contact = contactsMap.get(t.contact_id)
      if (!contact) continue
      result.push({
        contact,
        lastMessage: t.last_message,
        unreadCount: t.unread_count,
        channels: new Set(t.channels),
      })
    }
    return result
  }, [searchActive, searchResults, threads, contactsMap])

  const spamChats = useMemo<ChatItem[]>(() => {
    const messages = spamMessagesQuery.data ?? []
    const grouped = new Map<number, Message[]>()
    for (const msg of messages) {
      const list = grouped.get(msg.contact_id)
      if (list) list.push(msg)
      else grouped.set(msg.contact_id, [msg])
    }
    const result: ChatItem[] = []
    for (const [contactId, msgs] of grouped) {
      const contact = contactsMap.get(contactId)
      if (!contact) continue
      const sorted = [...msgs].sort(
        (a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime(),
      )
      result.push({
        contact,
        lastMessage: sorted[0],
        unreadCount: msgs.filter((m) => m.status === 'unread').length,
        channels: new Set(msgs.map((m) => m.channel)),
      })
    }
    return result
  }, [spamMessagesQuery.data, contactsMap])

  const favoriteCount = useMemo(() => {
    return allChats.filter((c) => c.contact.is_favorite).length
  }, [allChats])

  const otherCount = useMemo(() => {
    return allChats.filter((c) => c.contact.life_sphere == null && c.contact.folder_id == null).length
  }, [allChats])

  const channelsCount = useMemo(() => {
    return allChats.filter((c) => c.contact.life_sphere === 'channels').length
  }, [allChats])

  const folderCounts = useMemo(() => {
    const counts: Record<number, number> = {}
    for (const chat of allChats) {
      const fid = chat.contact.folder_id
      if (fid != null) counts[fid] = (counts[fid] || 0) + 1
    }
    return counts
  }, [allChats])

  const chats = useMemo(() => {
    const base = tab === 'spam' ? spamChats : allChats
    const filtered = filterChats(base, {
      channel: activeChannel,
      folder: tab === 'other' ? 'other' : activeFolder,
      showOnlyNew,
      favorites: showFavorites,
      searchQuery: '',
      lifeSphere: tab === 'spam' ? 'spam' : activeSphere,
    })

    if (sortMode === 'date') {
      filtered.sort((a, b) => {
        const da = new Date(a.lastMessage.created_at || 0).getTime()
        const db = new Date(b.lastMessage.created_at || 0).getTime()
        return db - da
      })
    } else if (sortMode === 'unread') {
      filtered.sort((a, b) => {
        if (a.unreadCount > 0 && b.unreadCount === 0) return -1
        if (a.unreadCount === 0 && b.unreadCount > 0) return 1
        const da = new Date(a.lastMessage.created_at || 0).getTime()
        const db = new Date(b.lastMessage.created_at || 0).getTime()
        return db - da
      })
    }
    return filtered
  }, [allChats, spamChats, activeChannel, activeFolder, showOnlyNew, showFavorites, searchQuery, sortMode, activeSphere, tab])

  const totalChats = useMemo(() => {
    return filterChats(tab === 'spam' ? spamChats : allChats, {
      channel: activeChannel,
      folder: tab === 'other' ? 'other' : null,
      showOnlyNew,
      favorites: showFavorites,
      searchQuery: '',
      lifeSphere: tab === 'spam' ? 'spam' : activeSphere,
    }).length
  }, [allChats, spamChats, activeChannel, showOnlyNew, showFavorites, searchQuery, activeSphere, tab])

  const getContactName = useCallback((contactId: number): string | null => {
    const c = contactsRef.current.get(contactId)
    return c ? displayNameShort(c) : null
  }, [])

  const handleChatClick = useCallback((chat: ChatItem) => {
    setSelectedContactId(chat.contact.id)
    setSelectedMessage(chat.lastMessage)
  }, [])

  const activeChannelInfo = useMemo(() => {
    if (!activeChannel) return null
    return channels.find((ch: { type: string }) => ch.type === activeChannel) || null
  }, [activeChannel, channels])

  const handleDownload = async () => {
    if (!activeChannel || downloading) return
    setDownloading(true)
    setDownloadError(null)
    try {
      await channelApi.download(activeChannel)
      refetch()
      showToast('Сообщения загружены', 'success')
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Ошибка загрузки'
      setDownloadError(msg)
    } finally {
      setDownloading(false)
    }
  }

  const updateSearchParams = useCallback((updates: Record<string, string>) => {
    const next = new URLSearchParams(searchParams)
    for (const [k, v] of Object.entries(updates)) {
      if (v) next.set(k, v)
      else next.delete(k)
    }
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams])

  const handleTabChange = (t: InboxTab) => {
    setTab(t)
    setFolderId(null)
  }

  const handleFolderChange = (fid: number | null) => {
    setFolderId(fid)
  }

  const handleChannelChange = (channel: string | null) => {
    updateSearchParams({ channel: channel || '' })
  }

  const handleSortChange = (mode: SortMode) => {
    updateSearchParams({ sort: mode === 'date' ? '' : mode })
  }

  const handleLoadChannels = async () => {
    try {
      refetch()
      await messageApi.loadChannels(folderId ?? undefined)
      refetch()
      showToast('Каналы загружены', 'success')
    } catch {
      showToast('Ошибка загрузки', 'error')
    }
  }

  const handleLoadSpam = async () => {
    if (spamLoading) return
    setSpamLoading(true)
    queryClient.invalidateQueries({ queryKey: ['messages', 'spam'] })
    try {
      await messageApi.loadSpam()
      queryClient.invalidateQueries({ queryKey: ['messages', 'spam'] })
      queryClient.invalidateQueries({ queryKey: ['messages', 'spam', 'count'] })
      showToast('Спам загружен', 'success')
    } catch {
      showToast('Не удалось загрузить спам', 'error')
    } finally {
      setSpamLoading(false)
    }
  }

  const handleShowLoadedChannels = () => {
    refetch()
    showToast('Показаны загруженные каналы', 'success')
  }

  const handleShowLoadedSpam = () => {
    spamMessagesQuery.refetch()
    showToast('Показан загруженный спам', 'success')
  }

  const orderedTabs = useMemo(() => {
    const byKey = new Map(TABS.map(t => [t.key, t]))
    return tabOrder.map(k => byKey.get(k)).filter((t): t is NonNullable<typeof t> => !!t)
  }, [tabOrder])

  const persistTabOrder = (order: InboxTab[]) => {
    setTabOrder(order)
    try {
      localStorage.setItem(TAB_ORDER_KEY, JSON.stringify(order))
    } catch {
      // ignore
    }
  }

  const handleTabDrop = (target: InboxTab) => {
    if (!dragTab || dragTab === target) return
    const next = [...tabOrder]
    const from = next.indexOf(dragTab)
    const to = next.indexOf(target)
    if (from === -1 || to === -1) return
    next.splice(from, 1)
    next.splice(to, 0, dragTab)
    persistTabOrder(next)
    setDragTab(null)
  }

  const handleBulkRead = async () => {
    if (selectedChatIds.size === 0 || bulkBusy) return
    setBulkBusy(true)
    try {
      await Promise.all(Array.from(selectedChatIds).map(id => messageApi.markContactRead(id)))
      showToast('Помечено прочитанным', 'success')
      setSelectedChatIds(new Set())
      queryClient.invalidateQueries({ queryKey: ['threads'] })
      queryClient.invalidateQueries({ queryKey: ['metrics'] })
      refetch()
    } catch {
      showToast('Не удалось пометить прочитанным', 'error')
    } finally {
      setBulkBusy(false)
    }
  }

  const handleBulkClassify = async (sphere: ContactSphere, folderId?: number) => {
    if (selectedChatIds.size === 0 || bulkBusy) return
    setBulkBusy(true)
    try {
      const payload: { ids: number[]; life_sphere: ContactSphere; folder_id?: number } = {
        ids: Array.from(selectedChatIds),
        life_sphere: sphere,
      }
      if (folderId !== undefined) payload.folder_id = folderId
      await contactApi.bulkUpdate(payload)
      showToast('Классифицировано', 'success')
      setSelectedChatIds(new Set())
      queryClient.invalidateQueries({ queryKey: ['contacts'] })
      queryClient.invalidateQueries({ queryKey: ['threads'] })
      refetch()
    } catch {
      showToast('Не удалось классифицировать', 'error')
    } finally {
      setBulkBusy(false)
    }
  }

  const renderFolderOption = (folder: ContactFolder, depth: number): ReactNode[] => {
    const children = folders.filter(f => f.parent_id === folder.id)
    return [
      <option key={folder.id} value={`folder:${folder.id}`}>
        {'\u00A0\u00A0\u00A0\u00A0'.repeat(depth)}{depth > 0 ? '↳ ' : ''}{folder.name}
      </option>,
      ...children.flatMap(c => renderFolderOption(c, depth + 1)),
    ]
  }

  if (isLoading && threads.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <InboxIcon className="w-6 h-6 text-primary" />
          <h2 className="text-2xl font-semibold text-gray-900">Входящие</h2>
        </div>
        <SkeletonList count={5} />
      </div>
    )
  }

  if (error && threads.length === 0) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold text-gray-900">Входящие</h2>
        <Card>
          <div className="text-center py-8">
            <p className="text-red-500 mb-4">{error instanceof Error ? error.message : 'Ошибка загрузки'}</p>
            <Button onClick={() => refetch()}>Повторить</Button>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <div className="sticky top-0 z-10 bg-background pb-3 space-y-2.5">
        {selectedChatIds.size > 0 && (
          <div className="flex items-center gap-2 px-3 py-2 bg-blue-50 border border-blue-200 rounded-xl flex-wrap">
            <span className="text-sm font-medium text-blue-700 shrink-0">
              Выбрано: {selectedChatIds.size}
            </span>
            <Button size="sm" onClick={handleBulkRead} disabled={bulkBusy}>
              <Check className="w-4 h-4 mr-1" />
              Прочитано
            </Button>
            <select
              value=""
              disabled={bulkBusy}
              onChange={(e) => {
                const v = e.target.value
                if (!v) return
                if (v.startsWith('folder:')) {
                  const fid = Number(v.slice('folder:'.length))
                  const folder = folders.find(f => f.id === fid)
                  if (folder) handleBulkClassify((folder.sphere || 'personal') as ContactSphere, fid)
                } else {
                  handleBulkClassify(v as ContactSphere)
                }
              }}
              className="px-2 py-1.5 text-sm border border-gray-200 rounded-lg bg-white outline-none focus:border-primary"
            >
              <option value="" disabled>Классифицировать…</option>
              {CONTACT_SPHERES.map(s => {
                const sphereFolders = folders.filter(f => (f.sphere || 'personal') === s)
                const topLevel = sphereFolders.filter(f => !f.parent_id)
                if (s === 'spam' || topLevel.length === 0) {
                  return <option key={s} value={s}>{CONTACT_SPHERE_META[s].label}</option>
                }
                return (
                  <optgroup key={s} label={CONTACT_SPHERE_META[s].label}>
                    <option value={s}>{CONTACT_SPHERE_META[s].label} (без папки)</option>
                    {topLevel.map(f => renderFolderOption(f, 0))}
                  </optgroup>
                )
              })}
            </select>
            <button
              onClick={() => setSelectedChatIds(new Set())}
              className="ml-auto p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100"
              title="Снять выделение"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        <div className="flex items-center gap-3">
          <InboxIcon className="w-6 h-6 text-primary shrink-0" />
          <h2 className="text-2xl font-semibold text-gray-900 truncate">Входящие</h2>
          <span className="text-sm text-gray-400 font-normal">
            {chats.length} {chats.length === 1 ? 'диалог' : 'диалогов'}
          </span>
          <div className="flex-1" />
          <div className="relative flex-1 max-w-xs">
            <input
              type="text"
              value={localSearch}
              onChange={(e) => setLocalSearch(e.target.value)}
              placeholder="Поиск..."
              className="w-full px-3 py-1.5 pl-8 rounded-lg border border-gray-200 bg-white text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors"
            />
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
          </div>
          <div className="flex items-center gap-1 bg-white border border-gray-200 rounded-lg p-0.5">
            {SORT_OPTIONS.map((opt) => {
              const Icon = opt.icon
              return (
                <button
                  key={opt.key}
                  onClick={() => handleSortChange(opt.key)}
                  className={`p-1.5 rounded-md text-xs transition-colors ${sortMode === opt.key ? 'bg-primary text-white' : 'text-gray-400 hover:text-gray-600'}`}
                  title={opt.label}
                >
                  <Icon className="w-3.5 h-3.5" />
                </button>
              )
            })}
          </div>
          <Button variant="ghost" size="sm" onClick={() => refetch()} className="shrink-0">
            <RefreshCw className="w-4 h-4 mr-1" />
            Обновить
          </Button>
          <Button size="sm" onClick={() => setComposerOpen(true)} className="shrink-0">
            <Plus className="w-4 h-4 mr-1" />
            Написать новое
          </Button>
        </div>

        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1">
            {CHANNEL_FILTERS.map((f) => {
              const isActive = activeChannel === f.key
              const count = f.key ? ((tab === 'spam' ? spamChats : allChats).filter(c => c.channels.has(f.key!)).length) : totalChats
              const Icon = f.icon
              return (
                <button
                  key={f.label}
                  onClick={() => handleChannelChange(f.key)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary text-white shadow-sm'
                      : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  {Icon && <Icon className="w-4 h-4" />}
                  <span>{f.label}</span>
                  <span className={`text-xs ml-0.5 ${isActive ? 'text-white/80' : 'text-gray-400'}`}>
                    {count}
                  </span>
                </button>
              )
            })}
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            <button
              onClick={() => { setFolderEditMode('create'); setFolderEditOpen(true) }}
              className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-50 border border-dashed border-gray-300"
              title="Создать папку"
            >
              <Plus className="w-3.5 h-3.5" />
              Создать папку
            </button>
            <button
              onClick={() => { setFolderEditMode('manage'); setFolderEditOpen(true) }}
              className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-50"
              title="Редактировать папки"
            >
              <Pencil className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="flex items-center gap-1 flex-wrap">
          {orderedTabs.map((t) => {
            const isActive = tab === t.key
            const count = t.key === 'favorites' ? favoriteCount
              : t.key === 'new' ? newChatCount
              : t.key === 'other' ? otherCount
              : t.key === 'channels' ? channelsCount
              : t.key === 'spam' ? spamCount
              : null
            const Icon = t.icon
            return (
              <button
                key={t.key}
                draggable
                onDragStart={() => setDragTab(t.key)}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => handleTabDrop(t.key)}
                onDragEnd={() => setDragTab(null)}
                onClick={() => handleTabChange(t.key)}
                title="Перетащите, чтобы изменить порядок"
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors cursor-grab active:cursor-grabbing ${
                  isActive
                    ? 'bg-primary text-white shadow-sm'
                    : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
                }`}
              >
                {Icon && <Icon className={`w-4 h-4 ${isActive && t.key === 'favorites' ? 'fill-white text-white' : ''}`} />}
                <span>{t.label}</span>
                {count !== null && count > 0 && (
                  <span className={`text-xs ml-0.5 ${isActive ? 'text-white/80' : 'text-gray-400'}`}>
                    {count}
                  </span>
                )}
              </button>
            )
          })}
        </div>

        {SPHERES_WITH_FOLDERS.includes(tab as ContactSphere) && (
          <div className="flex items-center gap-1 flex-wrap">
            {foldersOfSphere.map((folder) => {
              const isActive = folderId === folder.id
              return (
                <button
                  key={folder.id}
                  onClick={() => handleFolderChange(folder.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary text-white shadow-sm'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: folder.color || '#9ca3af' }}
                  />
                  <span>{folder.name}</span>
                  <span className={`text-xs ml-0.5 ${isActive ? 'text-white/80' : 'text-gray-400'}`}>
                    {folderCounts[folder.id] ?? 0}
                  </span>
                </button>
              )
            })}
            <button
              onClick={() => handleFolderChange(null)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                folderId === null
                  ? 'bg-primary text-white shadow-sm'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              Все
            </button>
            {tab === 'channels' && (
              <div className="flex items-center gap-2">
                <button
                  onClick={handleLoadChannels}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 hover:bg-blue-100 transition-colors"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Загрузить новые
                </button>
                <button
                  onClick={handleShowLoadedChannels}
                  className="px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 border border-gray-200 hover:bg-gray-50 transition-colors"
                >
                  Показать загруженные
                </button>
              </div>
            )}
          </div>
        )}

        {tab === 'spam' && (
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={handleLoadSpam}
              disabled={spamLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 hover:bg-blue-100 transition-colors disabled:opacity-60"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${spamLoading ? 'animate-spin' : ''}`} />
              {spamLoading ? 'Загрузка...' : 'Загрузить новые'}
            </button>
            <button
              onClick={handleShowLoadedSpam}
              className="px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 border border-gray-200 hover:bg-gray-50 transition-colors"
            >
              Показать загруженные
            </button>
          </div>
        )}

        {activeChannel && activeChannelInfo && (
          <div className="flex items-center gap-3 px-4 py-2.5 bg-blue-50 border border-blue-200 rounded-xl text-sm">
            <Clock className="w-4 h-4 text-blue-600 shrink-0" />
            <span className="text-blue-700">
              Последняя загрузка: {formatLastPolled(activeChannelInfo.last_polled_at)}
            </span>
            <div className="ml-auto flex items-center gap-2">
              {downloadError && (
                <span className="text-xs text-red-600">{downloadError}</span>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={handleDownload}
                disabled={downloading}
                className="text-blue-700 hover:text-blue-800 hover:bg-blue-100"
              >
                <RefreshCw className={`w-4 h-4 mr-1 ${downloading ? 'animate-spin' : ''}`} />
                {downloading ? 'Загрузка...' : 'Загрузить'}
              </Button>
            </div>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pb-6">
        {chats.length === 0 ? (
          <Card>
            <div className="text-center py-8">
              <MessageSquare className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">
                {searchQuery ? 'Ничего не найдено' :
                 activeChannel ? `Нет диалогов в ${CHANNEL_FILTERS.find(f => f.key === activeChannel)?.label ?? activeChannel}` :
                 activeFolder ? `Нет диалогов в папке "${folders.find(f => f.id === activeFolder)?.name}"` :
                 showOnlyNew ? 'Нет новых диалогов' :
                 showFavorites ? 'Нет избранных диалогов' :
                 tab === 'channels' ? 'Диалоги из каналов не загружены' :
                 tab === 'spam' ? 'Спам-диалоги не загружены' :
                 activeSphere ? 'Нет диалогов в этом разделе' :
                 'Нет сообщений'}
              </p>
              {tab === 'channels' && (
                <div className="mt-4 flex items-center justify-center gap-2">
                  <button
                    onClick={handleLoadChannels}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 hover:bg-blue-100 transition-colors"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Загрузить новые
                  </button>
                  <button
                    onClick={handleShowLoadedChannels}
                    className="px-4 py-2 rounded-lg text-sm font-medium text-gray-600 border border-gray-200 hover:bg-gray-50 transition-colors"
                  >
                    Показать загруженные
                  </button>
                </div>
              )}
              {tab === 'spam' && (
                <div className="mt-4 flex items-center justify-center gap-2">
                  <button
                    onClick={handleLoadSpam}
                    disabled={spamLoading}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 hover:bg-blue-100 transition-colors disabled:opacity-60"
                  >
                    <RefreshCw className={`w-4 h-4 ${spamLoading ? 'animate-spin' : ''}`} />
                    {spamLoading ? 'Загрузка...' : 'Загрузить новые'}
                  </button>
                  <button
                    onClick={handleShowLoadedSpam}
                    className="px-4 py-2 rounded-lg text-sm font-medium text-gray-600 border border-gray-200 hover:bg-gray-50 transition-colors"
                  >
                    Показать загруженные
                  </button>
                </div>
              )}
            </div>
          </Card>
        ) : (
          chats.map((chat) => (
            <ChatItemButton
              key={chat.contact.id}
              chat={chat}
              isSelected={selectedChatIds.has(chat.contact.id)}
              onToggle={(id) => {
                const next = new Set(selectedChatIds)
                if (next.has(id)) next.delete(id); else next.add(id)
                setSelectedChatIds(next)
              }}
              onSelect={handleChatClick}
            />
          ))
        )}
      </div>

      {selectedMessage && selectedContactId !== null && (
        <MessageDetail
          message={selectedMessage}
          contactName={getContactName(selectedContactId)}
          onClose={() => {
            setSelectedMessage(null); setSelectedContactId(null); setSearchParams({})
            queryClient.invalidateQueries({ queryKey: ['messages'] })
            queryClient.invalidateQueries({ queryKey: ['threads'] })
            queryClient.invalidateQueries({ queryKey: ['metrics'] })
            queryClient.invalidateQueries({ queryKey: ['dashboard', 'metrics'] })
            refetch()
          }}
          onReplied={() => {
            queryClient.invalidateQueries({ queryKey: ['messages'] })
            queryClient.invalidateQueries({ queryKey: ['threads'] })
            queryClient.invalidateQueries({ queryKey: ['metrics'] })
            queryClient.invalidateQueries({ queryKey: ['dashboard', 'metrics'] })
            refetch()
          }}
          onMessageUpdate={(msg) => setSelectedMessage(msg)}
        />
      )}

      <FolderEditDialog
        open={folderEditOpen}
        onClose={() => setFolderEditOpen(false)}
        initialMode={folderEditMode}
      />

      <ComposerModal
        open={composerOpen}
        onClose={() => setComposerOpen(false)}
        onSent={() => {
          refetch()
          queryClient.invalidateQueries({ queryKey: ['messages'] })
          queryClient.invalidateQueries({ queryKey: ['threads'] })
        }}
      />
    </div>
  )
}

export default Inbox
