export type NotificationPermissionState = 'granted' | 'denied' | 'default' | 'unsupported'

const SW_PATH = '/notifications-sw.js'

export function isPushSupported(): boolean {
  return (
    typeof navigator !== 'undefined' &&
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  )
}

export function getNotificationPermission(): NotificationPermissionState {
  if (!('Notification' in window)) return 'unsupported'
  return Notification.permission as NotificationPermissionState
}

/** Запрашивает разрешение на уведомления. Вызывается только по явному действию пользователя. */
export async function requestNotificationPermission(): Promise<NotificationPermissionState> {
  if (!isPushSupported()) return 'unsupported'
  try {
    const permission = await Notification.requestPermission()
    return permission as NotificationPermissionState
  } catch {
    return 'denied'
  }
}

/** Регистрирует notification SW и подписывается на push. */
export async function subscribeToPush(): Promise<PushSubscription | null> {
  if (!isPushSupported()) return null
  try {
    const registration = await navigator.serviceWorker.register(SW_PATH, { scope: '/' })
    await navigator.serviceWorker.ready
    const existing = await registration.pushManager.getSubscription()
    if (existing) return existing
    return await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(import.meta.env.VITE_VAPID_PUBLIC_KEY ?? ''),
    })
  } catch {
    return null
  }
}

function urlBase64ToUint8Array(base64String: string): Uint8Array<ArrayBuffer> | undefined {
  if (!base64String) return undefined
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = atob(base64)
  const outputArray = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; i++) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}
