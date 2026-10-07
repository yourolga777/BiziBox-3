export interface PaginatedResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
}

export interface ApiErrorDetail {
  detail: string
}

export interface BulkOperationResult {
  deleted?: number
  restored?: number
  updated?: number
}

export type Nullable<T> = T | null

export type Optional<T> = T | undefined
