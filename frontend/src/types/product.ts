export interface Product {
  id: number
  owner_id: number
  name: string
  sku: string | null
  price: number | null
  purchase_price: number | null
  stock: number | null
  unit: string | null
  description: string | null
  supplier_id: number | null
  supplier_name: string | null
  deleted_at: string | null
  created_at: string | null
  updated_at: string | null
  margin: number | null
  margin_percent: number | null
}

export interface ProductCreate {
  name: string
  sku?: string | null
  price?: number | null
  purchase_price?: number | null
  stock?: number | null
  unit?: string | null
  description?: string | null
  supplier_id?: number | null
}

export interface ProductUpdate {
  name?: string
  sku?: string | null
  price?: number | null
  purchase_price?: number | null
  stock?: number | null
  unit?: string | null
  description?: string | null
  supplier_id?: number | null
}

export interface ProductSuggest {
  id: number
  name: string
  price: number | null
  stock: number | null
  sku: string | null
}

export interface ProductImportResult {
  created: number
  updated: number
  skipped: number
}

export interface ProductQueryParams {
  search?: string
  supplier_id?: number
  sort_by?: string
  sort_order?: string
  skip?: number
  limit?: number
}
