import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { supplierApi, isOfflineError } from '../api/client'
import { saveSuppliers, getSuppliersFromCache } from '../offline/db'
import type { Supplier, SupplierCreate, SupplierUpdate } from '../types/supplier'

export function useSuppliersQuery() {
  return useQuery({
    queryKey: ['suppliers'],
    queryFn: async () => {
      try {
        const data = await supplierApi.getAll()
        if (Array.isArray(data) && data.length > 0) {
          saveSuppliers(data).catch(() => {})
        }
        return data
      } catch (err) {
        if (!navigator.onLine || isOfflineError(err)) {
          const cached = await getSuppliersFromCache()
          return cached as Supplier[]
        }
        throw err
      }
    },
  })
}

export function useCreateSupplierMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: SupplierCreate) => supplierApi.create(data),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['suppliers'] })
    },
  })
}

export function useUpdateSupplierMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: SupplierUpdate }) => supplierApi.update(id, data),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['suppliers'] })
    },
  })
}

export function useDeleteSupplierMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => supplierApi.delete(id),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['suppliers'] })
      qc.invalidateQueries({ queryKey: ['products'] })
    },
  })
}
