import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { productApi, isOfflineError, requestOptimistic } from '../api/client'
import { saveProducts, getProductsFromCache } from '../offline/db'
import { enqueueOptimistic } from '../offline/optimistic'
import type { Product, ProductCreate, ProductQueryParams, ProductUpdate } from '../types/product'

export function useProductsQuery(params?: ProductQueryParams) {
  return useQuery({
    queryKey: ['products', params],
    queryFn: async () => {
      try {
        const data = await productApi.getAll(params)
        if (Array.isArray(data) && data.length > 0) {
          saveProducts(data).catch(() => {})
        }
        return data
      } catch (err) {
        if (!navigator.onLine || isOfflineError(err)) {
          const cached = await getProductsFromCache()
          return cached as Product[]
        }
        throw err
      }
    },
  })
}

export function useCreateProductMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (data: ProductCreate) => {
      const body = JSON.stringify(data)
      return requestOptimistic<Product>(
        '/products/',
        { method: 'POST', body },
        () =>
          enqueueOptimistic(data, (d, localId) => {
            const price = d.price ?? 0
            const purchase = d.purchase_price ?? 0
            return {
              id: localId,
              owner_id: 0,
              name: d.name,
              sku: d.sku ?? null,
              price: d.price ?? null,
              purchase_price: d.purchase_price ?? null,
              stock: d.stock ?? null,
              unit: d.unit ?? 'шт',
              description: d.description ?? null,
              supplier_id: d.supplier_id ?? null,
              supplier_name: null,
              deleted_at: null,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              margin: price - purchase,
              margin_percent: purchase ? (price - purchase) / purchase * 100 : null,
            } as Product
          }, saveProducts, '/products'),
      )
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

function patchProductsCache(qc: ReturnType<typeof useQueryClient>, id: number, patch: Partial<Product> | ((p: Product) => Product)) {
  qc.setQueryData<Product[]>(['products'], (old) => {
    if (!old) return old
    return old.map((p) => (p.id === id ? (typeof patch === 'function' ? patch(p) : { ...p, ...patch }) : p))
  })
}

export function useUpdateProductMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ProductUpdate }) => productApi.update(id, data),
    onMutate: async ({ id, data }) => {
      await qc.cancelQueries({ queryKey: ['products'] })
      const previous = qc.getQueryData<Product[]>(['products'])
      patchProductsCache(qc, id, data)
      return { previous }
    },
    onError: (err, _vars, context) => {
      if (!isOfflineError(err) && context?.previous !== undefined) {
        qc.setQueryData(['products'], context.previous)
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

export function useDeleteProductMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => productApi.delete(id),
    onSuccess: (_data, id) => {
      qc.setQueryData<Product[]>(['products'], (old) => (old ? old.filter((p) => p.id !== id) : old))
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

export function useRestoreProductMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => productApi.restore(id),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['products'] })
    },
  })
}
