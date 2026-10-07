import { useRef } from 'react'
import { Send, Paperclip, X, Reply } from 'lucide-react'
import Button from '../common/Button'
import type { Message } from '../../types/message'

function truncate(content: string, max = 60): string {
  const oneLine = content.replace(/\s+/g, ' ').trim()
  return oneLine.length > max ? oneLine.slice(0, max) + '…' : oneLine
}

export interface RecipientOption {
  value: string
  label: string
}

export default function ReplyBar({
  text, sending, error, replyTarget, attachments,
  onTextChange, onSend, onKeyDown, onAttachmentsChange, onCancelReply, inputRef,
  recipientOptions, recipientValue, onRecipientChange,
}: {
  text: string; sending: boolean; error: string | null
  replyTarget: Message | null
  attachments: File[]
  onTextChange: (v: string) => void
  onSend: () => void
  onKeyDown: (e: React.KeyboardEvent) => void
  onAttachmentsChange: (files: File[]) => void
  onCancelReply: () => void
  inputRef?: React.RefObject<HTMLInputElement | null>
  recipientOptions?: RecipientOption[]
  recipientValue?: string
  onRecipientChange?: (v: string) => void
}) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const canSend = sending || (!text.trim() && attachments.length === 0)

  const handleFiles = (list: FileList | null) => {
    if (!list || list.length === 0) return
    onAttachmentsChange([...attachments, ...Array.from(list)])
  }

  return (
    <div className="shrink-0 border-t border-gray-200 p-4">
      {replyTarget && (
        <div className="flex items-center gap-2 mb-2 px-3 py-1.5 bg-blue-50 border-l-2 border-blue-400 rounded text-xs text-gray-600">
          <Reply className="w-3.5 h-3.5 text-blue-500 shrink-0" />
          <span className="truncate">
            Ответ на: {replyTarget.content ? truncate(replyTarget.content) : 'вложение'}
          </span>
          <button
            type="button"
            onClick={onCancelReply}
            className="ml-auto shrink-0 text-gray-400 hover:text-gray-600"
            title="Отменить ответ"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2">
          {attachments.map((file, i) => (
            <span key={`${file.name}-${i}`} className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 rounded text-xs text-gray-700">
              <Paperclip className="w-3 h-3 text-gray-400" />
              <span className="max-w-[140px] truncate">{file.name}</span>
              <button
                type="button"
                onClick={() => onAttachmentsChange(attachments.filter((_, idx) => idx !== i))}
                className="text-gray-400 hover:text-red-500"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      {(recipientOptions?.length ?? 0) > 1 && onRecipientChange && (
        <div className="flex items-center gap-2 mb-2">
          <label htmlFor="recipient-select" className="text-xs text-gray-500 shrink-0">Получатель:</label>
          <select
            id="recipient-select"
            value={recipientValue ?? ''}
            onChange={e => onRecipientChange(e.target.value)}
            className="px-2 py-1 text-xs border border-gray-200 rounded-lg bg-gray-50 outline-none focus:border-primary max-w-[320px] truncate"
          >
            <option value="">По умолчанию (адрес контакта)</option>
            {recipientOptions?.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="shrink-0 p-2 rounded-xl border border-gray-200 text-gray-400 hover:text-primary hover:border-primary transition-colors"
          title="Прикрепить файл"
        >
          <Paperclip className="w-4 h-4" />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => { handleFiles(e.target.files); e.target.value = '' }}
        />
        <input
          ref={inputRef}
          type="text"
          value={text}
          onChange={e => onTextChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Написать сообщение..."
          className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 bg-gray-50 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors"
        />
        <Button
          onClick={onSend}
          disabled={canSend}
        >
          <Send className="w-4 h-4 mr-1" />
          {sending ? 'Отправка...' : 'Отправить'}
        </Button>
      </div>
      {error && (
        <p className="text-sm text-red-500 mt-2">{error}</p>
      )}
    </div>
  )
}
