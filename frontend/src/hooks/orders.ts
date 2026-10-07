import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { orderApi, isOfflineError, requestOptimistic } from '../api/client'
import { saveOrders, getOrdersFromCache, getOrderFromCache } from '../offline/db'
import { enqueueOptimistic } from '../offline/optimistic'
import type { Order, OrderCreate, OrderItemInput, OrderItemUpdate, OrderStatus, OrderUpdate } from '../types/order'

export function useOrdersQuery(params?: { search?: string; status?: string; contact_id?: number; skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['orders', params],
    queryFn: async () => {
      try {
        const data = await orderApi.getAll(params)
        if (Array.isArray(data) && data.length > 0) {
          saveOrders(data).catch(() => {})
        }
        return data
      } catch (err) {
        if (!navigator.onLine || isOfflineError(err)) {
          const cached = await getOrdersFromCache()
          return cached as Order[]
        }
        throw err
      }
    },
  })
}

export function useOrderQuery(id: number | undefined) {
  return useQuery({
    queryKey: ['order', id],
    queryFn: async () => {
      try {
        const data = await orderApi.getById(id!)
        saveOrders([data]).catch(() => {})
        return data
      } catch (err) {
        if ((!navigator.onLine || isOfflineError(err)) && id) {
          const cached = await getOrderFromCache(id)
          if (cached) return cached as Order
        }
        throw err
      }
    },
    enabled: !!id,
  })
}

export function useCreateOrderMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (data: OrderCreate) => {
      const body = JSON.stringify(data)
      return requestOptimistic<Order>(
        '/orders/',
        { method: 'POST', body },
        () =>
          enqueueOptimistic(data, (d, localId) => {
            const now = new Date().toISOString()
            return {
              id: localId,
              order_number: `ORD-${now.slice(0, 10).replace(/-/g, '')}-${localId}`,
              contact_id: d.contact_id ?? -1,
              contact_name: d.contact_name ?? null,
              message_id: d.message_id ?? null,
              status: 'new',
              total: (d.items ?? []).reduce((sum, i) => sum + (i.quantity * i.price), 0),
              delivery_address: d.delivery_address ?? null,
              payment_method: d.payment_method ?? null,
              delivery_date: d.delivery_date ?? null,
              paid: false,
              items: (d.items ?? []).map((i, idx) => ({
                id: -(localId * 100 + idx),
                order_id: localId,
                product_id: i.product_id ?? null,
                name: i.name,
                quantity: i.quantity,
                price: i.price,
                created_at: now,
              })),
              comments: [],
              deleted_at: null,
              created_at: now,
              updated_at: now,
            } as Order
          }, saveOrders, '/orders'),
      )
    },

    onMutate: async () => {
      await qc.cancelQueries({ queryKey: ['orders'] })
      const previous = qc.getQueryData<Order[]>(['orders'])
      return { previous }
    },

    onError: (err, _data, context) => {
      if (!isOfflineError(err)) {
        qc.setQueryData(['orders'], context?.previous)
      }
    },

    onSuccess: (result) => {
      if ('__offline' in result) {
        qc.setQueryData<Order[]>(['orders'], (old) => {
          if (!old) return [result.entity]
          if (old.some(o => o.id === result.entity.id)) return old
          return [...old, result.entity]
        })
      } else {
        qc.setQueryData<Order[]>(['orders'], (old) => {
          if (!old) return [result]
          const withoutFake = old.filter(o => o.id >= 0 && o.id !== result.id)
          return [...withoutFake, result]
        })
      }
    },

    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['orders'] })
    },
  })
}

function patchOrdersCache(qc: ReturnType<typeof useQueryClient>, id: number, patch: Partial<Order> | ((o: Order) => Order)) {
  qc.setQueryData<Order[]>(['orders'], (old) => {
    if (!old) return old
    return old.map((o) => (o.id === id ? (typeof patch === 'function' ? patch(o) : { ...o, ...patch }) : o))
  })
}

export function useUpdateOrderMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: OrderUpdate }) => orderApi.update(id, data),
    onMutate: async ({ id, data }) => {
      await qc.cancelQueries({ queryKey: ['orders'] })
      const previous = qc.getQueryData<Order[]>(['orders'])
      patchOrdersCache(qc, id, data)
      return { previous }
    },
    onError: (err, _vars, context) => {
      if (!isOfflineError(err) && context?.previous !== undefined) {
        qc.setQueryData(['orders'], context.previous)
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['orders'] })
    },
  })
}

export function useUpdateOrderStatusMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: OrderStatus }) => orderApi.updateStatus(id, status),
    onMutate: async ({ id, status }) => {
      await qc.cancelQueries({ queryKey: ['orders'] })
      const previous = qc.getQueryData<Order[]>(['orders'])
      patchOrdersCache(qc, id, { status })
      return { previous }
    },
    onError: (err, _vars, context) => {
      if (!isOfflineError(err) && context?.previous !== undefined) {
        qc.setQueryData(['orders'], context.previous)
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['orders'] })
    },
  })
}

export function useDeleteOrderMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => orderApi.delete(id),
    onSuccess: (_data, id) => {
      patchOrdersCache(qc, id, { deleted_at: new Date().toISOString() })
      qc.invalidateQueries({ queryKey: ['orders'] })
    },
  })
}

export function useRestoreOrderMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => orderApi.restore(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['orders'] })
    },
  })
}

export function useAddOrderItemMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ orderId, data }: { orderId: number; data: OrderItemInput }) => orderApi.addItem(orderId, data),
    onSuccess: (_item, vars) => {
      qc.invalidateQueries({ queryKey: ['orders'] })
      qc.invalidateQueries({ queryKey: ['order', vars.orderId] })
    },
  })
}

export function useUpdateOrderItemMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ orderId, itemId, data }: { orderId: number; itemId: number; data: OrderItemUpdate }) =>
      orderApi.updateItem(orderId, itemId, data),
    onSuccess: (_item, vars) => {
      qc.invalidateQueries({ queryKey: ['orders'] })
      qc.invalidateQueries({ queryKey: ['order', vars.orderId] })
    },
  })
}

export function useRemoveOrderItemMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ orderId, itemId }: { orderId: number; itemId: number }) => orderApi.removeItem(orderId, itemId),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['orders'] })
      qc.invalidateQueries({ queryKey: ['order', vars.orderId] })
    },
  })
}

export function useAddOrderCommentMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ orderId, content }: { orderId: number; content: string }) => orderApi.addComment(orderId, content),
    onSuccess: (_comment, vars) => {
      qc.invalidateQueries({ queryKey: ['orders'] })
      qc.invalidateQueries({ queryKey: ['order', vars.orderId] })
    },
  })
}

export function useDeleteOrderCommentMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ orderId, commentId }: { orderId: number; commentId: number }) => orderApi.deleteComment(orderId, commentId),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['orders'] })
      qc.invalidateQueries({ queryKey: ['order', vars.orderId] })
    },
  })
}