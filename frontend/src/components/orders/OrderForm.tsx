import { useState } from 'react'
import { Plus, Trash2, PackageSearch } from 'lucide-react'
import Modal from '../common/Modal'
import Button from '../common/Button'
import ContactCombobox from '../contacts/ContactCombobox'
import ProductPicker from './ProductPicker'
import { formatMoney } from '../../utils/format'
import type { Contact } from '../../types/contact'
import type { OrderCreate, OrderItemInput } from '../../types/order'

interface OrderFormProps {
  open: boolean
  onClose: () => void
  contacts: Contact[]
  initial?: {
    contact_id?: number | null
    contact_name?: string | null
    message_id?: number | null
    message_preview?: string
  }
  onCreate: (data: OrderCreate) => Promise<void>
}

interface ItemRow extends OrderItemInput {
  key: number
}

let itemKeySeq = 0

function newItemRow(): ItemRow {
  itemKeySeq += 1
  return { key: itemKeySeq, name: '', quantity: 1, price: 0 }
}

function todayStr(): string {
  return new Date().toISOString().slice(0, 10)
}

function OrderForm({ open, onClose, contacts, initial, onCreate }: OrderFormProps) {
  const [contactId, setContactId] = useState<number | null>(initial?.contact_id ?? null)
  const [isNewContact, setIsNewContact] = useState<boolean>(!initial?.contact_id)
  const [contactName, setContactName] = useState(initial?.contact_name ?? '')
  const [contactPhone, setContactPhone] = useState('')
  const [contactEmail, setContactEmail] = useState('')
  const [deliveryAddress, setDeliveryAddress] = useState('')
  const [paymentMethod, setPaymentMethod] = useState('')
  const [deliveryDate, setDeliveryDate] = useState(todayStr())
  const [items, setItems] = useState<ItemRow[]>(() => [newItemRow()])
  const [creating, setCreating] = useState(false)
  const [created, setCreated] = useState(false)
  const [pickerKey, setPickerKey] = useState<number | null>(null)

  const total = items.reduce((sum, i) => sum + i.quantity * i.price, 0)

  const invalidItems = items.filter((i) => i.name.trim()).some((i) => i.price <= 0 || i.quantity <= 0)

  const updateItem = (key: number, patch: Partial<OrderItemInput>) => {
    setItems((prev) => prev.map((i) => (i.key === key ? { ...i, ...patch } : i)))
  }

  const removeItem = (key: number) => {
    setItems((prev) => (prev.length > 1 ? prev.filter((i) => i.key !== key) : prev.map((i) => ({ ...i, name: '', quantity: 1, price: 0 }))))
  }

  const handleCreate = async () => {
    if (creating) return
    const validItems = items
      .filter((i) => i.name.trim())
      .map(({ key: _key, ...rest }) => rest as OrderItemInput)
    const hasContact = contactId != null || contactName.trim()
    if (!validItems.length || !hasContact) return
    setCreating(true)
    try {
      await onCreate({
        contact_id: contactId,
        contact_name: contactId == null ? (contactName.trim() || null) : null,
        contact_phone: contactId == null ? (contactPhone.trim() || null) : null,
        contact_email: contactId == null ? (contactEmail.trim() || null) : null,
        message_id: initial?.message_id ?? null,
        delivery_address: deliveryAddress.trim() || null,
        payment_method: paymentMethod.trim() || null,
        delivery_date: deliveryDate || null,
        items: validItems,
      })
      setCreated(true)
    } finally {
      setCreating(false)
    }
  }

  const handleClose = () => {
    if (created) {
      setCreated(false)
      setItems([newItemRow()])
      setContactId(initial?.contact_id ?? null)
      setIsNewContact(!initial?.contact_id)
      setContactName(initial?.contact_name ?? '')
      setContactPhone('')
      setContactEmail('')
      setDeliveryAddress('')
      setPaymentMethod('')
      setDeliveryDate(todayStr())
    }
    onClose()
  }

  if (created) {
    return (
      <Modal open={open} onClose={handleClose} title="Заказ создан" maxWidth="max-w-md">
        <div className="p-6">
          <div className="p-4 rounded-xl bg-green-50 border border-green-200">
            <p className="text-sm font-medium text-green-700">✓ Заказ создан и добавлен в канбан</p>
          </div>
          <div className="flex justify-end mt-4">
            <Button onClick={handleClose}>Закрыть</Button>
          </div>
        </div>
      </Modal>
    )
  }

  return (
    <Modal open={open} onClose={handleClose} title="Новый заказ" maxWidth="max-w-2xl">
      <div className="p-6 space-y-4">
        {initial?.message_preview && (
          <div className="p-3 rounded-xl bg-gray-50 border border-gray-200 text-sm text-gray-600">
            {initial.message_preview}
          </div>
        )}

        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">Заказчик</p>
          <div className="flex items-center gap-3 mb-2">
            <label className="inline-flex items-center text-sm text-gray-600">
              <input
                type="radio"
                checked={!isNewContact}
                onChange={() => setIsNewContact(false)}
                className="mr-1.5"
              />
              Существующий
            </label>
            <label className="inline-flex items-center text-sm text-gray-600">
              <input
                type="radio"
                checked={isNewContact}
                onChange={() => setIsNewContact(true)}
                className="mr-1.5"
              />
              Новый
            </label>
          </div>
          {!isNewContact ? (
            <ContactCombobox
              id="order-contact"
              contacts={contacts}
              value={contactId}
              onChange={(id) => setContactId(id)}
              placeholder="Поиск контакта..."
            />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <input
                type="text"
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
                placeholder="Имя *"
                className="px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              />
              <input
                type="text"
                value={contactPhone}
                onChange={(e) => setContactPhone(e.target.value)}
                placeholder="Телефон"
                className="px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              />
              <input
                type="email"
                value={contactEmail}
                onChange={(e) => setContactEmail(e.target.value)}
                placeholder="Email"
                className="px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>
          )}
        </div>

        <div>
          <label htmlFor="order-delivery" className="block text-sm font-medium text-gray-700 mb-1">Адрес доставки</label>
          <input
            id="order-delivery"
            type="text"
            value={deliveryAddress}
            onChange={(e) => setDeliveryAddress(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            placeholder="Адрес доставки"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="order-delivery-date" className="block text-sm font-medium text-gray-700 mb-1">Дата доставки</label>
            <input
              id="order-delivery-date"
              type="date"
              value={deliveryDate}
              onChange={(e) => setDeliveryDate(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>
          <div>
            <label htmlFor="order-payment-method" className="block text-sm font-medium text-gray-700 mb-1">Способ оплаты</label>
            <select
              id="order-payment-method"
              value={paymentMethod}
              onChange={(e) => setPaymentMethod(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary bg-white"
            >
              <option value="">Не указан</option>
              <option value="card">Карта</option>
              <option value="cash">Наличные</option>
              <option value="sbp">СБП</option>
              <option value="transfer">Перевод</option>
            </select>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium text-gray-700">Позиции</p>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setItems((prev) => [...prev, newItemRow()])}
            >
              <Plus className="w-4 h-4 mr-1" />
              Добавить
            </Button>
          </div>
          <div className="space-y-2">
            {items.map((item, idx) => (
              <div key={item.key} className="flex items-center gap-2">
                <span className="text-xs text-gray-400 w-5 shrink-0">{idx + 1}.</span>
                <div className="relative flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setPickerKey(pickerKey === item.key ? null : item.key)}
                      className="shrink-0 p-2 text-gray-400 hover:text-primary transition-colors"
                      title="Выбрать из каталога"
                      aria-label="Выбрать товар из каталога"
                    >
                      <PackageSearch className="w-4 h-4" />
                    </button>
                    <input
                      type="text"
                      value={item.name}
                      onChange={(e) => updateItem(item.key, { name: e.target.value })}
                      placeholder="Товар *"
                      className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                    />
                  </div>
                  {pickerKey === item.key && (
                    <ProductPicker
                      onPick={(p) => {
                        updateItem(item.key, { product_id: p.id, name: p.name, price: p.price ?? 0 })
                        setPickerKey(null)
                      }}
                      onClose={() => setPickerKey(null)}
                    />
                  )}
                </div>
                <input
                  type="number"
                  min={0}
                  step="any"
                  value={item.quantity}
                  onChange={(e) => updateItem(item.key, { quantity: Number(e.target.value) || 0 })}
                  placeholder="Кол-во"
                  className="w-20 px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                />
                <input
                  type="number"
                  min={0}
                  step="any"
                  value={item.price}
                  onChange={(e) => updateItem(item.key, { price: Number(e.target.value) || 0 })}
                  placeholder="Цена"
                  className="w-24 px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                />
                <button
                  type="button"
                  onClick={() => removeItem(item.key)}
                  className="shrink-0 p-2 text-gray-300 hover:text-red-500 transition-colors"
                  title="Удалить позицию"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
          <div className="flex justify-end mt-2">
            <span className="text-sm text-gray-600">
              Итого: <span className="font-bold text-gray-900">{formatMoney(total)}</span>
            </span>
          </div>
          {invalidItems && (
            <p className="text-xs text-red-500">Заполните цену и количество для всех позиций</p>
          )}
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <Button variant="ghost" onClick={handleClose}>Отмена</Button>
          <Button
            onClick={handleCreate}
            disabled={creating || invalidItems || !items.some((i) => i.name.trim()) || (contactId == null && !contactName.trim())}
          >
            {creating ? 'Создание...' : 'Создать заказ'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default OrderForm