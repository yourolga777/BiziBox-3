import { forwardRef, useEffect, useMemo, useRef, useState } from 'react'
import { Paperclip, Download, Copy, Reply, CheckCircle, CalendarPlus, Trash2, Forward, PackagePlus } from 'lucide-react'
import { formatRelativeTime, formatBytes, formatDayLabel } from '../../utils/format'
import { autolinkText } from '../../utils/autolink'
import { useToast } from '../common/Toast'
import { getChannelIcon } from '../../utils/channelIcons'
import AttachmentPreview from './AttachmentPreview'
import type { Message } from '../../types/message'
import type { MessageAttachment } from '../../types/message'

interface DayGroup {
  label: string
  messages: Message[]
}

function groupByDay(messages: Message[]): DayGroup[] {
  const groups: DayGroup[] = []
  for (const msg of messages) {
    const label = formatDayLabel(msg.created_at)
    const last = groups[groups.length - 1]
    if (last && last.label === label) {
      last.messages.push(msg)
    } else {
      groups.push({ label, messages: [msg] })
    }
  }
  return groups
}

interface ThreadListProps {
  messages: Message[]
  hasMore?: boolean
  loadingMore?: boolean
  onLoadMore?: () => void
  onReply?: (message: Message) => void
  onCreateTask?: (message: Message) => void
  onCreateEvent?: (message: Message) => void
  onCreateOrder?: (message: Message) => void
  onDeleteMessage?: (message: Message) => void
  onForward?: (message: Message) => void
}

interface ContextMenuState {
  x: number
  y: number
  message: Message
}

