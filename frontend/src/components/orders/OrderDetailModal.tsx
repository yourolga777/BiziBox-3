import { useState, useEffect } from 'react'
import { CircleDollarSign, MapPin, Plus, Trash2, X } from 'lucide-react'
import Modal from '../common/Modal'
import Button from '../common/Button'
import MessagePreview from '../common/MessagePreview'
import { ORDER_STATUS_LABELS, type OrderStatus } from '../../types/order'
import type { Order, OrderComment, OrderItemInput, OrderItemUpdate, OrderUpdate } from '../../types/order'
import { formatDateTime, formatMoney } from '../../utils/format'
import { formatRelativeTime } from '../../utils/format'

const PAYMENT_OPTIONS = [
  { value: '', label: 'Не указан' },
  { value: 'card', label: 'Карта' },
  { value: 'cash', label: 'Наличные' },
  { value: 'sbp', label: 'СБП' },
  { value: 'transfer', label: 'Перевод' },
]

interface OrderDetailModalProps {
  open: boolean
  onClose: () => void
  order: Order | null
  onUpdateOrder: (order: Order, data: OrderUpdate) => Promise<void>
  onStatusChange: (order: Order, status: OrderStatus) => void
  onTogglePaid: (order: Order) => void
  onAddItem: (order: Order, data: OrderItemInput) => Promise<void>
  onRemoveItem: (order: Order, itemId: number) => Promise<void>
  onUpdateItem: (order: Order, itemId: number, data: OrderItemUpdate) => Promise<void>
  onAddComment: (orderId: number, content: string) => Promise<OrderComment>
  onDeleteComment: (orderId: number, commentId: number) => Promise<void>
  onDelete?: (id: number) => void
}

const STATUS_META: Record<OrderStatus, { color: string }> = {
  new: { color: 'bg-blue-100 text-blue-700' },
  in_progress: { color: 'bg-amber-100 text-amber-700' },
  shipped: { color: 'bg-violet-100 text-violet-700' },
  completed: { color: 'bg-green-100 text-green-700' },
  cancelled: { color: 'bg-red-100 text-red-700' },
}

