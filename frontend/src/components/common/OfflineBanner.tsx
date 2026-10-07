import { useEffect, useState } from 'react'
import { Wifi, WifiOff } from 'lucide-react'
import { useOnlineStatus } from '../../hooks/useOnlineStatus'
import { useToast } from './Toast'
import { getCount, getFailed } from '../../offline/queue'
import { SYNC_COMPLETE, processQueue, type SyncResult } from '../../offline/sync'
import { MUTATIONS_UPDATED } from '../../offline/queue'
import type { OfflineMutation } from '../../offline/db'

function OfflineBanner() {
  const online = useOnlineStatus()
  const { showToast } = useToast()
  const [pendingCount, setPendingCount] = useState(0)
  const [failedMuts, setFailedMuts] = useState<OfflineMutation[]>([])

  useEffect(() => {
    const refresh = () => {
      getCount().then(setPendingCount).catch(() => {})
      getFailed().then(setFailedMuts).catch(() => {})
    }
    refresh()

    window.addEventListener(MUTATIONS_UPDATED, refresh)
    return () => window.removeEventListener(MUTATIONS_UPDATED, refresh)
  }, [])

  useEffect(() => {
    if (!online) return

    const handleSyncComplete = (e: Event) => {
      const detail = (e as CustomEvent<SyncResult>).detail
      if (!detail) return

      getCount().then(setPendingCount).catch(() => {})
      getFailed().then(setFailedMuts).catch(() => {})

      if (detail.total === 0) return

      if (detail.failed === 0) {
        showToast(`✓ Отправлено ${detail.synced} из ${detail.total}`, 'success')
      } else {
        showToast(`Отправлено ${detail.synced} из ${detail.total}. Осталось ждать: ${detail.failed}. Попробуйте позднее.`, 'info')
      }
    }

    window.addEventListener(SYNC_COMPLETE, handleSyncComplete)
    return () => window.removeEventListener(SYNC_COMPLETE, handleSyncComplete)
  }, [online, showToast])

  // Авто-отправка по таймеру: пока есть ожидающие — пробуем каждые 15 секунд.
  useEffect(() => {
    if (!online) return
    const timer = setInterval(() => {
      processQueue()
    }, 15_000)
    return () => clearInterval(timer)
  }, [online])

  if (online && pendingCount === 0 && failedMuts.length === 0) return null

  if (!online) {
    return (
      <div className="flex items-center justify-center gap-2 bg-amber-500 text-white text-sm font-medium px-4 py-2">
        <WifiOff size={16} />
        <span>Оффлайн-режим</span>
        {pendingCount > 0 && (
          <span className="bg-amber-600 px-2 py-0.5 rounded-full text-xs">
            Ожидает: {pendingCount}
          </span>
        )}
      </div>
    )
  }

  return (
    <button
      type="button"
      onClick={() => processQueue()}
      className="flex items-center justify-center gap-2 bg-amber-500 text-white text-sm font-medium px-4 py-2 w-full cursor-pointer hover:bg-amber-600"
    >
      <Wifi size={16} />
      <span>Сообщения ожидают отправки ({pendingCount + failedMuts.length}) — отправятся автоматически, либо нажмите для повторной отправки</span>
    </button>
  )
}

export default OfflineBanner
