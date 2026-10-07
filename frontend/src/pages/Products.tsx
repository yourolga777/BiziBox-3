import { useMemo, useState } from 'react'
import { Package, Plus, Download, Upload, Users, ArrowUpDown } from 'lucide-react'
import Button from '../components/common/Button'
import Card from '../components/common/Card'
import { SkeletonList } from '../components/common/Skeleton'
import { productApi } from '../api/client'
import { useToast } from '../components/common/Toast'
import { useContactsQuery } from '../hooks/queries'
import {
  useProductsQuery,
  useCreateProductMutation,
  useUpdateProductMutation,
  useDeleteProductMutation,
} from '../hooks/products'
import {
  useSuppliersQuery,
  useCreateSupplierMutation,
  useDeleteSupplierMutation,
} from '../hooks/suppliers'
import ProductForm from '../components/products/ProductForm'
import SupplierManager from '../components/products/SupplierManager'
import ImportModal from '../components/products/ImportModal'
import type { Product, ProductCreate, ProductUpdate } from '../types/product'
import { formatMoney } from '../utils/format'

type SortKey = 'name' | 'price' | 'stock'

function Products() {
  const [search, setSearch] = useState('')
  const [supplierFilter, setSupplierFilter] = useState<number | null>(null)
  const [sortBy, setSortBy] = useState<SortKey>('name')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Product | null>(null)
  const [showSuppliers, setShowSuppliers] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [exporting, setExporting] = useState(false)
  const { showToast } = useToast()

  const productsQuery = useProductsQuery({ search: search || undefined, supplier_id: supplierFilter ?? undefined })
  const suppliersQuery = useSuppliersQuery()
  const contactsQuery = useContactsQuery()
  const createProduct = useCreateProductMutation()
  const updateProduct = useUpdateProductMutation()
  const deleteProduct = useDeleteProductMutation()
  const createSupplier = useCreateSupplierMutation()
  const deleteSupplier = useDeleteSupplierMutation()

  const products = productsQuery.data ?? []
  const suppliers = suppliersQuery.data ?? []
  const contacts = contactsQuery.data ?? []
  const loading = productsQuery.isLoading
  const error = productsQuery.error

  const sorted = useMemo(() => {
    const arr = [...products]
    arr.sort((a, b) => {
      let av: number | string = 0
      let bv: number | string = 0
      if (sortBy === 'name') {
        av = a.name.toLowerCase()
        bv = b.name.toLowerCase()
      } else if (sortBy === 'price') {
        av = a.price ?? 0
        bv = b.price ?? 0
      } else if (sortBy === 'stock') {
        av = a.stock ?? 0
        bv = b.stock ?? 0
      }
      if (av < bv) return sortOrder === 'asc' ? -1 : 1
      if (av > bv) return sortOrder === 'asc' ? 1 : -1
      return 0
    })
    return arr
  }, [products, sortBy, sortOrder])

  const toggleSort = (key: SortKey) => {
    if (sortBy === key) {
      setSortOrder((o) => (o === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(key)
      setSortOrder('asc')
    }
  }

  const handleSave = async (data: ProductCreate | ProductUpdate) => {
    if (editing) {
      await updateProduct.mutateAsync({ id: editing.id, data: data as ProductUpdate })
    } else {
      await createProduct.mutateAsync(data as ProductCreate)
    }
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      const csv = await productApi.exportCsv()
      const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'products.csv'
      a.click()
      URL.revokeObjectURL(url)
      showToast('Файл выгружен', 'success')
    } catch {
      showToast('Не удалось выгрузить файл', 'error')
    } finally {
      setExporting(false)
    }
  }

  const sortIcon = (key: SortKey) => (sortBy === key ? (sortOrder === 'asc' ? '↑' : '↓') : '')

  if (loading) {
    return (
      <div className="space-y-6">
        <Header search={search} setSearch={setSearch} onExport={handleExport} exporting={exporting}
          onCreate={() => { setEditing(null); setShowForm(true) }} onSuppliers={() => setShowSuppliers(true)} onImport={() => setShowImport(true)} />
        <SkeletonList count={4} />
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <Header search={search} setSearch={setSearch} onExport={handleExport} exporting={exporting}
          onCreate={() => { setEditing(null); setShowForm(true) }} onSuppliers={() => setShowSuppliers(true)} onImport={() => setShowImport(true)} />
        <Card>
          <div className="text-center py-8">
            <p className="text-red-500 mb-4">{error instanceof Error ? error.message : 'Ошибка загрузки'}</p>
            <Button onClick={() => productsQuery.refetch()}>Повторить</Button>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <Header search={search} setSearch={setSearch} onExport={handleExport} exporting={exporting}
        onCreate={() => { setEditing(null); setShowForm(true) }} onSuppliers={() => setShowSuppliers(true)} onImport={() => setShowImport(true)} />

      <div className="flex items-center gap-3">
        <label htmlFor="products-supplier-filter" className="text-sm text-gray-500">Поставщик:</label>
        <select
          id="products-supplier-filter"
          value={supplierFilter ?? ''}
          onChange={(e) => setSupplierFilter(e.target.value ? Number(e.target.value) : null)}
          className="px-3 py-1.5 rounded-lg border border-gray-200 text-sm bg-white outline-none focus:border-primary"
        >
          <option value="">Все</option>
          {suppliers.map((s) => (
            <option key={s.id} value={s.id}>{s.contact_name || s.company_name || `#${s.id}`}</option>
          ))}
        </select>
      </div>

      <Card>
        {products.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <Package className="w-10 h-10 mx-auto mb-2 opacity-50" />
            <p>Товаров пока нет. Создайте первый или импортируйте CSV.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-100">
                  <th className="px-4 py-3 font-medium cursor-pointer select-none" onClick={() => toggleSort('name')}>
                    <span className="inline-flex items-center gap-1">Название <ArrowUpDown size={12} /> {sortIcon('name')}</span>
                  </th>
                  <th className="px-4 py-3 font-medium">Артикул</th>
                  <th className="px-4 py-3 font-medium text-right cursor-pointer select-none" onClick={() => toggleSort('price')}>
                    <span className="inline-flex items-center gap-1">Цена {sortIcon('price')}</span>
                  </th>
                  <th className="px-4 py-3 font-medium text-right">Закупка</th>
                  <th className="px-4 py-3 font-medium text-right">Наценка</th>
                  <th className="px-4 py-3 font-medium text-right cursor-pointer select-none" onClick={() => toggleSort('stock')}>
                    <span className="inline-flex items-center gap-1">Остаток {sortIcon('stock')}</span>
                  </th>
                  <th className="px-4 py-3 font-medium">Поставщик</th>
                  <th className="px-4 py-3 font-medium text-right">Действия</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {sorted.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-800">{p.name}</td>
                    <td className="px-4 py-3 text-gray-500">{p.sku || '—'}</td>
                    <td className="px-4 py-3 text-right">{formatMoney(p.price)}</td>
                    <td className="px-4 py-3 text-right text-gray-500">{formatMoney(p.purchase_price)}</td>
                    <td className="px-4 py-3 text-right text-gray-500">
                      {p.margin_percent != null ? `${p.margin_percent.toFixed(1)}%` : '—'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {p.stock != null ? `${p.stock} ${p.unit || 'шт'}` : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500">{p.supplier_name || '—'}</td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <button className="text-primary hover:underline text-sm" onClick={() => { setEditing(p); setShowForm(true) }}>
                        Изменить
                      </button>
                      <button
                        className="text-red-500 hover:underline text-sm ml-3"
                        onClick={() => {
                          if (window.confirm('Переместить товар в архив?')) deleteProduct.mutate(p.id)
                        }}
                      >
                        В архив
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <ProductForm
        open={showForm}
        onClose={() => { setShowForm(false); setEditing(null) }}
        product={editing}
        suppliers={suppliers}
        onSave={handleSave}
      />
      <SupplierManager
        open={showSuppliers}
        onClose={() => setShowSuppliers(false)}
        suppliers={suppliers}
        contacts={contacts}
        onCreate={(data) => createSupplier.mutateAsync(data)}
        onDelete={(id) => deleteSupplier.mutateAsync(id)}
      />
      <ImportModal
        open={showImport}
        onClose={() => setShowImport(false)}
        onImport={async (file) => {
          const result = await productApi.importCsv(file)
          await Promise.all([
            productsQuery.refetch(),
            suppliersQuery.refetch(),
            contactsQuery.refetch(),
          ])
          return result
        }}
      />
    </div>
  )
}

function Header({ search, setSearch, onExport, exporting, onCreate, onSuppliers, onImport }: {
  search: string
  setSearch: (v: string) => void
  onExport: () => void
  exporting: boolean
  onCreate: () => void
  onSuppliers: () => void
  onImport: () => void
}) {
  return (
    <div className="flex items-center justify-between flex-wrap gap-3">
      <div className="flex items-center gap-3">
        <Package className="w-6 h-6 text-primary" />
        <h2 className="text-2xl font-semibold text-gray-900">Каталог</h2>
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Поиск по названию или артикулу…"
          className="px-3 py-2 rounded-lg border border-gray-200 text-sm w-64 outline-none focus:border-primary"
        />
        <Button variant="ghost" size="sm" onClick={onImport}>
          <Upload className="w-4 h-4 mr-1" />
          Импорт
        </Button>
        <Button variant="ghost" size="sm" onClick={onExport} disabled={exporting}>
          <Download className="w-4 h-4 mr-1" />
          {exporting ? 'Выгрузка…' : 'Экспорт'}
        </Button>
        <Button variant="ghost" size="sm" onClick={onSuppliers}>
          <Users className="w-4 h-4 mr-1" />
          Поставщики
        </Button>
        <Button size="sm" onClick={onCreate}>
          <Plus className="w-4 h-4 mr-1" />
          Товар
        </Button>
      </div>
    </div>
  )
}

export default Products