function OrderDetailModal({
  open,
  onClose,
  order,
  onUpdateOrder,
  onStatusChange,
  onTogglePaid,
  onAddItem,
  onRemoveItem,
  onUpdateItem,
  onAddComment,
  onDeleteComment,
  onDelete,
}: OrderDetailModalProps) {
  const [commentText, setCommentText] = useState('')
  const [addingComment, setAddingComment] = useState(false)
  const [editAddress, setEditAddress] = useState('')
  const [editPaymentMethod, setEditPaymentMethod] = useState('')
  const [editDeliveryDate, setEditDeliveryDate] = useState('')
  const [savingFields, setSavingFields] = useState(false)
  const [newItemName, setNewItemName] = useState('')
  const [newItemQty, setNewItemQty] = useState('1')
  const [newItemPrice, setNewItemPrice] = useState('')
  const [addingItem, setAddingItem] = useState(false)
  const [itemDrafts, setItemDrafts] = useState<Record<number, { quantity: string; price: string }>>({})

  useEffect(() => {
    if (order) {
      setCommentText('')
      setEditAddress(order.delivery_address ?? '')
      setEditPaymentMethod(order.payment_method ?? '')
      setEditDeliveryDate(order.delivery_date ?? '')
      setNewItemName('')
      setNewItemQty('1')
      setNewItemPrice('')
      const drafts: Record<number, { quantity: string; price: string }> = {}
      for (const item of order.items) {
        drafts[item.id] = { quantity: String(item.quantity), price: String(item.price) }
      }
      setItemDrafts(drafts)
    }
  }, [order])

  if (!order) return null

  const status = STATUS_META[order.status] || STATUS_META.new

  const handleAddComment = async () => {
    if (!commentText.trim() || addingComment) return
    setAddingComment(true)
    try {
      await onAddComment(order.id, commentText.trim())
      setCommentText('')
    } finally {
      setAddingComment(false)
    }
  }

  const handleAddItem = async () => {
    if (!newItemName.trim() || addingItem) return
    setAddingItem(true)
    try {
      await onAddItem(order, {
        name: newItemName.trim(),
        quantity: Number(newItemQty) || 1,
        price: Number(newItemPrice) || 0,
      })
      setNewItemName('')
      setNewItemQty('1')
      setNewItemPrice('')
    } finally {
      setAddingItem(false)
    }
  }

  const handleSaveFields = async () => {
    if (savingFields) return
    setSavingFields(true)
    try {
      await onUpdateOrder(order, {
        delivery_address: editAddress || null,
        payment_method: editPaymentMethod || null,
        delivery_date: editDeliveryDate || null,
      })
    } finally {
      setSavingFields(false)
    }
  }

  const handleDraftChange = (itemId: number, patch: Partial<{ quantity: string; price: string }>) => {
    setItemDrafts((prev) => ({ ...prev, [itemId]: { ...prev[itemId], ...patch } }))
  }

  const commitItem = async (itemId: number) => {
    const draft = itemDrafts[itemId]
    const item = order.items.find((i) => i.id === itemId)
    if (!draft || !item) return
    const quantity = Number(draft.quantity) || 0
    const price = Number(draft.price) || 0
    if (quantity === item.quantity && price === item.price) return
    try {
      await onUpdateItem(order, itemId, { quantity, price })
    } catch {
      setItemDrafts((prev) => ({ ...prev, [itemId]: { quantity: String(item.quantity), price: String(item.price) } }))
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={order.order_number || `Заказ #${order.id}`} maxWidth="max-w-2xl">
      <div className="p-6 space-y-6">
        <div className="flex items-center gap-3 flex-wrap">
          <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${status.color}`}>
            {ORDER_STATUS_LABELS[order.status]}
          </span>
          <select
            value={order.status}
            onChange={(e) => onStatusChange(order, e.target.value as OrderStatus)}
            className="text-xs border border-gray-200 rounded-lg px-2 py-1 outline-none focus:border-primary"
            aria-label="Статус заказа"
          >
            {Object.entries(ORDER_STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <span className="text-sm font-bold text-gray-800">{formatMoney(order.total)}</span>
          <button
            type="button"
            onClick={() => onTogglePaid(order)}
            className={`inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full transition-colors ${
              order.paid
                ? 'bg-green-100 text-green-700 hover:bg-green-200'
                : 'bg-amber-100 text-amber-700 hover:bg-amber-200'
            }`}
            title={order.paid ? 'Отметить неоплаченным' : 'Отметить оплаченным'}
          >
            <CircleDollarSign className="w-3.5 h-3.5" />
            {order.paid ? 'Оплачен' : 'Не оплачен'}
          </button>
        </div>

        <div className="text-sm text-gray-600 space-y-1">
          <p>
            <span className="text-gray-500">Заказчик:</span>{' '}
            <span className="font-medium">{order.contact_name || `Контакт #${order.contact_id}`}</span>
          </p>
          {order.created_at && (
            <p>
              <span className="text-gray-500">Создан:</span>{' '}
              <span title={formatRelativeTime(order.created_at)}>{formatDateTime(order.created_at)}</span>
            </p>
          )}
          {order.message_id != null && (
            <MessagePreview messageId={order.message_id} className="text-xs text-gray-500 italic mt-1 line-clamp-3" />
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label htmlFor="order-detail-address" className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5" />
              Адрес доставки
            </label>
            <input
              id="order-detail-address"
              type="text"
              value={editAddress}
              onChange={(e) => setEditAddress(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              placeholder="Адрес"
            />
          </div>
          <div>
            <label htmlFor="order-detail-payment" className="block text-xs font-medium text-gray-500 mb-1">Способ оплаты</label>
            <select
              id="order-detail-payment"
              value={editPaymentMethod}
              onChange={(e) => setEditPaymentMethod(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary bg-white"
            >
              {PAYMENT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="order-detail-delivery-date" className="block text-xs font-medium text-gray-500 mb-1">Дата доставки</label>
            <input
              id="order-detail-delivery-date"
              type="date"
              value={editDeliveryDate}
              onChange={(e) => setEditDeliveryDate(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>
        <div className="flex justify-end">
          <Button size="sm" onClick={handleSaveFields} disabled={savingFields}>
            {savingFields ? 'Сохранение...' : 'Сохранить'}
          </Button>
        </div>

        <div className="border-t pt-4">
          <h4 className="text-sm font-medium text-gray-700 mb-3">Позиции</h4>
          {order.items.length === 0 ? (
            <p className="text-sm text-gray-400">Нет позиций</p>
          ) : (
            <div className="space-y-2 mb-3">
              {order.items.map((item) => {
                const draft = itemDrafts[item.id]
                const qty = draft ? Number(draft.quantity) || 0 : item.quantity
                const price = draft ? Number(draft.price) || 0 : item.price
                return (
                  <div key={item.id} className="bg-gray-50 rounded-xl px-3 py-2 flex items-center gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-700 truncate">{item.name}</p>
                    </div>
                    <input
                      type="number"
                      min={0}
                      step="any"
                      value={draft?.quantity ?? item.quantity}
                      onChange={(e) => handleDraftChange(item.id, { quantity: e.target.value })}
                      onBlur={() => commitItem(item.id)}
                      onKeyDown={(e) => { if (e.key === 'Enter') commitItem(item.id) }}
                      className="w-16 px-2 py-1 rounded-lg border border-gray-200 text-sm outline-none focus:border-primary"
                      aria-label={`Количество: ${item.name}`}
                    />
                    <span className="text-xs text-gray-400">×</span>
                    <input
                      type="number"
                      min={0}
                      step="any"
                      value={draft?.price ?? item.price}
                      onChange={(e) => handleDraftChange(item.id, { price: e.target.value })}
                      onBlur={() => commitItem(item.id)}
                      onKeyDown={(e) => { if (e.key === 'Enter') commitItem(item.id) }}
                      className="w-24 px-2 py-1 rounded-lg border border-gray-200 text-sm outline-none focus:border-primary"
                      aria-label={`Цена: ${item.name}`}
                    />
                    <span className="text-sm font-semibold text-gray-700 shrink-0 w-20 text-right">{formatMoney(qty * price)}</span>
                    <button
                      onClick={() => onRemoveItem(order, item.id)}
                      className="shrink-0 p-1 text-gray-300 hover:text-red-500 transition-colors"
                      title="Удалить позицию"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )
              })}
            </div>
          )}
          <div className="flex justify-end mb-3">
            <span className="text-sm text-gray-600">
              Итого: <span className="font-bold text-gray-900">{formatMoney(order.total)}</span>
            </span>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={newItemName}
              onChange={(e) => setNewItemName(e.target.value)}
              placeholder="Название товара"
              className="flex-1 px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
            <input
              type="number"
              min={0}
              step="any"
              value={newItemQty}
              onChange={(e) => setNewItemQty(e.target.value)}
              placeholder="Кол-во"
              className="w-20 px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
            <input
              type="number"
              min={0}
              step="any"
              value={newItemPrice}
              onChange={(e) => setNewItemPrice(e.target.value)}
              placeholder="Цена"
              className="w-24 px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
            <Button onClick={handleAddItem} disabled={addingItem || !newItemName.trim()} size="sm">
              <Plus className="w-4 h-4 mr-1" />
              Добавить
            </Button>
          </div>
        </div>

        <div className="border-t pt-4">
          <h4 className="text-sm font-medium text-gray-700 mb-3">Комментарии</h4>
          {order.comments.length === 0 ? (
            <p className="text-sm text-gray-400">Нет комментариев</p>
          ) : (
            <div className="space-y-2 mb-4">
              {order.comments.map((comment) => (
                <div key={comment.id} className="bg-gray-50 rounded-xl p-3 flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">{comment.content}</p>
                    <p className="text-xs text-gray-400 mt-1">{formatRelativeTime(comment.created_at)}</p>
                  </div>
                  <button
                    onClick={() => onDeleteComment(order.id, comment.id)}
                    className="shrink-0 p-1 text-gray-300 hover:text-red-500 transition-colors"
                    title="Удалить комментарий"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <input
              type="text"
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleAddComment() }}
              placeholder="Добавить комментарий..."
              className="flex-1 px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
            <Button onClick={handleAddComment} disabled={addingComment || !commentText.trim()} size="sm">
              <Plus className="w-4 h-4 mr-1" />
              {addingComment ? '...' : 'Добавить'}
            </Button>
          </div>
        </div>

        <div className="flex justify-between items-center">
          {onDelete ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(order.id)}
              className="text-red-600 hover:text-red-700 hover:bg-red-50"
            >
              <Trash2 className="w-4 h-4 mr-1" />
              В архив
            </Button>
          ) : (
            <div />
          )}
          <div className="flex gap-2">
            <Button variant="ghost" onClick={onClose}>Закрыть</Button>
          </div>
        </div>
      </div>
    </Modal>
  )
}

export default OrderDetailModal