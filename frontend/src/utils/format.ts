export function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null || bytes <= 0) return '0 Б'
  const units = ['Б', 'КБ', 'МБ', 'ГБ']
  const k = 1024
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  const value = bytes / k ** i
  return `${value.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

export function formatMoney(amount: number | null | undefined): string {
  if (amount == null || Number.isNaN(amount)) return '0 ₽'
  return `${amount.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 2 })} ₽`
}

/** Абсолютная дата и время: «29.09.2026, 14:30». */
export function formatDateTime(dateStr: string | null | undefined): string {
  const date = parseDateTime(dateStr)
  if (!date) return ''
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Абсолютная дата: «29.09.2026». */
export function formatDate(dateStr: string | null | undefined): string {
  const date = parseDateTime(dateStr)
  if (!date) return ''
  return date.toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

/** Парсит дату: наивные строки бэкенда (без таймзоны) считает UTC. */
export function parseDateTime(dateStr: string | null | undefined): Date | null {
  if (!dateStr) return null
  const trimmed = dateStr.trim()
  const date = /Z$|[+-]\d{2}:\d{2}$/.test(trimmed)
    ? new Date(trimmed)
    : new Date(trimmed + 'Z')
  return isNaN(date.getTime()) ? null : date
}

export function formatRelativeTime(dateStr: string | null | undefined, short?: boolean): string {
  const date = parseDateTime(dateStr)
  if (!date) return ''
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)

  if (minutes < 1) return 'только что'
  if (minutes < 60) {
    if (short) return `${minutes} мин. назад`
    return `${minutes} мин. назад`
  }

  if (short) {
    return date.toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
  }

  const isToday = now.toDateString() === date.toDateString()
  if (isToday) return date.toLocaleString('ru-RU', { hour: '2-digit', minute: '2-digit' })

  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  if (yesterday.toDateString() === date.toDateString()) return 'вчера'

  return date.toLocaleString('ru-RU', { day: 'numeric', month: 'short' })
}

export function formatDayLabel(dateStr: string | null | undefined): string {
  const date = parseDateTime(dateStr)
  if (!date) return 'Без даты'
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const thatDay = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const diffDays = Math.round((today.getTime() - thatDay.getTime()) / 86400000)
  if (diffDays === 0) return 'Сегодня'
  if (diffDays === 1) return 'Вчера'
  return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
}

/** Время последней загрузки канала: корректная дата + время. */
export function formatLastPolled(dateStr: string | null | undefined): string {
  if (!dateStr) return 'Не загружалось'
  const date = parseDateTime(dateStr)
  if (!date) return 'Не загружалось'
  const now = new Date()
  const time = date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
  if (now.toDateString() === date.toDateString()) return `сегодня в ${time}`
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  if (yesterday.toDateString() === date.toDateString()) return `вчера в ${time}`
  return date.toLocaleString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
