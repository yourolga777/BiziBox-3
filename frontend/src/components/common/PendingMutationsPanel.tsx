import { useEffect, useRef, useState } from 'react'
import { RefreshCw, X, Clock, Trash2, Pencil, Check, Paperclip } from 'lucide-react'
import { getPending, discardPending, editPendingMessage, MUTATIONS_UPDATED } from '../../offline/queue'
import { invalidateAllEntityCaches } from '../../offline/sync'
import type { OfflineMutation } from '../../offline/db'

interface Props {
  onClose: () => void
}

function formatDate(ts: number): string {
  return new Date(ts).toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function isMessageSend(m: OfflineMutation): boolean {
  return m.method === 'POST' && m.path === '/messages/send'
}

function bodyContent(m: OfflineMutation): string | null {
  if (!m.body) return null
  if (isMessageSend(m)) {
    try {
      const parsed = JSON.parse(m.body)
      if (parsed && typeof parsed.content === 'string') return parsed.content
    } catch {
      return m.body
    }
  }
  return m.body
}

export default function PendingMutationsPanel({ onClose }: Props) {
  const [pending, setPending] = useState<OfflineMutation[]>([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editText, setEditText] = useState('')
  const overlayRef = useRef<HTMLDivElement>(null)
  const mouseDownTargetRef = useRef<EventTarget | null>(null)

  async function load() {
    setLoading(true)
    const items = await getPending()
    setPending(items)
    setLoading(false)
  }

  useEffect(() => {
    load()
    const handler = () => load()
    window.addEventListener(MUTATIONS_UPDATED, handler)

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)

    return () => {
      window.removeEventListener(MUTATIONS_UPDATED, handler)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [onClose])

  function startEdit(m: OfflineMutation) {
    setEditingId(m.id ?? null)
    setEditText(bodyContent(m) ?? '')
  }

  async function saveEdit(m: OfflineMutation) {
    const text = editText.trim()
    if (!text) return
    let newBody = m.body ?? ''
    if (isMessageSend(m)) {
      try {
        const parsed = JSON.parse(m.body ?? '{}')
        parsed.content = text
        newBody = JSON.stringify(parsed)
      } catch {
        newBody = m.body ?? ''
      }
    }
    await editPendingMessage(m.id!, newBody, m.localId, text)
    setEditingId(null)
    setEditText('')
    invalidateAllEntityCaches()
    await load()
  }

  async function handleDiscard(m: OfflineMutation) {
    await discardPending(m.id!, m.localId)
    invalidateAllEntityCaches()
    await load()
  }

  function handleOverlayMouseDown(e: React.MouseEvent) {
    mouseDownTargetRef.current = e.target
  }

  function handleOverlayMouseUp(e: React.MouseEvent) {
    if (e.target === overlayRef.current && mouseDownTargetRef.current === overlayRef.current) {
      onClose()
    }
    mouseDownTargetRef.current = null
  }

  return (
    // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions
    <div
      ref={overlayRef}
      role="dialog"
      aria-modal="true"
      aria-label="Ожидает отправки"
      className="fixed inset-0 z-50 flex items-start justify-center pt-16 bg-black/40"
      onMouseDown={handleOverlayMouseDown}
      onMouseUp={handleOverlayMouseUp}
    >
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <RefreshCw size={18} className="text-primary animate-spin" />
            <h2 className="text-base font-semibold text-gray-900">
              Ожидает отправки: {pending.length}
            </h2>
          </div>
          <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 text-gray-400">
            <X size={18} />
          </button>
        </div>

        <div className="overflow-y-auto flex-1 px-5 py-3 space-y-3">
          {loading && (
            <div className="text-sm text-gray-500 py-4 text-center">Загрузка...</div>
          )}
          {!loading && pending.length === 0 && (
            <div className="text-sm text-gray-500 py-4 text-center">Нет ожидающих отправки данных</div>
          )}
          {pending.map((m) => (
            <div key={m.id} className="rounded-lg border border-gray-200 p-3 text-sm space-y-1.5">
              <div className="flex items-center gap-1.5 text-gray-700 font-mono text-xs">
                <span className="px-1.5 py-0.5 bg-primary/10 text-primary rounded font-semibold">{m.method}</span>
                <span className="truncate text-gray-500">{m.path}</span>
              </div>
              {editingId === m.id ? (
                <div className="space-y-2">
                  <textarea
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    rows={3}
                    className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                    aria-label="Текст ожидающего сообщения"
                  />
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => saveEdit(m)}
                      className="flex items-center gap-1 px-2 py-1 text-xs text-white bg-primary rounded-lg hover:bg-primary/90"
                    >
                      <Check size={12} />
                      Сохранить
                    </button>
                    <button
                      type="button"
                      onClick={() => { setEditingId(null); setEditText('') }}
                      className="flex items-center gap-1 px-2 py-1 text-xs text-gray-600 hover:bg-gray-100 rounded-lg"
                    >
                      Отмена
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  {(m.files && m.files.length > 0) && (
                    <div className="flex items-center gap-1.5 text-gray-500 text-xs">
                      <Paperclip size={12} />
                      <span>Вложение ({m.files.length})</span>
                    </div>
                  )}
                  {m.body && (
                    <div className="text-gray-600 text-xs break-all">
                      {(bodyContent(m) ?? '').length > 200 ? bodyContent(m)!.slice(0, 200) + '…' : bodyContent(m)}
                    </div>
                  )}
                  <div className="flex items-center gap-1 text-gray-400 text-[10px]">
                    <Clock size={10} />
                    {m.createdAt ? formatDate(m.createdAt) : '—'}
                    {m.status === 'failed' && m.retry_count > 0 && (
                      <span className="text-amber-600"> · повторная попытка {m.retry_count}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 pt-1">
                    {isMessageSend(m) && (
                      <button
                        type="button"
                        onClick={() => startEdit(m)}
                        className="flex items-center gap-1 text-xs text-primary hover:underline"
                      >
                        <Pencil size={12} />
                        Изменить
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => handleDiscard(m)}
                      className="flex items-center gap-1 text-xs text-red-500 hover:underline"
                    >
                      <Trash2 size={12} />
                      Отменить
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
