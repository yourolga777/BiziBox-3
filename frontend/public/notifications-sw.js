/* global self, clients */
self.addEventListener('push', (event) => {
  let data = { title: 'BiziBox', body: 'Новое уведомление' }
  try {
    const payload = event.data ? event.data.json() : null
    if (payload && payload.title) data = payload
  } catch {
    // payload не JSON — используем дефолтное уведомление
  }
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/icons/icon-192.png',
      badge: '/icons/icon-192.png',
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
      for (const client of list) {
        if ('focus' in client) return client.focus()
      }
      return clients.openWindow('/')
    }),
  )
})
