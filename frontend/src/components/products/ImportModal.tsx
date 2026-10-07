import { useRef, useState } from 'react'
import { Upload } from 'lucide-react'
import Modal from '../common/Modal'
import Button from '../common/Button'
import type { ProductImportResult } from '../../types/product'

interface ImportModalProps {
  open: boolean
  onClose: () => void
  onImport: (file: File) => Promise<ProductImportResult>
}

function ImportModal({ open, onClose, onImport }: ImportModalProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [importing, setImporting] = useState(false)
  const [result, setResult] = useState<ProductImportResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reset = () => {
    setFile(null)
    setResult(null)
    setError(null)
  }

  const handleFile = (f: File | null) => {
    setFile(f)
    setResult(null)
    setError(null)
  }

  const handleImport = async () => {
    if (!file) return
    setImporting(true)
    setError(null)
    try {
      const res = await onImport(file)
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось импортировать CSV')
    } finally {
      setImporting(false)
    }
  }

  return (
    <Modal open={open} onClose={() => { reset(); onClose() }} title="Импорт товаров из CSV">
      <div className="p-5 space-y-4">
        <p className="text-sm text-gray-500">
          Ожидаются колонки: <code className="bg-gray-100 px-1 rounded">name</code>, <code className="bg-gray-100 px-1 rounded">sku</code>,{' '}
          <code className="bg-gray-100 px-1 rounded">price</code>, <code className="bg-gray-100 px-1 rounded">purchase_price</code>,{' '}
          <code className="bg-gray-100 px-1 rounded">stock</code>, <code className="bg-gray-100 px-1 rounded">unit</code>,{' '}
          <code className="bg-gray-100 px-1 rounded">description</code>, <code className="bg-gray-100 px-1 rounded">supplier</code>.
          Неизвестный поставщик будет создан автоматически (контакт + поставщик).
        </p>

        <div
          role="button"
          tabIndex={0}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              inputRef.current?.click()
            }
          }}
          className="border-2 border-dashed border-gray-200 rounded-xl p-6 text-center cursor-pointer hover:border-primary transition-colors"
        >
          <Upload className="w-6 h-6 mx-auto text-gray-400" />
          <p className="text-sm text-gray-600 mt-2">
            {file ? file.name : 'Нажмите, чтобы выбрать CSV-файл'}
          </p>
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
          />
        </div>

        {result && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-700">
            Импорт завершён: создано {result.created}, обновлено {result.updated}, пропущено {result.skipped}.
          </div>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => { reset(); onClose() }}>Закрыть</Button>
          <Button onClick={handleImport} disabled={!file || importing}>
            {importing ? 'Импорт…' : 'Импортировать'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default ImportModal