export const ThreadList = forwardRef<HTMLDivElement, ThreadListProps>(
  ({ messages, hasMore, loadingMore, onLoadMore, onReply, onCreateTask, onCreateEvent, onCreateOrder, onDeleteMessage, onForward }, ref) => {
    const [preview, setPreview] = useState<{ messageId: number; attachment: MessageAttachment } | null>(null)
    const [menu, setMenu] = useState<ContextMenuState | null>(null)
    const menuRef = useRef<HTMLDivElement>(null)
    const bubbleRefs = useRef<Record<number, HTMLDivElement | null>>({})
    const { showToast } = useToast()
    const groups = useMemo(() => groupByDay(messages), [messages])

    const replyTargets = useMemo(() => {
      const byChannelMsg = new Map<string, Message>()
      for (const m of messages) {
        if (m.channel_message_id) byChannelMsg.set(m.channel_message_id, m)
      }
      const targets: Record<number, Message | undefined> = {}
      for (const m of messages) {
        targets[m.id] = m.reply_to ? byChannelMsg.get(m.reply_to) : undefined
      }
      return targets
    }, [messages])

    const scrollToReply = (msg: Message) => {
      const target = replyTargets[msg.id]
      if (!target) return
      const el = bubbleRefs.current[target.id]
      if (!el) return
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      el.classList.remove('reply-flash')
      void el.offsetWidth
      el.classList.add('reply-flash')
      window.setTimeout(() => el.classList.remove('reply-flash'), 1400)
    }

    useEffect(() => {
      if (!menu) return
      const close = (e: Event) => {
        if (menuRef.current && e.target instanceof Node && menuRef.current.contains(e.target)) return
        setMenu(null)
      }
      window.addEventListener('mousedown', close)
      window.addEventListener('scroll', close, true)
      window.addEventListener('resize', close)
      return () => {
        window.removeEventListener('mousedown', close)
        window.removeEventListener('scroll', close, true)
        window.removeEventListener('resize', close)
      }
    }, [menu])

    const handleContextMenu = (e: React.MouseEvent, msg: Message) => {
      e.preventDefault()
      setMenu({ x: e.clientX, y: e.clientY, message: msg })
    }

    const handleCopy = async (msg: Message) => {
      setMenu(null)
      try {
        await navigator.clipboard.writeText(msg.content)
        showToast('Скопировано', 'success')
      } catch {
        showToast('Не удалось скопировать', 'error')
      }
    }

    const handleReply = (msg: Message) => {
      setMenu(null)
      onReply?.(msg)
    }

    const handleCreateTask = (msg: Message) => {
      setMenu(null)
      onCreateTask?.(msg)
    }

  const handleCreateEvent = (msg: Message) => {
    setMenu(null)
    onCreateEvent?.(msg)
  }

  const handleCreateOrder = (msg: Message) => {
    setMenu(null)
    onCreateOrder?.(msg)
  }

    const handleDeleteMessage = (msg: Message) => {
      setMenu(null)
      onDeleteMessage?.(msg)
    }

    const handleForward = (msg: Message) => {
      setMenu(null)
      onForward?.(msg)
    }

    if (messages.length === 0) {
      return (
        <div className="flex-1 min-h-0 overflow-y-auto p-4">
          <p className="text-gray-400 text-center py-8">Нет сообщений в этой переписке</p>
        </div>
      )
    }

    return (
      <div className="flex-1 min-h-0 overflow-y-auto p-4">
        {hasMore && (
          <div className="flex justify-center mb-3">
            <button
              type="button"
              onClick={onLoadMore}
              disabled={loadingMore}
              className="px-4 py-1.5 text-xs font-medium text-primary bg-blue-50 border border-blue-200 rounded-full hover:bg-blue-100 disabled:opacity-50 transition-colors"
            >
              {loadingMore ? 'Загрузка...' : 'Загрузить ещё 10'}
            </button>
          </div>
        )}
        {groups.map((group) => (
          <div key={group.label}>
            <div className="flex items-center justify-center my-3">
              <span className="px-3 py-1 rounded-full bg-gray-100 text-xs text-gray-500">
                {group.label}
              </span>
            </div>
            <div className="space-y-3">
              {group.messages.map(msg => (
                <div key={msg.id}>
                  <div
                    className={`flex ${msg.direction === 'outgoing' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      ref={(el) => {
                        bubbleRefs.current[msg.id] = el
                      }}
                      onContextMenu={(e) => handleContextMenu(e, msg)}
                      className={`max-w-[75%] px-4 py-2.5 rounded-2xl ${
                        msg.direction === 'outgoing'
                          ? 'bg-primary text-white rounded-br-sm'
                          : 'bg-gray-100 text-gray-900 rounded-bl-sm'
                      }`}
                    >
                      {msg.reply_to && (
                        <button
                          type="button"
                          onClick={() => scrollToReply(msg)}
                          className={`block mb-1.5 w-full max-w-[220px] text-left rounded-lg px-2 py-1 text-[11px] leading-snug border truncate transition-colors ${
                            msg.direction === 'outgoing'
                              ? 'bg-white/15 border-white/20 text-white/90 hover:bg-white/25'
                              : 'bg-white/70 border-gray-200 text-gray-600 hover:bg-white'
                          }`}
                          title={
                            replyTargets[msg.id]
                              ? 'Показать сообщение, на которое отвечали'
                              : 'Сообщение, на которое отвечали, ещё не загружено'
                          }
                        >
                          <span className="font-semibold">Ответ на:</span>{' '}
                          {replyTargets[msg.id]
                            ? (replyTargets[msg.id]!.content || 'Вложение').slice(0, 60)
                            : 'сообщение'}
                        </button>
                      )}
                      <div className="flex items-center gap-1.5 mb-0.5">
                        {(() => {
                          const ChannelIcon = getChannelIcon(msg.channel)
                          return (
                            <ChannelIcon
                              className={`w-3 h-3 shrink-0 ${msg.direction === 'outgoing' ? 'text-white/70' : 'text-gray-400'}`}
                            />
                          )
                        })()}
                        <span className={`text-[10px] uppercase tracking-wide ${msg.direction === 'outgoing' ? 'text-white/60' : 'text-gray-400'}`}>
                          {msg.channel}
                        </span>
                      </div>
                      {msg.subject && (
                        <p className="text-sm font-semibold mb-0.5 break-words">
                          {msg.subject}
                        </p>
                      )}
                      {msg.content_html ? (
                        <p
                          className="text-sm whitespace-pre-wrap break-words"
                          dangerouslySetInnerHTML={{ __html: msg.content_html }}
                        />
                      ) : (
                        <p
                          className="text-sm whitespace-pre-wrap break-words"
                          dangerouslySetInnerHTML={{ __html: autolinkText(msg.content) }}
                        />
                      )}
                      {(msg.attachments ?? []).map(att => (
                        <button
                          key={att.id}
                          type="button"
                          onClick={() => setPreview({ messageId: msg.id, attachment: att })}
                          className={`mt-1 flex items-center gap-1.5 text-xs text-left rounded px-1.5 py-0.5 -ml-1.5 transition-colors ${
                            msg.direction === 'outgoing'
                              ? 'text-white/90 hover:bg-white/10'
                              : 'text-primary hover:bg-blue-50'
                          }`}
                          title="Открыть вложение"
                        >
                          <Paperclip className="w-3 h-3 shrink-0" />
                          <span className="truncate max-w-[180px]">{att.file_name || 'Вложение'}</span>
                          {att.file_size != null && (
                            <span className="opacity-70">({formatBytes(att.file_size)})</span>
                          )}
                          <Download className="w-3 h-3 shrink-0 opacity-70" />
                        </button>
                      ))}
                      <p className={`text-xs mt-1 ${msg.direction === 'outgoing' ? 'text-white/70' : 'text-gray-400'}`}>
                        {formatRelativeTime(msg.created_at, true)}
                        {msg.status === 'read' && msg.direction === 'outgoing' && msg.channel_message_id && ' ✓✓'}
                        {msg.direction === 'outgoing' && !msg.channel_message_id && ' ⏳ ожидает отправки'}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
        <div ref={ref} />
        <AttachmentPreviewDialog preview={preview} onClose={() => setPreview(null)} />

        {menu && (
          <div
            ref={menuRef}
            className="fixed z-[70] min-w-[180px] bg-white border border-gray-200 rounded-xl shadow-lg py-1"
            style={{ left: menu.x, top: menu.y }}
            onContextMenu={(e) => e.preventDefault()}
          >
            <button
              type="button"
              onClick={() => handleCopy(menu.message)}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 text-left"
            >
              <Copy className="w-4 h-4 text-gray-400" />
              Скопировать
            </button>
            {onReply && (
              <button
                type="button"
                onClick={() => handleReply(menu.message)}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 text-left"
              >
                <Reply className="w-4 h-4 text-gray-400" />
                Ответить
              </button>
            )}
            {onForward && (
              <button
                type="button"
                onClick={() => handleForward(menu.message)}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 text-left"
              >
                <Forward className="w-4 h-4 text-gray-400" />
                Переслать
              </button>
            )}
            {onCreateTask && (
              <button
                type="button"
                onClick={() => handleCreateTask(menu.message)}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 text-left"
              >
                <CheckCircle className="w-4 h-4 text-purple-400" />
                Создать задачу
              </button>
            )}
            {onCreateOrder && (
              <button
                type="button"
                onClick={() => handleCreateOrder(menu.message)}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 text-left"
              >
                <PackagePlus className="w-4 h-4 text-orange-400" />
                Создать заказ
              </button>
            )}
            {onCreateEvent && (
              <button
                type="button"
                onClick={() => handleCreateEvent(menu.message)}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 text-left"
              >
                <CalendarPlus className="w-4 h-4 text-indigo-400" />
                Создать событие
              </button>
            )}
            {onDeleteMessage && (
              <button
                type="button"
                onClick={() => handleDeleteMessage(menu.message)}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 text-left"
              >
                <Trash2 className="w-4 h-4 text-red-400" />
                Удалить сообщение
              </button>
            )}
          </div>
        )}
      </div>
    )
  },
)

function AttachmentPreviewDialog({
  preview,
  onClose,
}: {
  preview: { messageId: number; attachment: MessageAttachment } | null
  onClose: () => void
}) {
  if (!preview) return null
  return (
    <AttachmentPreview
      messageId={preview.messageId}
      attachment={preview.attachment}
      isOpen
      onClose={onClose}
    />
  )
}

ThreadList.displayName = 'ThreadList'
