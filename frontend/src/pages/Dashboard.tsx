import { useMemo, useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertCircle,
  ArrowRight,
  Cake,
  CalendarPlus,
  Inbox,
  ListTodo,
  MessageSquare,
  UserPlus,
  X,
  Plus,
  Folder,
} from 'lucide-react'
import Card from '../components/common/Card'
import PulseWidget from '../components/dashboard/PulseWidget'
import TasksBoard from '../components/dashboard/TasksBoard'
import OrdersBoard from '../components/dashboard/OrdersBoard'
import TaskCreateModal from '../components/tasks/TaskCreateModal'
import { CalendarModal } from '../components/calendar/CalendarModal'
import ContactForm, { toNullableString } from '../components/contacts/ContactForm'
import Modal from '../components/common/Modal'
import { useDashboardMetricsQuery, useInboxMessagesQuery, useTasksQuery, useContactsQuery, useCreateContactMutation, useFoldersQuery } from '../hooks/queries'
import { displayNameShort } from '../utils/contactDisplayName'
import { formatRelativeTime } from '../utils/format'
import type { Contact } from '../types/contact'
import type { Task } from '../types/task'
import type { ContactFormData } from '../schemas'

function formatDay(dateStr: string | null): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}

function isOverdue(task: Task): boolean {
  return task.status !== 'completed' && !!task.due_date && new Date(task.due_date) < new Date()
}

function isToday(task: Task): boolean {
  if (!task.due_date) return false
  const d = new Date(task.due_date)
  const now = new Date()
  return d.toDateString() === now.toDateString()
}

function UpcomingBirthdays({ contacts }: { contacts: Contact[] }) {
  const now = new Date()
  const upcoming = contacts
    .filter((c) => c.birthday)
    .map((c) => {
      const b = new Date(c.birthday as string)
      const next = new Date(now.getFullYear(), b.getMonth(), b.getDate())
      if (next < now) next.setFullYear(now.getFullYear() + 1)
      return { contact: c, next }
    })
    .sort((a, b) => a.next.getTime() - b.next.getTime())
    .slice(0, 5)

  if (upcoming.length === 0) {
    return <p className="text-sm text-gray-400">Нет ближайших дней рождения</p>
  }

  return (
    <div className="space-y-2">
      {upcoming.map(({ contact, next }) => (
        <Link key={contact.id} to={`/contacts?contact_id=${contact.id}`} className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50">
          <Cake className="w-4 h-4 text-pink-500 shrink-0" />
          <span className="flex-1 min-w-0 truncate text-sm text-gray-800">{displayNameShort(contact)}</span>
          <span className="text-xs text-gray-400 shrink-0">
            {next.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })}
          </span>
        </Link>
      ))}
    </div>
  )
}

function UnreadSection({ unreadMessages, unreadChats }: { unreadMessages: number; unreadChats: number }) {
  return (
    <Link to="/inbox?new=1" className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 group">
      <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
        <Inbox className="w-4 h-4 text-blue-600" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900">Непрочитанные</p>
        <p className="text-xs text-gray-400">{unreadChats} диалогов</p>
      </div>
      <span className="text-xl font-bold text-blue-600">{unreadMessages}</span>
      <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-gray-500" />
    </Link>
  )
}

function QuickCreate({ onCreateTask, onCreateEvent, onCreateContact }: {
  onCreateTask: () => void
  onCreateEvent: () => void
  onCreateContact: () => void
}) {
  const items = [
    { label: 'Задача', icon: ListTodo, color: 'text-amber-600 bg-amber-50', onClick: onCreateTask },
    { label: 'Событие', icon: CalendarPlus, color: 'text-indigo-600 bg-indigo-50', onClick: onCreateEvent },
    { label: 'Контакт', icon: UserPlus, color: 'text-green-600 bg-green-50', onClick: onCreateContact },
  ]
  return (
    <div className="flex gap-2 flex-wrap">
      {items.map((item) => {
        const Icon = item.icon
        return (
          <button key={item.label} onClick={item.onClick} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50">
            <span className={`w-6 h-6 rounded-md flex items-center justify-center ${item.color}`}>
              <Icon className="w-3.5 h-3.5" />
            </span>
            {item.label}
          </button>
        )
      })}
    </div>
  )
}

type DashboardPin = { type: 'folder' | 'chat'; id: number }

const PIN_KEY = 'bizibox:dashboard-pins'

