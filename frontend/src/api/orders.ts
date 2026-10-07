import type { Order, OrderComment, OrderCreate, OrderImportResult, OrderItem, OrderItemInput, OrderItemUpdate, OrderSuggest, OrderUpdate } from '../types/order'
import { request } from './client'

export const orderApi = {
  getAll: (params?: { search?: string; status?: string; contact_id?: number; skip?: number; limit?: number }) => {
    const search = new URLSearchParams()
    if (params?.search) search.set('search', params.search)
    if (params?.status) search.set('status', params.status)
    if (params?.contact_id) search.set('contact_id', String(params.contact_id))
    if (params?.skip) search.set('skip', String(params.skip))
    if (params?.limit) search.set('limit', String(params.limit))
    const qs = search.toString()
    return request<Order[]>(`/orders${qs ? `?${qs}` : ''}`)
  },

  getArchived: (params?: { skip?: number; limit?: number }) => {
    const search = new URLSearchParams()
    if (params?.skip) search.set('skip', String(params.skip))
    if (params?.limit) search.set('limit', String(params.limit))
    const qs = search.toString()
    return request<Order[]>(`/orders/archive${qs ? `?${qs}` : ''}`)
  },

  getById: (id: number) => request<Order>(`/orders/${id}`),

  exportCsv: () => request<string>('/orders/export/csv', { _textResponse: true }),

  importCsv: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request<OrderImportResult>('/orders/import/csv', {
      method: 'POST',
      body: formData,
      _skipEnqueue: true,
    })
  },

  suggest: (messageId: number) => request<OrderSuggest>(`/orders/suggest/${messageId}`),

  create: (data: OrderCreate) =>
    request<Order>('/orders/', { method: 'POST', body: JSON.stringify(data) }),

  update: (id: number, data: OrderUpdate) =>
    request<Order>(`/orders/${id}`, { method: 'PATCH', body: JSON.stringify(data), _entityId: id }),

  updateStatus: (id: number, status: string) =>
    request<Order>(`/orders/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }), _entityId: id }),

  delete: (id: number) =>
    request<void>(`/orders/${id}`, { method: 'DELETE', _entityId: id }),

  restore: (id: number) =>
    request<Order>(`/orders/${id}/restore`, { method: 'POST' }),

  addComment: (orderId: number, content: string) =>
    request<OrderComment>(`/orders/${orderId}/comments`, { method: 'POST', body: JSON.stringify({ content }) }),

  deleteComment: (orderId: number, commentId: number) =>
    request<void>(`/orders/${orderId}/comments/${commentId}`, { method: 'DELETE', _entityId: orderId }),

  addItem: (orderId: number, data: OrderItemInput) =>
    request<OrderItem>(`/orders/${orderId}/items`, { method: 'POST', body: JSON.stringify(data) }),

  removeItem: (orderId: number, itemId: number) =>
    request<void>(`/orders/${orderId}/items/${itemId}`, { method: 'DELETE', _entityId: orderId }),

  updateItem: (orderId: number, itemId: number, data: OrderItemUpdate) =>
    request<OrderItem>(`/orders/${orderId}/items/${itemId}`, { method: 'PATCH', body: JSON.stringify(data), _entityId: orderId }),
}