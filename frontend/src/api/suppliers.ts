import type { Supplier, SupplierCreate, SupplierUpdate } from '../types/supplier'
import type { Product } from '../types/product'
import { request } from './client'

export const supplierApi = {
  getAll: (params?: { skip?: number; limit?: number }) => {
    const search = new URLSearchParams()
    if (params?.skip) search.set('skip', String(params.skip))
    if (params?.limit) search.set('limit', String(params.limit))
    const qs = search.toString()
    return request<Supplier[]>(`/suppliers${qs ? `?${qs}` : ''}`)
  },

  getById: (id: number) => request<Supplier>(`/suppliers/${id}`),

  getProducts: (id: number) => request<Product[]>(`/suppliers/${id}/products`),

  create: (data: SupplierCreate) =>
    request<Supplier>('/suppliers/', { method: 'POST', body: JSON.stringify(data) }),

  update: (id: number, data: SupplierUpdate) =>
    request<Supplier>(`/suppliers/${id}`, { method: 'PATCH', body: JSON.stringify(data), _entityId: id }),

  delete: (id: number) =>
    request<void>(`/suppliers/${id}`, { method: 'DELETE', _entityId: id }),
}
