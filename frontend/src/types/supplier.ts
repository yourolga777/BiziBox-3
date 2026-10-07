export interface Supplier {
  id: number
  owner_id: number
  contact_id: number
  contact_name: string | null
  contact_phone: string | null
  company_name: string | null
  inn: string | null
  notes: string | null
  deleted_at: string | null
  created_at: string | null
  updated_at: string | null
}

export interface SupplierCreate {
  contact_id: number
  company_name?: string | null
  inn?: string | null
  notes?: string | null
}

export interface SupplierUpdate {
  company_name?: string | null
  inn?: string | null
  notes?: string | null
}
