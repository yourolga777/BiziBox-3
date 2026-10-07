import { z } from 'zod'

export const contactSchema = z.object({
  name: z.string().max(200, 'Максимум 200 символов').optional().or(z.literal('')),
  phone: z.string().max(50, 'Максимум 50 символов').optional().or(z.literal('')),
  email: z.string().email('Некорректный email').optional().or(z.literal('')),
  telegram_username: z.string().max(100, 'Максимум 100 символов').optional().or(z.literal('')),
  notes: z.string().max(2000, 'Максимум 2000 символов').optional().or(z.literal('')),
  is_known: z.boolean().optional(),
  is_favorite: z.boolean().optional(),
  life_sphere: z.enum(['personal', 'work', 'channels', 'spam']).optional().or(z.literal('')),
  birthday: z
    .string()
    .refine(
      (v) => v === '' || (/^\d{4}-\d{2}-\d{2}$/.test(v) && !isNaN(new Date(v).getTime())),
      'Некорректная дата',
    )
    .optional()
    .or(z.literal('')),
  folder_ids: z.array(z.number().int().positive()).optional(),
})

export type ContactFormData = z.infer<typeof contactSchema>

export const orderCreateSchema = z.object({
  contact_id: z.number().positive('Контакт обязателен'),
  notes: z.string().optional().or(z.literal('')),
  delivery_address: z.string().optional().or(z.literal('')),
  payment_method: z.string().optional().or(z.literal('')),
  items: z.array(z.object({
    product_id: z.number().positive().optional().nullable(),
    name: z.string().min(1, 'Название товара обязательно'),
    quantity: z.number().positive('Количество должно быть больше 0'),
    price: z.number().nonnegative('Цена не может быть отрицательной'),
  })).min(1, 'Добавьте хотя бы один товар'),
})

export type OrderCreateFormData = z.infer<typeof orderCreateSchema>

export const productSchema = z.object({
  name: z.string().min(1, 'Название обязательно').max(200, 'Максимум 200 символов'),
  sku: z.string().max(50, 'Максимум 50 символов').optional().or(z.literal('')),
  price: z.number().nonnegative('Цена не может быть отрицательной'),
  unit: z.string().max(20, 'Максимум 20 символов').optional().or(z.literal('')),
  description: z.string().max(5000, 'Максимум 5000 символов').optional().or(z.literal('')),
  quantity: z.number().nonnegative('Количество не может быть отрицательным'),
  category_id: z.number().positive().optional().nullable(),
  supplier_id: z.number().positive().optional().nullable(),
  purchase_price: z.number().nonnegative('Цена закупки не может быть отрицательной'),
  purchase_date: z.string().optional().or(z.literal('')),
})

export type ProductFormData = z.infer<typeof productSchema>

export const messageSchema = z.object({
  content: z.string().min(1, 'Сообщение не может быть пустым').max(10000, 'Максимум 10000 символов'),
  contact_id: z.number().positive('Контакт обязателен'),
  channel: z.string().min(1, 'Канал обязателен'),
  direction: z.enum(['incoming', 'outgoing']),
  channel_message_id: z.string().optional().nullable(),
})

export type MessageFormData = z.infer<typeof messageSchema>
