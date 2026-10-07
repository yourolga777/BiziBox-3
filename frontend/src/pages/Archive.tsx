import { useState, useEffect, useCallback } from 'react'
import { ArchiveRestore, Trash2, Mail, MessageCircle, ListTodo, Package } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import Card from '../components/common/Card'
import { contactApi, messageApi, orderApi, productApi } from '../api/client'
import { taskApi } from '../api/tasks'
import type { Contact } from '../types/contact'
import type { Message } from '../types/message'
import type { Task } from '../types/task'
import type { Order } from '../types/order'
import type { Product } from '../types/product'
import { formatMoney } from '../utils/format'

type Tab = 'contacts' | 'messages' | 'tasks' | 'orders' | 'products'

const PAGE_SIZE = 20

const tabs: { key: Tab; label: string }[] = [
  { key: 'contacts', label: 'Контакты' },
  { key: 'messages', label: 'Сообщения' },
  { key: 'tasks', label: 'Задачи' },
  { key: 'orders', label: 'Заказы' },
  { key: 'products', label: 'Товары' },
]

function Archive() {
  const [activeTab, setActiveTab] = useState<Tab>('contacts')
  const queryClient = useQueryClient()

  const [contacts, setContacts] = useState<Contact[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)

  const loadContacts = useCallback(async () => {
    try {
      const data = await contactApi.getArchived({ limit: PAGE_SIZE })
      setContacts(data)
    } catch { /* empty */ }
  }, [])

  const loadMessages = useCallback(async () => {
    try {
      const data = await messageApi.getArchived({ limit: PAGE_SIZE })
      setMessages(data)
    } catch { /* empty */ }
  }, [])

  const loadTasks = useCallback(async () => {
    try {
      const data = await taskApi.getArchived({ limit: PAGE_SIZE })
      setTasks(data)
    } catch { /* empty */ }
  }, [])

  const loadOrders = useCallback(async () => {
    try {
      const data = await orderApi.getArchived({ limit: PAGE_SIZE })
      setOrders(data)
    } catch { /* empty */ }
  }, [])

  const loadProducts = useCallback(async () => {
    try {
      const data = await productApi.getArchived({ limit: PAGE_SIZE })
      setProducts(data)
    } catch { /* empty */ }
  }, [])

  useEffect(() => {
    setLoading(true)
    const load = activeTab === 'contacts' ? loadContacts
      : activeTab === 'messages' ? loadMessages
      : activeTab === 'tasks' ? loadTasks
      : activeTab === 'orders' ? loadOrders
      : loadProducts
    load().finally(() => setLoading(false))
  }, [activeTab, loadContacts, loadMessages, loadTasks, loadOrders, loadProducts])

  const handleRestoreContact = async (id: number) => {
    try {
      await contactApi.restore(id)
      setContacts(prev => prev.filter(c => c.id !== id))
    } catch { /* empty */ }
  }

  const handleDeleteContact = async (id: number) => {
    if (!confirm('Удалить контакт навсегда?')) return
    try {
      await contactApi.bulkDelete([id])
      setContacts(prev => prev.filter(c => c.id !== id))
    } catch { /* empty */ }
  }

  const handleRestoreMessage = async (id: number) => {
    try {
      await messageApi.bulkRestore([id])
      setMessages(prev => prev.filter(m => m.id !== id))
      queryClient.invalidateQueries({ queryKey: ['threads'] })
    } catch { /* empty */ }
  }

  const handleDeleteMessage = async (id: number) => {
    if (!confirm('Удалить сообщение навсегда?')) return
    try {
      await messageApi.bulkDelete([id])
      setMessages(prev => prev.filter(m => m.id !== id))
      queryClient.invalidateQueries({ queryKey: ['threads'] })
    } catch { /* empty */ }
  }

  const handleRestoreTask = async (id: number) => {
    try {
      await taskApi.restore(id)
      setTasks(prev => prev.filter(t => t.id !== id))
    } catch { /* empty */ }
  }

  const handleDeleteTask = async (id: number) => {
    if (!confirm('Удалить задачу навсегда?')) return
    try {
      await taskApi.bulkDelete([id])
      setTasks(prev => prev.filter(t => t.id !== id))
    } catch { /* empty */ }
  }

  const handleRestoreOrder = async (id: number) => {
    try {
      await orderApi.restore(id)
      setOrders(prev => prev.filter(o => o.id !== id))
    } catch { /* empty */ }
  }

  const handleRestoreProduct = async (id: number) => {
    try {
      await productApi.restore(id)
      setProducts(prev => prev.filter(p => p.id !== id))
    } catch { /* empty */ }
  }

  const handleDeleteProduct = async (id: number) => {
    if (!confirm('Удалить товар навсегда? Записи о нём в заказах будут очищены.')) return
    try {
      await productApi.permanentDelete(id)
      setProducts(prev => prev.filter(p => p.id !== id))
    } catch { /* empty */ }
  }

  const renderEmpty = (label: string) => (
    <div className="p-8 text-center text-gray-400">В архиве нет {label}</div>
  )

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold text-gray-900">Архив</h2>

      <div className="flex gap-1 border-b border-gray-200">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <Card>
        {loading ? (
          <div className="p-8 text-center text-gray-400">Загрузка...</div>
        ) : activeTab === 'contacts' && contacts.length === 0 ? renderEmpty('контактов')
        : activeTab === 'messages' && messages.length === 0 ? renderEmpty('сообщений')
        : activeTab === 'tasks' && tasks.length === 0 ? renderEmpty('задач')
        : activeTab === 'orders' && orders.length === 0 ? renderEmpty('заказов')
        : activeTab === 'products' && products.length === 0 ? renderEmpty('товаров')
        : activeTab === 'contacts' ? (
          <div className="divide-y divide-gray-100">
            {contacts.map(c => (
              <div key={c.id} className="flex items-center justify-between p-4">
                <div>
                  <p className="font-medium text-gray-900">{c.name || 'Без имени'}</p>
                  <p className="text-sm text-gray-500">
                    {c.phone && `${c.phone} `}
                    {c.email && `· ${c.email}`}
                    {c.telegram_username && `· @${c.telegram_username}`}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleRestoreContact(c.id)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100"
                  >
                    <ArchiveRestore className="w-4 h-4" />
                    Восстановить
                  </button>
                  <button
                    onClick={() => handleDeleteContact(c.id)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100"
                  >
                    <Trash2 className="w-4 h-4" />
                    Удалить
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : activeTab === 'messages' ? (
          <div className="divide-y divide-gray-100">
            {messages.map(m => (
              <div key={m.id} className="flex items-center justify-between p-4">
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-gray-900 truncate">{m.content}</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {m.channel === 'telegram' && <MessageCircle className="w-3 h-3 inline mr-1" />}
                    {m.channel === 'email' && <Mail className="w-3 h-3 inline mr-1" />}
                    {m.channel === 'vk' && <MessageCircle className="w-3 h-3 inline mr-1" />}
                    {m.channel} · {m.created_at ? new Date(m.created_at).toLocaleString() : ''}
                  </p>
                </div>
                <div className="flex gap-2 shrink-0 ml-4">
                  <button
                    onClick={() => handleRestoreMessage(m.id)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100"
                  >
                    <ArchiveRestore className="w-4 h-4" />
                    Восстановить
                  </button>
                  <button
                    onClick={() => handleDeleteMessage(m.id)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100"
                  >
                    <Trash2 className="w-4 h-4" />
                    Удалить
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : activeTab === 'tasks' ? (
          <div className="divide-y divide-gray-100">
            {tasks.map(t => (
              <div key={t.id} className="flex items-center justify-between p-4">
                <div>
                  <p className="font-medium text-gray-900">{t.title || `Задача #${t.id}`}</p>
                  <p className="text-sm text-gray-500">
                    <ListTodo className="w-3 h-3 inline mr-1" />
                    {t.description ? `${t.description.slice(0, 60)}${t.description.length > 60 ? '...' : ''}` : 'Нет описания'}
                    {t.due_date && ` · ${new Date(t.due_date).toLocaleDateString()}`}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleRestoreTask(t.id)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100"
                  >
                    <ArchiveRestore className="w-4 h-4" />
                    Восстановить
                  </button>
                  <button
                    onClick={() => handleDeleteTask(t.id)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100"
                  >
                    <Trash2 className="w-4 h-4" />
                    Удалить
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : activeTab === 'orders' ? (
          <div className="divide-y divide-gray-100">
            {orders.map(o => (
              <div key={o.id} className="flex items-center justify-between p-4">
                <div className="min-w-0">
                  <p className="font-medium text-gray-900">{o.order_number || `Заказ #${o.id}`}</p>
                  <p className="text-sm text-gray-500">
                    {o.contact_name || `Контакт #${o.contact_id}`} · {formatMoney(o.total)}
                  </p>
                </div>
                <div className="flex gap-2 shrink-0 ml-4">
                  <button
                    onClick={() => handleRestoreOrder(o.id)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100"
                  >
                    <ArchiveRestore className="w-4 h-4" />
                    Восстановить
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {products.map(p => (
              <div key={p.id} className="flex items-center justify-between p-4">
                <div className="min-w-0">
                  <p className="font-medium text-gray-900">{p.name || `Товар #${p.id}`}</p>
                  <p className="text-sm text-gray-500">
                    <Package className="w-3 h-3 inline mr-1" />
                    {p.sku && `${p.sku} · `}{formatMoney(p.price)}
                  </p>
                </div>
                <div className="flex gap-2 shrink-0 ml-4">
                  <button
                    onClick={() => handleRestoreProduct(p.id)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100"
                  >
                    <ArchiveRestore className="w-4 h-4" />
                    Восстановить
                  </button>
                  <button
                    onClick={() => handleDeleteProduct(p.id)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100"
                  >
                    <Trash2 className="w-4 h-4" />
                    Удалить
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}

export default Archive
