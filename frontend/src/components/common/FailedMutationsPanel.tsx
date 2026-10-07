import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, PauseCircle, RefreshCw, Trash2, X, Copy, Check, RotateCcw } from 'lucide-react'
import { getFailed, getPaused, retryFailed, discardFailed, resetMutationsForRetry, clearMutations, MUTATIONS_UPDATED } from '../../offline/queue'
import { processQueue } from '../../offline/sync'
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

export default function FailedMutationsPanel({ onClose }: Props) {
  const [failed, setFailed] = useState<OfflineMutation[]>([])
  const [paused, setPaused] = useState<OfflineMutation[]>([])
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)
  const overlayRef = useRef<HTMLDivElement>(null)
  const mouseDownTargetRef = useRef<EventTarget | null>(null)

  async function load() {
    setLoading(true)
    const [failedItems, pausedItems] = await Promise.all([getFailed(), getPaused()])
    setFailed(failedItems)
    setPaused(pausedItems)
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

  async function handleRetry(id: number) {
    await retryFailed(id)
    await load()
  }

  async function handleDiscard(id: number) {
    await discardFailed(id)
    await load()
  }

  async function handleRetryAll() {
    await resetMutationsForRetry()
    await load()
    await processQueue()
  }

  async function handleClearAll() {
    await clearMutations()
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

  async function handleCopyAll() {
    const lines: string[] = []
    if (paused.length > 0) {
      lines.push('На паузе:')
      paused.forEach((m) => {
        lines.push(`[${m.method}] ${m.path} — ${m.error || ''}`)
        if (m.body) lines.push(m.body)
      })
    }
    if (failed.length > 0) {
      lines.push('Ошибки:')
      failed.forEach((m) => {
        lines.push(`[${m.method}] ${m.path} — ${m.error || ''}`)
        if (m.body) lines.push(m.body)
      })
    }
    const text = lines.join('\n')
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback
    }
  }

  const total = failed.length + paused.length

  function renderMutation(m: OfflineMutation, isPaused: boolean) {
    return (
      <div key={m.id} className="rounded-lg border border-gray-200 p-3 text-sm space-y-1.5">
        <div className="flex items-center gap-1.5 text-gray-700 font-mono text-xs">
          <span className="px-1.5 py-0.5 bg-gray-100 rounded font-semibold">{m.method}</span>
          <span className="truncate text-gray-500">{m.path}</span>
          {isPaused && (
            <span className="flex items-center gap-1 px-1.5 py-0.5 bg-gray-200 rounded text-gray-600 text-[10px]">
              <PauseCircle size={10} />
              пауза
            </span>
          )}
        </div>
        {m.error && (
          <div className={`text-xs rounded px-2 py-1 truncate ${isPaused ? 'text-gray-600 bg-gray-50' : 'text-red-600 bg-red-50'}`}>
            {m.error}
          </div>
        )}
        {!isPaused && m.retry_count >= 999 && (
          <div className="text-[10px] text-gray-400">повтор не выполняется автоматически</div>
        )}
        {m.body && (
          <div className="text-gray-400 text-xs truncate">
            {m.body.length > 80 ? m.body.slice(0, 80) + '…' : m.body}
          </div>
        )}
        {m.createdAt && (
          <div className="text-gray-400 text-[10px]">{formatDate(m.createdAt)}</div>
        )}
        <div className="flex items-center gap-2 pt-1">
          <button
            type="button"
            onClick={() => handleRetry(m.id!)}
            className="flex items-center gap-1 text-xs text-primary hover:underline"
          >
            <RefreshCw size={12} />
            Повторить
          </button>
          <button
            type="button"
            onClick={() => handleDiscard(m.id!)}
            className="flex items-center gap-1 text-xs text-red-500 hover:underline"
          >
            <Trash2 size={12} />
            Отбросить
          </button>
        </div>
      </div>
    )
  }

  return (
    // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions
    <div
      ref={overlayRef}
      role="dialog"
      aria-modal="true"
      aria-label="Ошибки синхронизации"
      className="fixed inset-0 z-50 flex items-start justify-center pt-16 bg-black/40"
      onMouseDown={handleOverlayMouseDown}
      onMouseUp={handleOverlayMouseUp}
    >
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            {failed.length > 0 ? <AlertTriangle size={18} className="text-amber-500" /> : <PauseCircle size={18} className="text-gray-400" />}
            <h2 className="text-base font-semibold text-gray-900">
              Не синхронизировано: {total}
            </h2>
          </div>
          <div className="flex items-center gap-1">
            {total > 0 && (
              <>
                <button
                  type="button"
                  onClick={handleRetryAll}
                  className="flex items-center gap-1 px-2 py-1 text-xs text-primary hover:bg-primary/10 rounded-lg"
                  title="Переотправить все"
                >
                  <RotateCcw size={14} />
                  Повторить всё
                </button>
                <button
                  type="button"
                  onClick={handleClearAll}
                  className="flex items-center gap-1 px-2 py-1 text-xs text-red-500 hover:bg-red-50 rounded-lg"
                  title="Удалить все ошибки"
                >
                  <Trash2 size={14} />
                  Очистить всё
                </button>
              </>
            )}
            <button
              type="button"
              onClick={handleCopyAll}
              className="flex items-center gap-1 px-2 py-1 text-xs text-gray-600 hover:bg-gray-100 rounded-lg"
              title="Скопировать всё"
            >
              {copied ? <Check size={14} className="text-green-600" /> : <Copy size={14} />}
              {copied ? 'Скопировано' : 'Копировать'}
            </button>
            <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 text-gray-400">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="overflow-y-auto flex-1 px-5 py-3 space-y-3">
          {loading && (
            <div className="text-sm text-gray-500 py-4 text-center">Загрузка...</div>
          )}
          {!loading && total === 0 && (
            <div className="text-sm text-gray-500 py-4 text-center">Нет ошибок синхронизации</div>
          )}
          {paused.map((m) => renderMutation(m, true))}
          {failed.map((m) => renderMutation(m, false))}
        </div>
      </div>
    </div>
  )
}
