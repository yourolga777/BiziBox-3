import { useState, useEffect } from 'react'
import { Merge } from 'lucide-react'
import Card from '../common/Card'
import { contactApi } from '../../api/client'
import type { DuplicateGroup } from '../../types/contact'

export default function DuplicatePanel({
  onMerge,
}: {
  onMerge: (primaryId: number, secondaryIds: number[]) => Promise<void>
}) {
  const [duplicates, setDuplicates] = useState<DuplicateGroup[]>([])
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState<Set<number>>(new Set())

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    contactApi.getDuplicates().then(data => {
      if (!cancelled) {
        setDuplicates(data)
        setLoading(false)
      }
    }).catch(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [])

  if (loading) return null
  if (duplicates.length === 0) return null

  return (
    <Card title={`Возможные дубликаты (${duplicates.length})`}>
      <div className="space-y-3 max-h-60 overflow-y-auto">
        {duplicates.map((group, idx) => (
          <div key={idx} className="border border-gray-200 rounded-lg p-2">
            <button
              onClick={() => {
                const next = new Set(expanded)
                if (next.has(idx)) next.delete(idx)
                else next.add(idx)
                setExpanded(next)
              }}
              className="w-full text-left text-xs text-gray-500 mb-1"
            >
              {group.reason}
            </button>
            {expanded.has(idx) && (
              <div className="space-y-1">
                {group.contacts.map(c => (
                  <div key={c.id} className="text-sm text-gray-700 px-2">
                    {c.name || 'Без имени'}
                    {c.phone && ` · ${c.phone}`}
                    {c.email && ` · ${c.email}`}
                  </div>
                ))}
                <button
                  onClick={async () => {
                    const ids = group.contacts.map(c => c.id)
                    await onMerge(ids[0], ids.slice(1))
                    setDuplicates(prev => prev.filter((_, i) => i !== idx))
                  }}
                  className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50 rounded"
                >
                  <Merge className="w-3 h-3" />
                  Объединить все
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </Card>
  )
}
