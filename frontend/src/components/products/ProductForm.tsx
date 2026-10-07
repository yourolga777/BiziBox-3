import { useEffect, useState } from 'react'
import Modal from '../common/Modal'
import Button from '../common/Button'
import type { Product, ProductCreate, ProductUpdate } from '../../types/product'
import type { Supplier } from '../../types/supplier'

interface ProductFormProps {
  open: boolean
  onClose: () => void
  product?: Product | null
  suppliers: Supplier[]
  onSave: (data: ProductCreate | ProductUpdate) => Promise<void>
}

function toNumber(value: string): number | null {
  const parsed = parseFloat(value.replace(',', '.'))
  return Number.isNaN(parsed) ? null : parsed
}

function ProductForm({ open, onClose, product, suppliers, onSave }: ProductFormProps) {
  const [name, setName] = useState('')
  const [sku, setSku] = useState('')
  const [price, setPrice] = useState('')
  const [purchasePrice, setPurchasePrice] = useState('')
  const [stock, setStock] = useState('')
  const [unit, setUnit] = useState('шт')
  const [description, setDescription] = useState('')
  const [supplierId, setSupplierId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setName(product?.name ?? '')
    setSku(product?.sku ?? '')
    setPrice(product?.price != null ? String(product.price) : '')
    setPurchasePrice(product?.purchase_price != null ? String(product.purchase_price) : '')
    setStock(product?.stock != null ? String(product.stock) : '')
    setUnit(product?.unit ?? 'шт')
    setDescription(product?.description ?? '')
    setSupplierId(product?.supplier_id ?? null)
    setError(null)
  }, [open, product])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      setError('Укажите название товара')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await onSave({
        name: name.trim(),
        sku: sku.trim() || null,
        price: toNumber(price),
        purchase_price: toNumber(purchasePrice),
        stock: toNumber(stock),
        unit: unit.trim() || null,
        description: description.trim() || null,
        supplier_id: supplierId,
      })
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить товар')
    } finally {
      setSaving(false)
    }
  }

  const inputClass = 'w-full px-3 py-2 rounded-xl border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary'

  return (
    <Modal open={open} onClose={onClose} title={product ? 'Редактировать товар' : 'Новый товар'}>
      <form onSubmit={handleSubmit} className="p-5 space-y-4">
        <div>
          <label htmlFor="product-name" className="block text-sm font-medium text-gray-700 mb-1">Название *</label>
          <input
            id="product-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={inputClass}
            placeholder="Например, Стул офисный"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="product-sku" className="block text-sm font-medium text-gray-700 mb-1">Артикул (SKU)</label>
            <input
              id="product-sku"
              type="text"
              value={sku}
              onChange={(e) => setSku(e.target.value)}
              className={inputClass}
              placeholder="SKU-001"
            />
          </div>
          <div>
            <label htmlFor="product-unit" className="block text-sm font-medium text-gray-700 mb-1">Ед. измерения</label>
            <input
              id="product-unit"
              type="text"
              value={unit}
              onChange={(e) => setUnit(e.target.value)}
              className={inputClass}
              placeholder="шт"
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label htmlFor="product-price" className="block text-sm font-medium text-gray-700 mb-1">Цена, ₽</label>
            <input
              id="product-price"
              type="number"
              step="any"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              className={inputClass}
              placeholder="0"
            />
          </div>
          <div>
            <label htmlFor="product-purchase" className="block text-sm font-medium text-gray-700 mb-1">Закупка, ₽</label>
            <input
              id="product-purchase"
              type="number"
              step="any"
              value={purchasePrice}
              onChange={(e) => setPurchasePrice(e.target.value)}
              className={inputClass}
              placeholder="0"
            />
          </div>
          <div>
            <label htmlFor="product-stock" className="block text-sm font-medium text-gray-700 mb-1">Остаток</label>
            <input
              id="product-stock"
              type="number"
              step="any"
              value={stock}
              onChange={(e) => setStock(e.target.value)}
              className={inputClass}
              placeholder="0"
            />
          </div>
        </div>

        <div>
          <label htmlFor="product-supplier" className="block text-sm font-medium text-gray-700 mb-1">Поставщик</label>
          <select
            id="product-supplier"
            value={supplierId ?? ''}
            onChange={(e) => setSupplierId(e.target.value ? Number(e.target.value) : null)}
            className={`${inputClass} bg-white`}
          >
            <option value="">— без поставщика —</option>
            {suppliers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.contact_name || s.company_name || `Поставщик #${s.id}`}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="product-description" className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
          <textarea
            id="product-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className={`${inputClass} resize-none`}
            placeholder="Дополнительная информация"
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>Отмена</Button>
          <Button type="submit" disabled={saving}>{saving ? 'Сохранение…' : 'Сохранить'}</Button>
        </div>
      </form>
    </Modal>
  )
}

export default ProductForm
