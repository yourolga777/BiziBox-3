import { useState, useMemo } from 'react'
import { Dialog } from '@headlessui/react'
import { Search, X, LayoutDashboard, Inbox, Users, Calendar, ListTodo, Radio, Archive, Settings, WifiOff, HelpCircle } from 'lucide-react'
import { instructions, type InstructionItem } from '../../data/instructions'
import type { LucideIcon } from 'lucide-react'

const iconMap: Record<string, LucideIcon> = {
  LayoutDashboard,
  Inbox,
  Users,
  Calendar,
  ListTodo,
  Radio,
  Archive,
  Settings,
  WifiOff,
  HelpCircle,
}

interface InstructionsModalProps {
  open: boolean
  onClose: () => void
}

function InstructionsModal({ open, onClose }: InstructionsModalProps) {
  const [searchQuery, setSearchQuery] = useState('')

  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return instructions
    const q = searchQuery.toLowerCase()
    return instructions.filter(
      (item: InstructionItem) =>
        item.label.toLowerCase().includes(q) ||
        item.intro.toLowerCase().includes(q) ||
        item.steps.some((s) => s.toLowerCase().includes(q)),
    )
  }, [searchQuery])

  return (
    <Dialog open={open} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="w-full max-w-lg bg-white rounded-xl shadow-xl max-h-[80vh] flex flex-col">
          <div className="flex items-center justify-between p-5 border-b border-gray-200">
            <Dialog.Title className="text-lg font-semibold text-gray-900">
              Справка по разделам
            </Dialog.Title>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
              <X size={20} />
            </button>
          </div>

          <div className="px-5 pt-4 pb-2">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Поиск по инструкциям..."
                className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-5 pb-5 space-y-3">
            {filtered.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-8">
                Ничего не найдено
              </p>
            ) : (
              filtered.map((item: InstructionItem) => {
                const Icon = iconMap[item.icon]
                return (
                  <div key={item.id} className="p-3 rounded-lg bg-gray-50">
                    <div className="flex gap-3">
                      <div className="shrink-0 w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                        {Icon && <Icon size={16} className="text-primary" />}
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-900">{item.label}</p>
                        <p className="text-sm text-gray-500 mt-0.5 leading-relaxed">{item.intro}</p>
                      </div>
                    </div>
                    <ul className="mt-2 pl-11 space-y-1">
                      {item.steps.map((step, i) => (
                        <li key={i} className="text-sm text-gray-600 leading-relaxed list-disc">
                          {step}
                        </li>
                      ))}
                    </ul>
                  </div>
                )
              })
            )}
          </div>
        </Dialog.Panel>
      </div>
    </Dialog>
  )
}

export default InstructionsModal
