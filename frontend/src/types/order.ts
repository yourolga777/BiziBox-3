export type OrderStatus = 'new' | 'in_progress' | 'shipped' | 'completed' | 'cancelled'

export const ORDER_STATUSES: OrderStatus[] = [
  'new',
  'in_progress',
  'shipped',
  'completed',
  'cancelled',
]

export const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  new: 'Новый',
  in_progress: 'В работе',
  shipped: 'Отправлен',
  completed: 'Завершён',
  cancelled: 'Отменён',
}

export const ORDER_KANBAN_STATUSES: OrderStatus[] = ['new', 'in_progress', 'shipped', 'completed', 'cancelled']

export interface OrderItem {
  id: number
  order_id: number
  product_id: number | null
  name: string
  quantity: number
  price: number
  created_at: string | null
}

export interface OrderComment {
  id: number
  order_id: number
  content: string
  created_at: string | null
}

export interface Order {
  id: number
  order_number: string | null
  contact_id: number
  contact_name: string | null
  message_id: number | null
  status: OrderStatus
  total: number
  delivery_address: string | null
  payment_method: string | null
  delivery_date: string | null
  paid: boolean
  items: OrderItem[]
  comments: OrderComment[]
  deleted_at: string | null
  created_at: string | null
  updated_at: string | null
}

export interface OrderItemInput {
  product_id?: number | null
  name: string
  quantity: number
  price: number
}

export interface OrderItemUpdate {
  quantity?: number
  price?: number
}

export interface OrderImportResult {
  created: number
  skipped: number
  errors: string[]
}

export interface OrderCreate {
  contact_id?: number | null
  contact_name?: string | null
  contact_phone?: string | null
  contact_email?: string | null
  message_id?: number | null
  delivery_address?: string | null
  payment_method?: string | null
  delivery_date?: string | null
  items: OrderItemInput[]
}

export interface OrderUpdate {
  delivery_address?: string | null
  payment_method?: string | null
  delivery_date?: string | null
  paid?: boolean
}

export interface OrderSuggest {
  contact_id: number | null
  contact_name: string | null
  suggested_amount: number | null
  message_preview: string
  confidence: number
}