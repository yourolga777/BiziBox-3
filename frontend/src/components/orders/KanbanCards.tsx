import { useDroppable, useDraggable } from '@dnd-kit/core'
import { GripVertical, Package } from 'lucide-react'
import MessagePreview from '../common/MessagePreview'
import { ORDER_KANBAN_STATUSES, type Order, type OrderStatus } from '../../types/order'
import { formatDate, formatDateTime, formatMoney } from '../../utils/format'
import { formatRelativeTime } from '../../utils/format'

export const KANBAN_STATUSES: { status: OrderStatus; color: string; dot: string }[] = [
  { status: 'new', color: 'bg-blue-50', dot: 'bg-blue-500' },
  { status: 'in_progress', color: 'bg-amber-50', dot: 'bg-amber-500' },
  { status: 'shipped', color: 'bg-violet-50', dot: 'bg-violet-500' },
  { status: 'completed', color: 'bg-green-50', dot: 'bg-green-500' },
  { status: 'cancelled', color: 'bg-red-50', dot: 'bg-red-500' },
]

interface ColumnProps {
  status: OrderStatus
  label: string
  dot: string
  orders: Order[]
  isLoading: boolean
  onOrderClick: (order: Order) => void
  dragHandle?: React.ReactNode
}

export function DroppableColumn({ status, label, dot, orders, isLoading, onOrderClick, dragHandle }: ColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: `column-${status}` })

  return (
    <div
      ref={setNodeRef}
      className={`flex flex-col rounded-xl border min-h-[300px] transition-colors duration-150 ${
        isOver ? 'border-primary bg-primary/5' : 'border-gray-200 bg-gray-50/50'
      }`}
    >
      <div className="px-3 pt-3">
        <div className="flex items-center justify-between mb-3 px-0.5">
          <div className="flex items-center gap-2">
            {dragHandle}
            <span className={`w-2.5 h-2.5 rounded-full ${dot}`} />
            <h4 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">{label}</h4>
          </div>
          <span className="text-xs font-bold text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
            {orders.length}
          </span>
        </div>
      </div>
      <div className="flex-1 px-3 pb-3 space-y-2 overflow-y-auto max-h-[calc(100vh-22rem)]">
        {isLoading ? (
          <div className="space-y-2 animate-pulse">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-lg" />
            ))}
          </div>
        ) : orders.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-xs text-gray-400">Нет заказов</div>
        ) : (
          orders.map((order) => (
            <DraggableOrderCard key={order.id} order={order} onClick={onOrderClick} />
          ))
        )}
      </div>
    </div>
  )
}

interface DraggableOrderCardProps {
  order: Order
  onClick: (order: Order) => void
}

export function DraggableOrderCard({ order, onClick }: DraggableOrderCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `order-${order.id}`,
    data: { order },
  })

  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`, zIndex: 50 }
    : undefined

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      role="button"
      tabIndex={0}
      onClick={() => {
        if (isDragging) return
        onClick(order)
      }}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick(order)
        }
      }}
      className={`block bg-white rounded-lg border border-gray-200 p-3 shadow-sm transition-all duration-150 cursor-grab active:cursor-grabbing
        ${isDragging ? 'opacity-50 shadow-lg ring-2 ring-primary/30' : 'hover:shadow-md hover:border-gray-300'}
      `}
    >
      <div className="flex items-start gap-2">
        <GripVertical size={14} className="mt-0.5 text-gray-300" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-semibold text-gray-900 truncate">{order.order_number || `Заказ #${order.id}`}</p>
            <span className="text-sm font-bold text-gray-800 shrink-0">{formatMoney(order.total)}</span>
          </div>
          <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
            <span className="truncate">{order.contact_name || `Контакт #${order.contact_id}`}</span>
          </div>
          {order.message_id != null && (
            <MessagePreview messageId={order.message_id} className="text-[10px] text-gray-400 mt-1 line-clamp-2 italic" />
          )}
          <div className="flex items-center gap-1.5 mt-2 flex-wrap">
            {order.items.length > 0 && (
              <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">
                <Package size={10} />
                {order.items.reduce((sum, i) => sum + i.quantity, 0)} поз.
              </span>
            )}
            {order.delivery_date && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600" title="Дата доставки">
                Доставка: {formatDate(order.delivery_date)}
              </span>
            )}
            {order.paid ? (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-100 text-green-600">Оплачен</span>
            ) : (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-600">Не оплачен</span>
            )}
            {order.created_at && (
              <span className="text-[10px] text-gray-400" title={formatDateTime(order.created_at)}>
                {formatRelativeTime(order.created_at, true)}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export function DragOverlayCard({ order }: { order: Order }) {
  return (
    <div className="bg-white rounded-lg border-2 border-primary border-dashed p-3 shadow-xl">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <GripVertical size={14} className="mt-0.5 text-gray-300" />
          <p className="text-sm font-semibold text-gray-900 truncate">
            {order.order_number || `Заказ #${order.id}`}
          </p>
        </div>
        <span className="text-sm font-bold text-gray-800 shrink-0">{formatMoney(order.total)}</span>
      </div>
    </div>
  )
}

export function isKanbanStatus(status: string): status is OrderStatus {
  return (ORDER_KANBAN_STATUSES as string[]).includes(status)
}