function loadPins(): DashboardPin[] {
  try {
    const raw = localStorage.getItem(PIN_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter((p) => p && p.id) : []
  } catch {
    return []
  }
}

function PinnedWidget({
  folders,
  chats,
}: {
  folders: { id: number; name: string; color: string | null }[]
  chats: Contact[]
}) {
  const [pins, setPins] = useState<DashboardPin[]>(loadPins)
  const [configOpen, setConfigOpen] = useState(false)

  useEffect(() => {
    try {
      localStorage.setItem(PIN_KEY, JSON.stringify(pins))
    } catch {
      // ignore
    }
  }, [pins])

  const togglePin = (pin: DashboardPin) => {
    setPins((prev) =>
      prev.some((p) => p.type === pin.type && p.id === pin.id)
        ? prev.filter((p) => !(p.type === pin.type && p.id === pin.id))
        : [...prev, pin],
    )
  }

  const isPinned = (pin: DashboardPin) =>
    pins.some((p) => p.type === pin.type && p.id === pin.id)

  const pinnedFolders = pins.filter((p) => p.type === 'folder').map((p) => folders.find((f) => f.id === p.id)).filter(Boolean)
  const pinnedChats = pins.filter((p) => p.type === 'chat').map((p) => chats.find((c) => c.id === p.id)).filter(Boolean)

  return (
    <Card title="Закреплено">
      {(pinnedFolders.length === 0 && pinnedChats.length === 0) ? (
        <p className="text-sm text-gray-400">Закрепите папки и чаты для быстрого доступа</p>
      ) : (
        <div className="space-y-1">
          {pinnedFolders.map((f) => (
            <div key={`f-${f!.id}`} className="group flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-50">
              <Folder className="w-4 h-4 text-gray-400 shrink-0" />
              <Link to={`/contacts`} className="flex-1 min-w-0 text-sm text-gray-800 truncate hover:text-blue-600">
                {f!.name}
              </Link>
              <button onClick={() => togglePin({ type: 'folder', id: f!.id })} className="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-500 shrink-0">
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
          {pinnedChats.map((c) => (
            <div key={`c-${c!.id}`} className="group flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-50">
              <MessageSquare className="w-4 h-4 text-gray-400 shrink-0" />
              <Link to={`/inbox?contact_id=${c!.id}`} className="flex-1 min-w-0 text-sm text-gray-800 truncate hover:text-blue-600">
                {displayNameShort(c!)}
              </Link>
              <button onClick={() => togglePin({ type: 'chat', id: c!.id })} className="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-500 shrink-0">
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      <button
        onClick={() => setConfigOpen(true)}
        className="mt-3 flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
      >
        <Plus className="w-4 h-4" />
        Настроить
      </button>

      {configOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <button type="button" aria-label="Закрыть" tabIndex={-1} className="fixed inset-0 bg-black/30" onClick={() => setConfigOpen(false)} />
          <div className="relative bg-white rounded-xl shadow-xl p-5 w-full max-w-md max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <p className="text-lg font-semibold text-gray-900">Закрепить на дашборде</p>
              <button onClick={() => setConfigOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto space-y-4">
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase mb-1">Папки</p>
                <div className="space-y-1">
                  {folders.length === 0 && <p className="text-sm text-gray-400">Нет папок</p>}
                  {folders.map((f) => (
                    <label key={f.id} className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-50 cursor-pointer">
                      <input type="checkbox" checked={isPinned({ type: 'folder', id: f.id })} onChange={() => togglePin({ type: 'folder', id: f.id })} className="w-4 h-4" />
                      <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: f.color || '#d1d5db' }} />
                      <span className="text-sm text-gray-700">{f.name}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase mb-1">Чаты</p>
                <div className="space-y-1">
                  {chats.length === 0 && <p className="text-sm text-gray-400">Нет диалогов</p>}
                  {chats.map((c) => (
                    <label key={c.id} className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-50 cursor-pointer">
                      <input type="checkbox" checked={isPinned({ type: 'chat', id: c.id })} onChange={() => togglePin({ type: 'chat', id: c.id })} className="w-4 h-4" />
                      <span className="text-sm text-gray-700">{displayNameShort(c)}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex justify-end mt-4">
              <button onClick={() => setConfigOpen(false)} className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700">Готово</button>
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}

function Dashboard() {
  const metricsQuery = useDashboardMetricsQuery()
  const tasksQuery = useTasksQuery({ limit: 100 })
  const messagesQuery = useInboxMessagesQuery()
  const contactsQuery = useContactsQuery({ limit: 100 })
  const createContact = useCreateContactMutation()
  const foldersQuery = useFoldersQuery()

  const [taskModalOpen, setTaskModalOpen] = useState(false)
  const [eventModalOpen, setEventModalOpen] = useState(false)
  const [contactModalOpen, setContactModalOpen] = useState(false)

  const handleCreateContact = async (data: ContactFormData) => {
    await createContact.mutateAsync({
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
    setContactModalOpen(false)
  }

  const metrics = metricsQuery.data
  const tasks = tasksQuery.data ?? []
  const messages = messagesQuery.data ?? []
  const contacts = contactsQuery.data ?? []
  const folders = foldersQuery.data ?? []

  const chatContacts = useMemo(() => {
    const ids = new Set<number>()
    for (const msg of messages) ids.add(msg.contact_id)
    return contacts.filter((c) => ids.has(c.id))
  }, [messages, contacts])

  const todayTasks = useMemo(() => tasks.filter(isToday), [tasks])
  const overdueTasks = useMemo(() => tasks.filter(isOverdue), [tasks])

  const recentDialogues = useMemo(() => {
    const grouped = new Map<number, { contact: Contact; last: typeof messages[number] }>()
    for (const msg of messages) {
      const existing = grouped.get(msg.contact_id)
      if (!existing || new Date(msg.created_at || 0) > new Date(existing.last.created_at || 0)) {
        const contact = contacts.find((c) => c.id === msg.contact_id && c.life_sphere === 'personal')
        if (contact) grouped.set(msg.contact_id, { contact, last: msg })
      }
    }
    return Array.from(grouped.values()).slice(0, 5)
  }, [messages, contacts])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-gray-900">Дашборд</h2>
        <QuickCreate
          onCreateTask={() => setTaskModalOpen(true)}
          onCreateEvent={() => setEventModalOpen(true)}
          onCreateContact={() => setContactModalOpen(true)}
        />
      </div>

      <PulseWidget />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <Card title="Сегодня">
            {todayTasks.length === 0 ? (
              <p className="text-sm text-gray-400">На сегодня задач нет</p>
            ) : (
              <div className="space-y-2">
                {todayTasks.map((task) => (
                  <Link key={task.id} to={`/tasks?contact_id=${task.contact_id ?? ''}`} className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50">
                    <ListTodo className="w-4 h-4 text-amber-500 shrink-0" />
                    <span className="flex-1 min-w-0 truncate text-sm text-gray-800">{task.title}</span>
                    {task.due_date && <span className="text-xs text-gray-400 shrink-0">{formatDay(task.due_date)}</span>}
                  </Link>
                ))}
              </div>
            )}
          </Card>

          <Card title="Просроченное">
            {overdueTasks.length === 0 ? (
              <p className="text-sm text-gray-400">Просроченных задач нет</p>
            ) : (
              <div className="space-y-2">
                {overdueTasks.map((task) => (
                  <Link key={task.id} to="/tasks" className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-red-50">
                    <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
                    <span className="flex-1 min-w-0 truncate text-sm text-gray-800">{task.title}</span>
                    {task.due_date && <span className="text-xs text-red-400 shrink-0">{formatDay(task.due_date)}</span>}
                  </Link>
                ))}
              </div>
            )}
          </Card>

          <TasksBoard />

          <OrdersBoard />
        </div>

        <div className="space-y-4">
          <Card title="Непрочитанные">
            <UnreadSection unreadMessages={metrics?.unread_messages ?? 0} unreadChats={metrics?.unread_chats ?? 0} />
          </Card>

          <Card title="Диалоги">
            {recentDialogues.length === 0 ? (
              <p className="text-sm text-gray-400">Нет диалогов</p>
            ) : (
              <div className="space-y-2">
                {recentDialogues.map(({ contact, last }) => (
                  <Link key={contact.id} to={`/inbox?contact_id=${contact.id}`} className="flex items-start gap-3 px-3 py-2 rounded-lg hover:bg-gray-50">
                    <MessageSquare className="w-4 h-4 text-gray-400 shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{displayNameShort(contact)}</p>
                      <p className="text-xs text-gray-400 truncate">{last.content}</p>
                    </div>
                    <span className="text-xs text-gray-300 shrink-0">{formatRelativeTime(last.created_at)}</span>
                  </Link>
                ))}
              </div>
            )}
          </Card>

          <Card title="Дни рождения">
            <UpcomingBirthdays contacts={contacts} />
          </Card>

          <PinnedWidget folders={folders} chats={chatContacts} />
        </div>
      </div>

      <TaskCreateModal
        open={taskModalOpen}
        onClose={() => setTaskModalOpen(false)}
      />

      <CalendarModal
        isOpen={eventModalOpen}
        onClose={() => setEventModalOpen(false)}
        date={new Date()}
        onCreated={() => setEventModalOpen(false)}
      />

      <Modal open={contactModalOpen} onClose={() => setContactModalOpen(false)} title="Новый контакт" maxWidth="max-w-md">
        <div className="p-6">
          <ContactForm
            initial={null}
            onSubmit={handleCreateContact}
            onCancel={() => setContactModalOpen(false)}
          />
        </div>
      </Modal>
    </div>
  )
}

export default Dashboard
