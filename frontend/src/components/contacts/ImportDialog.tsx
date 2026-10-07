import { useState, useRef } from 'react'
import { Dialog } from '@headlessui/react'
import { Upload } from 'lucide-react'
import { contactApi } from '../../api/client'
import type { ImportResult } from '../../types/contact'

export default function ImportDialog({
  open,
  onClose,
}: {
  open: boolean
  onClose: () => void
}) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setError('')
    try {
      const res = await contactApi.importCsv(file)
      setResult(res)
    } catch {
      setError('Ошибка при импорте. Проверьте формат CSV.')
    }
    setUploading(false)
  }

  const handleExport = async () => {
    try {
      const csv = await contactApi.exportCsv()
      const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `contacts_${new Date().toISOString().slice(0, 10)}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setError('Ошибка при экспорте')
    }
  }

  return (
    <Dialog open={open} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="w-full max-w-md bg-white rounded-xl p-6">
          <Dialog.Title className="text-lg font-semibold mb-4">Импорт / Экспорт контактов</Dialog.Title>

          <div className="space-y-4">
            <div>
              <label htmlFor="import-file" className="block text-sm font-medium text-gray-700 mb-2">Импорт CSV</label>
              <div className="flex gap-2">
                <input
                  ref={fileRef}
                  id="import-file"
                  type="file"
                  accept=".csv"
                  onChange={handleFile}
                  className="hidden"
                />
                <button
                  onClick={() => fileRef.current?.click()}
                  disabled={uploading}
                  className="flex items-center gap-2 px-4 py-2 text-sm text-blue-600 border border-blue-300 rounded-lg hover:bg-blue-50 disabled:opacity-50"
                >
                  <Upload className="w-4 h-4" />
                  {uploading ? 'Загрузка...' : 'Выбрать CSV-файл'}
                </button>
              </div>
              {result && (
                <p className="text-sm text-green-600 mt-2">
                  Создано: {result.created}, обновлено: {result.updated}
                </p>
              )}
              {error && <p className="text-sm text-red-500 mt-2">{error}</p>}
            </div>

            <div className="border-t pt-4">
              <label htmlFor="export-csv" className="block text-sm font-medium text-gray-700 mb-2">Экспорт CSV</label>
              <button
                id="export-csv"
                onClick={handleExport}
                className="flex items-center gap-2 px-4 py-2 text-sm text-green-600 border border-green-300 rounded-lg hover:bg-green-50"
              >
                <Upload className="w-4 h-4 rotate-180" />
                Скачать все контакты (CSV)
              </button>
            </div>
          </div>

          <div className="flex justify-end pt-4">
            <button onClick={onClose} className="px-4 py-2 text-sm border rounded-lg">Закрыть</button>
          </div>
        </Dialog.Panel>
      </div>
    </Dialog>
  )
}
