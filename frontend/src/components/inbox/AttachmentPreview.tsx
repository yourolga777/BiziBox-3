import { useState } from 'react'
import { Dialog } from '@headlessui/react'
import { FileText, Download, ExternalLink, X, FileImage } from 'lucide-react'
import { getAttachmentDownloadUrl } from '../../api/messages'
import { formatBytes } from '../../utils/format'
import type { MessageAttachment } from '../../types/message'

interface AttachmentPreviewProps {
  messageId: number
  attachment: MessageAttachment
  isOpen: boolean
  onClose: () => void
}

export default function AttachmentPreview({ messageId, attachment, isOpen, onClose }: AttachmentPreviewProps) {
  const [imageError, setImageError] = useState(false)
  const downloadUrl = getAttachmentDownloadUrl(messageId, attachment.id)
  const isImage = !imageError && attachment.mime_type?.startsWith('image/')
  const isAudio = attachment.mime_type?.startsWith('audio/')
  const isVideo = attachment.mime_type?.startsWith('video/')
  const isPdf = attachment.mime_type === 'application/pdf'
  const fileName = attachment.file_name || `attachment_${attachment.id}`

  return (
    <Dialog open={isOpen} onClose={onClose} className="relative z-[60]">
      <div className="fixed inset-0 bg-black/60" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <Dialog.Title className="text-sm font-medium text-gray-900 truncate pr-4">
              {fileName}
            </Dialog.Title>
            <button
              type="button"
              onClick={onClose}
              className="p-1 text-gray-400 hover:text-gray-600 rounded"
              aria-label="Закрыть"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-gray-50 min-h-[200px]">
            {isImage ? (
              <img
                src={downloadUrl}
                alt={fileName}
                className="max-w-full max-h-[50vh] object-contain rounded-lg shadow-sm"
                onError={() => setImageError(true)}
              />
            ) : isAudio ? (
              <div className="w-full max-w-md">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-white border border-gray-200 shadow-sm mx-auto">
                  <FileImage className="w-8 h-8 text-gray-400" />
                </div>
                <div className="mt-4 text-center">
                  <p className="text-sm font-medium text-gray-900 truncate">{fileName}</p>
                  {attachment.file_size != null && (
                    <p className="text-xs text-gray-500">{formatBytes(attachment.file_size)}</p>
                  )}
                </div>
                <audio controls src={downloadUrl} className="w-full mt-4" preload="metadata">
                  <track kind="captions" />
                </audio>
              </div>
            ) : isVideo ? (
              <div className="w-full max-w-lg">
                <video controls src={downloadUrl} className="w-full max-h-[50vh] rounded-lg shadow-sm" preload="metadata">
                  <track kind="captions" />
                </video>
                <div className="mt-2 text-center">
                  <p className="text-sm font-medium text-gray-900 truncate">{fileName}</p>
                  {attachment.file_size != null && (
                    <p className="text-xs text-gray-500">{formatBytes(attachment.file_size)}</p>
                  )}
                </div>
              </div>
            ) : isPdf ? (
              <iframe
                src={downloadUrl}
                title={fileName}
                className="w-full h-[60vh] rounded-lg shadow-sm border border-gray-200 bg-white"
              />
            ) : (
              <div className="text-center space-y-3">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-white border border-gray-200 shadow-sm">
                  {attachment.mime_type?.startsWith('image/') ? (
                    <FileImage className="w-8 h-8 text-gray-400" />
                  ) : (
                    <FileText className="w-8 h-8 text-gray-400" />
                  )}
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900">{fileName}</p>
                  {attachment.file_size != null && (
                    <p className="text-xs text-gray-500">{formatBytes(attachment.file_size)}</p>
                  )}
                  {attachment.mime_type && (
                    <p className="text-xs text-gray-400">{attachment.mime_type}</p>
                  )}
                </div>
                <p className="text-xs text-gray-400">Предпросмотр недоступен</p>
              </div>
            )}
          </div>

          <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-gray-100">
            <a
              href={downloadUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Открыть
            </a>
            <a
              href={downloadUrl}
              download={fileName}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
            >
              <Download className="w-3.5 h-3.5" />
              Сохранить
            </a>
          </div>
        </Dialog.Panel>
      </div>
    </Dialog>
  )
}
