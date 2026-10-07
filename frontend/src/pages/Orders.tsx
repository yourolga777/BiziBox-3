import { useMemo, useState, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core'
import { Package, Plus, RefreshCw, Download, Upload } from 'lucide-react'
import Button from '../components/common/Button'
import Card from '../components/common/Card'
import { SkeletonList } from '../components/common/Skeleton'
import { orderApi } from '../api/client'
import {
  useContactsQuery,
} from '../hooks/queries'
import {
  useCreateOrderMutation,
  useOrdersQuery,
  useUpdateOrderMutation,
  useUpdateOrderStatusMutation,
  useDeleteOrderMutation,
  useAddOrderItemMutation,
  useUpdateOrderItemMutation,
  useRemoveOrderItemMutation,
  useAddOrderCommentMutation,
  useDeleteOrderCommentMutation,
} from '../hooks/orders'
import OrderForm from '../components/orders/OrderForm'
import OrderDetailModal from '../components/orders/OrderDetailModal'
import OrderImportModal from '../components/orders/OrderImportModal'
import {
  DroppableColumn,
  DragOverlayCard,
  KANBAN_STATUSES,
  isKanbanStatus,
} from '../components/orders/KanbanCards'
import { ORDER_STATUS_LABELS, type OrderStatus } from '../types/order'
import type { Order, OrderCreate, OrderItemInput, OrderItemUpdate, OrderUpdate } from '../types/order'
import { formatMoney } from '../utils/format'
import { useToast } from '../components/common/Toast'

function Orders() {
  const [searchParams] = useSearchParams()
  const [contactIdFilter] = useState<number | null>(() => {
    const cid = searchParams.get('contact_id')
    return cid ? parseInt(cid, 10) || null : null
  })
  const [showCreate, setShowCreate] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [activeOrder, setActiveOrder] = useState<Order | null>(null)
  const [exporting, setExporting] = useState(false)
  const justDroppedRef = useRef(false)
  const { showToast } = useToast()

  const ordersQuery = useOrdersQuery({ contact_id: contactIdFilter || undefined, limit: 200 })
  const contactsQuery = useContactsQuery()
  const createOrder = useCreateOrderMutation()
  const updateOrder = useUpdateOrderMutation()
  const updateStatus = useUpdateOrderStatusMutation()
  const deleteOrder = useDeleteOrderMutation()
  const addItem = useAddOrderItemMutation()
  const removeItem = useRemoveOrderItemMutation()
  const updateItem = useUpdateOrderItemMutation()
  const addComment = useAddOrderCommentMutation()
  const deleteComment = useDeleteOrderCommentMutation()

  const orders = ordersQuery.data ?? []
  const loading = ordersQuery.isLoading
  const error = ordersQuery.error

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  )

  const grouped = useMemo(() => {
    const map: Record<OrderStatus, Order[]> = {
      new: [],
      in_progress: [],
      shipped: [],
      completed: [],
      cancelled: [],
    }
    for (const order of orders) {
      if (map[order.status]) {
        map[order.status].push(order)
      } else {
        map.new.push(order)
      }
    }
    const byDelivery = (a: Order, b: Order) => {
      if (a.delivery_date && b.delivery_date) {
        const d = new Date(a.delivery_date).getTime() - new Date(b.delivery_date).getTime()
        if (d !== 0) return d
      } else if (a.delivery_date) {
        return -1
      } else if (b.delivery_date) {
        return 1
      }
      return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
    }
    for (const key of Object.keys(map) as OrderStatus[]) {
      map[key].sort(byDelivery)
    }
    return map
  }, [orders])

  const activeTotal = useMemo(
    () => orders
      .filter((o) => o.status !== 'cancelled')
      .reduce((sum, o) => sum + o.total, 0),
    [orders],
  )

  const handleDragStart = useCallback((event: DragStartEvent) => {
    const order = event.active.data.current?.order as Order | undefined
    if (order) {
      setActiveOrder(order)
      justDroppedRef.current = false
    }
  }, [])

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setActiveOrder(null)
      const { active, over } = event
      if (!over) {
        setTimeout(() => { justDroppedRef.current = false }, 0)
        return
      }

      const order = active.data.current?.order as Order | undefined
      if (!order) {
        setTimeout(() => { justDroppedRef.current = false }, 0)
        return
      }

      const targetStatus = String(over.id).replace('column-', '') as OrderStatus
      if (targetStatus === order.status || !isKanbanStatus(targetStatus)) {
        setTimeout(() => { justDroppedRef.current = false }, 0)
        return
      }

      justDroppedRef.current = true
      updateStatus.mutate(
        { id: order.id, status: targetStatus },
        { onSettled: () => { setTimeout(() => { justDroppedRef.current = false }, 100) } },
      )
    },
    [updateStatus],
  )

  const handleDragCancel = useCallback(() => {
    setActiveOrder(null)
    setTimeout(() => { justDroppedRef.current = false }, 0)
  }, [])

  const handleOrderClick = async (order: Order) => {
    if (justDroppedRef.current) return
    try {
      const detail = await orderApi.getById(order.id)
      setSelectedOrder(detail)
      setDetailOpen(true)
    } catch {
      // ignore error — modal won't open
    }
  }

  const handleCreate = async (data: OrderCreate) => {
    await createOrder.mutateAsync(data)
  }

  const handleUpdateOrder = async (order: Order, data: OrderUpdate) => {
    await updateOrder.mutateAsync({ id: order.id, data })
    try {
      const detail = await orderApi.getById(order.id)
      setSelectedOrder(detail)
    } catch {
      // ignore — query invalidation обновит список
    }
  }

  const handleStatusChange = async (order: Order, status: OrderStatus) => {
    await updateStatus.mutateAsync({ id: order.id, status })
    setSelectedOrder({ ...order, status })
  }

  const handleTogglePaid = async (order: Order) => {
    await updateOrder.mutateAsync({ id: order.id, data: { paid: !order.paid } })
    setSelectedOrder({ ...order, paid: !order.paid })
  }

  const handleAddItem = async (order: Order, data: OrderItemInput) => {
    await addItem.mutateAsync({ orderId: order.id, data })
    const detail = await orderApi.getById(order.id)
    setSelectedOrder(detail)
  }

  const handleRemoveItem = async (order: Order, itemId: number) => {
    await removeItem.mutateAsync({ orderId: order.id, itemId })
    const detail = await orderApi.getById(order.id)
    setSelectedOrder(detail)
  }

  const handleUpdateItem = async (order: Order, itemId: number, data: OrderItemUpdate) => {
    await updateItem.mutateAsync({ orderId: order.id, itemId, data })
    const detail = await orderApi.getById(order.id)
    setSelectedOrder(detail)
  }

  const handleAddComment = async (orderId: number, content: string) => {
    const comment = await addComment.mutateAsync({ orderId, content })
    setSelectedOrder((prev) => prev ? { ...prev, comments: [...prev.comments, comment] } : prev)
    return comment
  }

  const handleDeleteComment = async (orderId: number, commentId: number) => {
    await deleteComment.mutateAsync({ orderId, commentId })
    setSelectedOrder((prev) => prev ? { ...prev, comments: prev.comments.filter(c => c.id !== commentId) } : prev)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Переместить заказ в архив?')) return
    await deleteOrder.mutateAsync(id)
    setDetailOpen(false)
    setSelectedOrder(null)
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      const csv = await orderApi.exportCsv()
      const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'orders.csv'
      a.click()
      URL.revokeObjectURL(url)
      showToast('Файл выгружен', 'success')
    } catch {
      showToast('Не удалось выгрузить файл', 'error')
    } finally {
      setExporting(false)
    }
  }

  const handleImport = async (file: File) => {
    const result = await orderApi.importCsv(file)
    ordersQuery.refetch()
    showToast(`Импортировано: ${result.created} создано, ${result.skipped} пропущено`, result.errors.length ? 'error' : 'success')
    return result
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Package className="w-6 h-6 text-primary" />
          <h2 className="text-2xl font-semibold text-gray-900">Заказы</h2>
        </div>
        <SkeletonList count={4} />
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold text-gray-900">Заказы</h2>
        <Card>
          <div className="text-center py-8">
            <p className="text-red-500 mb-4">{error instanceof Error ? error.message : 'Ошибка загрузки'}</p>
            <Button onClick={() => ordersQuery.refetch()}>Повторить</Button>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-4 h-[calc(100vh-4rem)] flex flex-col">
      <div className="flex items-center justify-between flex-wrap gap-3 shrink-0">
        <div className="flex items-center gap-3">
          <Package className="w-6 h-6 text-primary" />
          <h2 className="text-2xl font-semibold text-gray-900">Заказы</h2>
          <span className="text-sm text-gray-400">{orders.length} заказов</span>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => ordersQuery.refetch()}>
            <RefreshCw className="w-4 h-4 mr-1" />
            Обновить
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setShowImport(true)}>
            <Upload className="w-4 h-4 mr-1" />
            Импорт
          </Button>
          <Button variant="ghost" size="sm" onClick={handleExport} disabled={exporting}>
            <Download className="w-4 h-4 mr-1" />
            {exporting ? 'Выгрузка...' : 'Экспорт'}
          </Button>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="w-4 h-4 mr-1" />
            Создать
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-3 md:grid-cols-5 gap-3 shrink-0">
        <div className="bg-white border rounded-xl p-3"><p className="text-xs text-gray-500">Всего</p><p className="text-xl font-bold">{orders.length}</p></div>
        <div className="bg-white border rounded-xl p-3"><p className="text-xs text-gray-500">Новых</p><p className="text-xl font-bold text-blue-600">{grouped.new.length}</p></div>
        <div className="bg-white border rounded-xl p-3"><p className="text-xs text-gray-500">В работе</p><p className="text-xl font-bold text-amber-600">{grouped.in_progress.length}</p></div>
        <div className="bg-white border rounded-xl p-3"><p className="text-xs text-gray-500">Отправлено</p><p className="text-xl font-bold text-violet-600">{grouped.shipped.length}</p></div>
        <div className="bg-white border rounded-xl p-3"><p className="text-xs text-gray-500">Сумма активных</p><p className="text-lg font-bold text-green-600">{formatMoney(activeTotal)}</p></div>
      </div>

      <DndContext
        sensors={sensors}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onDragCancel={handleDragCancel}
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 flex-1 min-h-0">
          {KANBAN_STATUSES.map(({ status, dot }) => (
            <DroppableColumn
              key={status}
              status={status}
              label={ORDER_STATUS_LABELS[status]}
              dot={dot}
              orders={grouped[status]}
              isLoading={loading}
              onOrderClick={handleOrderClick}
            />
          ))}
        </div>
        <DragOverlay>
          {activeOrder ? <DragOverlayCard order={activeOrder} /> : null}
        </DragOverlay>
      </DndContext>

      <OrderForm
        open={showCreate}
        onClose={() => setShowCreate(false)}
        contacts={contactsQuery.data ?? []}
        onCreate={handleCreate}
      />

      <OrderImportModal
        open={showImport}
        onClose={() => setShowImport(false)}
        onImport={handleImport}
      />

      <OrderDetailModal
        open={detailOpen}
        onClose={() => { setDetailOpen(false); setSelectedOrder(null) }}
        order={selectedOrder}
        onUpdateOrder={handleUpdateOrder}
        onStatusChange={handleStatusChange}
        onTogglePaid={handleTogglePaid}
        onAddItem={handleAddItem}
        onRemoveItem={handleRemoveItem}
        onUpdateItem={handleUpdateItem}
        onAddComment={handleAddComment}
        onDeleteComment={handleDeleteComment}
        onDelete={handleDelete}
      />
    </div>
  )
}

export default Orders