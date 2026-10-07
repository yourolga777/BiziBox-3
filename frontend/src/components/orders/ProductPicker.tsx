import { useEffect, useRef, useState } from 'react'
import { Search } from 'lucide-react'
import { productApi } from '../../api/client'
import type { ProductSuggest } from '../../types/product'

interface ProductPickerProps {
  onPick: (p: ProductSuggest) => void
  onClose: () => void
}

function ProductPicker({ onPick, onClose }: ProductPickerProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<ProductSuggest[]>([])
  const [loading, setLoading] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
    function onClickOutside(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) onClose()
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [onClose])

  useEffect(() => {
    let cancelled = false
    const q = query.trim()
    if (q.length < 1) {
      setResults([])
      return
    }
    setLoading(true)
    const t = setTimeout(() => {
      productApi
        .suggest(q, 8)
        .then((r) => { if (!cancelled) setResults(r) })
        .catch(() => { if (!cancelled) setResults([]) })
        .finally(() => { if (!cancelled) setLoading(false) })
    }, 200)
    return () => { cancelled = true; clearTimeout(t) }
  }, [query])

  return (
    <div ref={rootRef} className="absolute top-full left-0 right-0 z-30 mt-1 bg-white rounded-xl border border-gray-200 shadow-lg">
      <div className="p-2 relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Поиск товара из каталога…"
          className="w-full pl-8 pr-3 py-2 rounded-lg border border-gray-200 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
        />
      </div>
      <ul className="max-h-48 overflow-y-auto">
        {loading && <li className="px-3 py-2 text-sm text-gray-400">Поиск…</li>}
        {!loading && results.length === 0 && query.trim() !== '' && (
          <li className="px-3 py-2 text-sm text-gray-400">Ничего не найдено</li>
        )}
        {!loading && results.length === 0 && query.trim() === '' && (
          <li className="px-3 py-2 text-sm text-gray-400">Введите название товара…</li>
        )}
        {!loading && results.map((p) => (
          <li key={p.id}>
            <button
              type="button"
              onClick={() => onPick(p)}
              className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center justify-between gap-2"
            >
              <span className="truncate text-gray-700">{p.name}</span>
              {p.price != null && <span className="text-xs text-gray-400 shrink-0">{p.price} ₽</span>}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default ProductPicker
