import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { Archive, CalendarIcon, LayoutDashboard, Inbox, ListTodo, LogOut, Package, ShoppingCart, Radio, Users, Settings, HelpCircle, Sparkles } from 'lucide-react'
import { useMetrics } from '../../hooks/useMetrics'
import { settingsApi } from '../../api/settings'
import { setStoredLogin, clearLocalOnboarded } from '../../api/client'
import InstructionsModal from './InstructionsModal'

interface SidebarProps {
  open: boolean
  onClose: () => void
}

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Дашборд', tooltip: 'Главная панель с метриками' },
  { to: '/inbox', icon: Inbox, label: 'Входящие', tooltip: 'Сообщения: личные, лента, папки' },
  { to: '/contacts', icon: Users, label: 'Контакты', tooltip: 'Управление контактами' },
  { to: '/calendar', icon: CalendarIcon, label: 'Календарь', tooltip: 'Календарь задач' },
  { to: '/tasks', icon: ListTodo, label: 'Задачи', tooltip: 'Список задач и дел' },
  { to: '/orders', icon: Package, label: 'Заказы', tooltip: 'Заказы и позиции' },
  { to: '/products', icon: ShoppingCart, label: 'Каталог', tooltip: 'Товары и поставщики' },
  { to: '/channels', icon: Radio, label: 'Каналы', tooltip: 'Подключение Telegram, Email' },
  { to: '/archive', icon: Archive, label: 'Архив', tooltip: 'Удалённые контакты, сообщения, задачи' },
  { to: '/ai', icon: Sparkles, label: 'AI-ассистент', tooltip: 'AI-функции (скоро)' },
  { to: '/settings', icon: Settings, label: 'Настройки', tooltip: 'Настройки приложения' },
]

function Sidebar({ open, onClose }: SidebarProps) {
  const { data: metrics } = useMetrics()
  const [isInstructionsOpen, setIsInstructionsOpen] = useState(false)

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 bg-black/30 z-30 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={`
          fixed top-0 left-0 h-full w-64 bg-white border-r border-gray-200 z-40 flex flex-col
          transform transition-transform duration-200 ease-in-out
          lg:translate-x-0 lg:static lg:z-auto
          ${open ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <div className="h-16 flex items-center px-6 border-b border-gray-200">
          <h1 className="text-xl font-bold text-primary">BiziBox</h1>
        </div>
        <nav className="flex-1 overflow-y-auto p-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onClose}
              end={item.to === '/'}
              title={item.tooltip}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`
              }
            >
              <item.icon size={18} />
              <span className="flex-1">{item.label}</span>
              {item.to === '/inbox' && metrics && metrics.unread_chats > 0 && (
                <span className="bg-red-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-full min-w-[20px] text-center">
                  {metrics.unread_chats > 99 ? '99+' : metrics.unread_chats}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-gray-200 p-4 mt-auto space-y-1">
          <button
            onClick={() => setIsInstructionsOpen(true)}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
            title="Справка по разделам"
          >
            <HelpCircle size={18} />
            <span>Справка</span>
          </button>
          <button
            onClick={async () => {
              if (!window.confirm('Выйти из приложения? Данные сохранятся.')) return
              try {
                await settingsApi.logout()
              } catch (e) {
                // Сервер может быть недоступен — всё равно очищаем локальное состояние
                console.error('Logout request failed', e)
              }
              setStoredLogin(null)
              clearLocalOnboarded()
              localStorage.removeItem('BIZIBOX_RQ_CACHE')
              window.location.replace('/')
            }}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-red-500 hover:bg-red-50 hover:text-red-600 transition-colors"
            title="Выйти и пройти онбординг заново"
          >
            <LogOut size={18} />
            <span>Выход</span>
          </button>
        </div>
      </aside>

      <InstructionsModal
        open={isInstructionsOpen}
        onClose={() => setIsInstructionsOpen(false)}
      />
    </>
  )
}

export default Sidebar
