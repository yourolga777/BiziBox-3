import { useEffect, useState, useCallback } from 'react'
import { RefreshCw, CloudOff, CheckCircle2, AlertTriangle, PauseCircle } from 'lucide-react'
import { getCount, getFailed, getPaused, MUTATIONS_UPDATED } from '../../offline/queue'
import { useOnlineStatus } from '../../hooks/useOnlineStatus'
import FailedMutationsPanel from './FailedMutationsPanel'
import PendingMutationsPanel from './PendingMutationsPanel'

type SyncState = 'synced' | 'pending' | 'syncing' | 'offline'

function SyncBadge() {
  const online = useOnlineStatus()
  const [state, setState] = useState<SyncState>('synced')
  const [pendingCount, setPendingCount] = useState(0)
  const [failedCount, setFailedCount] = useState(0)
  const [pausedCount, setPausedCount] = useState(0)
  const [showPanel, setShowPanel] = useState(false)
  const [showPendingPanel, setShowPendingPanel] = useState(false)

  const update = useCallback(async () => {
    const count = await getCount()
    setPendingCount(count)
    const failed = await getFailed()
    setFailedCount(failed.length)
    const paused = await getPaused()
    setPausedCount(paused.length)
    if (!online) {
      setState('offline')
    } else if (count > 0) {
      setState('pending')
    } else if (failed.length > 0) {
      setState('synced')
    } else {
      setState('synced')
    }
  }, [online])

  useEffect(() => {
    update()
    window.addEventListener(MUTATIONS_UPDATED, update)
    return () => window.removeEventListener(MUTATIONS_UPDATED, update)
  }, [update])

  if (state === 'synced' && failedCount === 0 && pausedCount === 0 && online) return null

  return (
    <>
      <div className="flex items-center gap-2">
        {failedCount > 0 && (
          <button
            onClick={() => setShowPanel(true)}
            className="flex items-center gap-1.5 text-xs text-amber-600 bg-amber-50 px-2.5 py-1 rounded-full hover:bg-amber-100 transition-colors cursor-pointer"
          >
            <AlertTriangle size={12} />
            <span>Ошибки: {failedCount}</span>
          </button>
        )}
        {pausedCount > 0 && (
          <button
            onClick={() => setShowPanel(true)}
            className="flex items-center gap-1.5 text-xs text-gray-600 bg-gray-100 px-2.5 py-1 rounded-full hover:bg-gray-200 transition-colors cursor-pointer"
          >
            <PauseCircle size={12} />
            <span>Пауза: {pausedCount}</span>
          </button>
        )}
        {state === 'offline' && (
          <div className="flex items-center gap-1.5 text-xs text-amber-600 bg-amber-50 px-2.5 py-1 rounded-full">
            <CloudOff size={12} />
            <span>Офлайн</span>
          </div>
        )}
        {state === 'pending' && (
          <button
            onClick={() => setShowPendingPanel(true)}
            className="flex items-center gap-1.5 text-xs text-primary bg-primary/10 px-2.5 py-1 rounded-full hover:bg-primary/20 transition-colors cursor-pointer"
          >
            <RefreshCw size={12} className="animate-spin" />
            <span>Ожидает: {pendingCount}</span>
          </button>
        )}
        {state === 'synced' && !online && (
          <div className="flex items-center gap-1.5 text-xs text-green-600 bg-green-50 px-2.5 py-1 rounded-full">
            <CheckCircle2 size={12} />
            <span>Синхронизировано</span>
          </div>
        )}
      </div>
      {showPanel && <FailedMutationsPanel onClose={() => { setShowPanel(false); update() }} />}
      {showPendingPanel && <PendingMutationsPanel onClose={() => { setShowPendingPanel(false); update() }} />}
    </>
  )
}

export default SyncBadge
