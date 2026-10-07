import { useEffect, useState } from 'react'
import { Bell, Menu, Search, X } from 'lucide-react'
import { Popover } from '@headlessui/react'
import SyncBadge from '../common/SyncBadge'
import GlobalSearch from './GlobalSearch'
import { getStoredLogin } from '../../api/client'
import { useRemindersQuery, useAckReminderMutation } from '../../hooks/queries'
import { formatRelativeTime } from '../../utils/format'
import type { Reminder } from '../../api/reminders'

interface HeaderProps {
  onToggleSidebar: () => void
  sidebarOpen: boolean
}

function Header({ onToggleSidebar, sidebarOpen }: HeaderProps) {
  const login = getStoredLogin()
  const [searchOpen, setSearchOpen] = useState(false)
  const { data: reminders = [] } = useRemindersQuery({ refetchInterval: 30_000 })
  const ackReminder = useAckReminderMutation()
  const reminderCount = reminders.length

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setSearchOpen((prev) => !prev)
      }
      if (e.key === 'Escape') {
        setSearchOpen(false)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-4 lg:px-6 sticky top-0 z-20">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="lg:hidden p-2 rounded-lg hover:bg-gray-100 text-gray-600"
          title={sidebarOpen ? 'Закрыть меню' : 'Открыть меню'}
          aria-label={sidebarOpen ? 'Закрыть меню' : 'Открыть меню'}
        >
          {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
        <nav className="text-sm text-gray-500 flex items-center" aria-label="Breadcrumb">
          <span className="text-gray-900 font-medium">BiziBox</span>
          {login && (
            <>
              <span className="mx-1.5 text-gray-300">·</span>
              <span className="text-gray-600">@{login}</span>
            </>
          )}
        </nav>
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={() => setSearchOpen(true)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-200 text-gray-400 hover:text-gray-600 hover:bg-gray-50 text-sm"
          title="Поиск (Ctrl+K)"
        >
          <Search size={14} />
          <span className="hidden sm:inline">Поиск</span>
          <kbd className="hidden sm:inline text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-400">Ctrl K</kbd>
        </button>
        <SyncBadge />
        <Popover className="relative">
          <Popover.Button className="relative p-2 rounded-lg hover:bg-gray-100 text-gray-500 outline-none" title="Напоминания" aria-label="Напоминания">
            <Bell size={20} />
            {reminderCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center px-1">
                {reminderCount > 99 ? '99+' : reminderCount}
              </span>
            )}
          </Popover.Button>
          <Popover.Panel className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto rounded-xl bg-white border border-gray-200 shadow-lg z-30">
            {reminders.length === 0 ? (
              <div className="px-4 py-6 text-center text-sm text-gray-400">Нет напоминаний</div>
            ) : (
              <ul className="divide-y divide-gray-100">
                {reminders.map((r: Reminder) => (
                  <li key={`${r.kind}-${r.id}`} className="px-4 py-3 flex items-start gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{r.title}</p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {r.kind === 'task' ? 'Задача' : 'Событие'}
                        {r.fired_at ? ` · ${formatRelativeTime(r.fired_at)}` : ''}
                      </p>
                    </div>
                    <button
                      onClick={() => ackReminder.mutate({ kind: r.kind, id: r.id })}
                      className="shrink-0 px-2.5 py-1 rounded-lg text-xs font-medium bg-primary/10 text-primary hover:bg-primary/20"
                    >
                      ОК
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Popover.Panel>
        </Popover>
      </div>

      <GlobalSearch open={searchOpen} onClose={() => setSearchOpen(false)} />
    </header>
  )
}

export default Header
