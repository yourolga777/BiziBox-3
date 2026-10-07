import { useEffect, useState } from 'react'
import { messageApi } from '../../api/client'

const cache = new Map<number, string>()

interface MessagePreviewProps {
  messageId: number
  className?: string
}

export default function MessagePreview({ messageId, className }: MessagePreviewProps) {
  const [text, setText] = useState<string | null>(cache.get(messageId) ?? null)

  useEffect(() => {
    if (text !== null) return
    let alive = true
    messageApi.getById(messageId)
      .then((m) => {
        if (!alive) return
        cache.set(messageId, m.content)
        setText(m.content)
      })
      .catch(() => { /* сообщение недоступно — скрываем превью */ })
    return () => { alive = false }
  }, [messageId, text])

  if (!text) return null
  return <p className={className ?? 'text-xs text-gray-400 mt-1 line-clamp-2 italic'}>{text}</p>
}