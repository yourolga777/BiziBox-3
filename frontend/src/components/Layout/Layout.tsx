import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { MetricsProvider } from '../../hooks/useMetrics'
import Header from './Header'
import Sidebar from './Sidebar'
import { ToastProvider } from '../common/Toast'
import OfflineBanner from '../common/OfflineBanner'

function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const toggleSidebar = () => setSidebarOpen((prev) => !prev)
  const closeSidebar = () => setSidebarOpen(false)

  return (
    <MetricsProvider>
      <ToastProvider>
        <div className="min-h-screen bg-background flex">
          <Sidebar open={sidebarOpen} onClose={closeSidebar} />
          <div className="flex-1 flex flex-col min-w-0">
            <OfflineBanner />
            <Header onToggleSidebar={toggleSidebar} sidebarOpen={sidebarOpen} />
            <main className="flex-1 p-6 animate-fade-in">
              <Outlet />
            </main>
          </div>
        </div>
      </ToastProvider>
    </MetricsProvider>
  )
}

export default Layout
