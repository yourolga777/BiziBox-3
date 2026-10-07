import { type ReactNode } from 'react'
import { Dialog } from '@headlessui/react'
import { X } from 'lucide-react'

interface ModalProps {
  open: boolean
  onClose: () => void
  title?: string
  children: ReactNode
  maxWidth?: string
}

function Modal({ open, onClose, title, children, maxWidth = 'max-w-lg' }: ModalProps) {
  return (
    <Dialog open={open} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className={`w-full ${maxWidth} bg-white rounded-xl shadow-xl max-h-[80vh] flex flex-col`}>
          {title && (
            <div className="flex items-center justify-between p-5 border-b border-gray-200">
              <Dialog.Title className="text-lg font-semibold text-gray-900">
                {title}
              </Dialog.Title>
              <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
                <X size={20} />
              </button>
            </div>
          )}
          <div className="flex-1 overflow-y-auto">
            {children}
          </div>
        </Dialog.Panel>
      </div>
    </Dialog>
  )
}

export default Modal
