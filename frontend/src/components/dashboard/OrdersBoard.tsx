import { useMemo } from 'react'
import { AlertCircle, CircleDollarSign, LinkIcon, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'
import Card from '../common/Card'
import { useOrdersQuery } from '../../hooks/orders'
import { ORDER_STATUS_LABELS, type Order, type OrderStatus } from '../../types/order'
import { formatMoney } from '../../utils/format'

const DASHBOARD_STATUSES: { status: OrderStatus; label: string; color: string; dot: string }[] = [
  { status: 'new', label: ORDER_STATUS_LABELS.new, color: 'text-blue-600', dot: 'bg-blue-500' },
  { status: 'in_progress', label: ORDER_STATUS_LABELS.in_progress, color: 'text-amber-600', dot: 'bg-amber-500' },
  { status: 'shipped', label: ORDER_STATUS_LABELS.shipped, color: 'text-violet-600', dot: 'bg-violet-500' },
  { status: 'completed', label: ORDER_STATUS_LABELS.completed, color: 'text-green-600', dot: 'bg-green-500' },
  { status: 'cancelled', label: ORDER_STATUS_LABELS.cancelled, color: 'text-red-600', dot: 'bg-red-500' },
]

const MAX_CARDS = 4

function OrderCard({ order }: { order: Order }) {
  return (
    <div className="flex items-start gap-2 bg-white rounded-lg border border-gray-200 p-2.5 shadow-sm">
      <LinkIcon className="mt-0.5 shrink-0 text-gray-300" size={16} />
      <Link to="/orders" className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-gray-900 truncate">{order.order_number || `Заказ #${order.id}`}</p>
        <div className="flex items-center gap-2 mt-1 text-xs text-gray-400">
          <span className="truncate">{order.contact_name || `Контакт #${order.contact_id}`}</span>
          <span className={`inline-flex items-center gap-0.5 shrink-0 font-medium ${order.paid ? 'text-green-600' : 'text-amber-600'}`}>
            <CircleDollarSign size={12} />
            {formatMoney(order.total)}
          </span>
        </div>
      </Link>
    </div>
  )
}

function StatusColumn({ status, label, color, dot, orders, isLoading }: {
  status: OrderStatus
  label: string
  color: string
  dot: string
  orders: Order[]
  isLoading: boolean
}) {
  const visible = orders.slice(0, MAX_CARDS)
  const hasMore = orders.length > MAX_CARDS

  return (
    <div className="flex flex-col rounded-xl border border-gray-200 bg-gray-50/50 min-h-[140px]">
      <div className="px-2.5 pt-2.5">
        <div className="flex items-center justify-between mb-2 px-0.5">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${dot}`} />
            <h4 className={`text-sm font-semibold uppercase tracking-wide ${color}`}>{label}</h4>
          </div>
          <span className="text-xs font-bold text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
            {orders.length}
          </span>
        </div>
      </div>
      <div className="flex-1 px-2.5 pb-2.5 space-y-2 overflow-y-auto max-h-[280px]">
        {isLoading ? (
          <div className="space-y-2 animate-pulse">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-14 bg-gray-200 rounded-lg" />
            ))}
          </div>
        ) : visible.length === 0 ? (
          <div className="flex items-center justify-center h-20 text-xs text-gray-400">Нет заказов</div>
        ) : (
          visible.map((order) => <OrderCard key={order.id} order={order} />)
        )}
      </div>
      {hasMore && (
        <div className="px-2.5 pb-2.5">
          <Link to={`/orders?status=${status}`} className="text-xs text-primary hover:underline">
            Все →
          </Link>
        </div>
      )}
    </div>
  )
}

function OrdersBoard() {
  const { data: orders, isLoading, isError, error, refetch } = useOrdersQuery({ limit: 100 })

  const grouped = useMemo(() => {
    const all = orders ?? []
    const map: Record<OrderStatus, Order[]> = {
      new: [],
      in_progress: [],
      shipped: [],
      completed: [],
      cancelled: [],
    }
    for (const order of all) {
      if (map[order.status]) map[order.status].push(order)
    }
    return map
  }, [orders])

  if (isError) {
    return (
      <Card title="Заказы">
        <div className="flex flex-col items-center gap-3 py-6 text-center">
          <AlertCircle className="text-red-500" size={32} />
          <p className="text-gray-600">{error instanceof Error ? error.message : 'Ошибка загрузки заказов'}</p>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 text-sm text-primary hover:underline"
          >
            <RefreshCw size={14} />
            Повторить
          </button>
        </div>
      </Card>
    )
  }

  return (
    <Card title="Заказы">
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        {DASHBOARD_STATUSES.map((s) => (
          <StatusColumn
            key={s.status}
            status={s.status}
            label={s.label}
            color={s.color}
            dot={s.dot}
            orders={grouped[s.status]}
            isLoading={isLoading}
          />
        ))}
      </div>
      <div className="text-right mt-2">
        <Link to="/orders" className="text-xs text-primary hover:underline">
          Все заказы →
        </Link>
      </div>
    </Card>
  )
}

export default OrdersBoard