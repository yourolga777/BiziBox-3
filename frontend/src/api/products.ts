import type { Product, ProductCreate, ProductImportResult, ProductQueryParams, ProductSuggest, ProductUpdate } from '../types/product'
import { request } from './client'

export const productApi = {
  getAll: (params?: ProductQueryParams) => {
    const search = new URLSearchParams()
    if (params?.search) search.set('search', params.search)
    if (params?.supplier_id !== undefined && params?.supplier_id !== null) search.set('supplier_id', String(params.supplier_id))
    if (params?.sort_by) search.set('sort_by', params.sort_by)
    if (params?.sort_order) search.set('sort_order', params.sort_order)
    if (params?.skip) search.set('skip', String(params.skip))
    if (params?.limit) search.set('limit', String(params.limit))
    const qs = search.toString()
    return request<Product[]>(`/products${qs ? `?${qs}` : ''}`)
  },

  getArchived: (params?: { skip?: number; limit?: number }) => {
    const search = new URLSearchParams()
    if (params?.skip) search.set('skip', String(params.skip))
    if (params?.limit) search.set('limit', String(params.limit))
    const qs = search.toString()
    return request<Product[]>(`/products/archive${qs ? `?${qs}` : ''}`)
  },

  getById: (id: number) => request<Product>(`/products/${id}`),

  exportCsv: () => request<string>('/products/export/csv', { _textResponse: true }),

  importCsv: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request<ProductImportResult>('/products/import', { method: 'POST', body: formData })
  },

  suggest: (query: string, limit?: number) => {
    const qs = `q=${encodeURIComponent(query)}${limit ? `&limit=${limit}` : ''}`
    return request<ProductSuggest[]>(`/products/suggest?${qs}`)
  },

  create: (data: ProductCreate) =>
    request<Product>('/products/', { method: 'POST', body: JSON.stringify(data) }),

  update: (id: number, data: ProductUpdate) =>
    request<Product>(`/products/${id}`, { method: 'PATCH', body: JSON.stringify(data), _entityId: id }),

  delete: (id: number) =>
    request<void>(`/products/${id}`, { method: 'DELETE', _entityId: id }),

  permanentDelete: (id: number) =>
    request<void>(`/products/${id}/permanent`, { method: 'DELETE', _entityId: id }),

  restore: (id: number) =>
    request<Product>(`/products/${id}/restore`, { method: 'POST' }),
}
