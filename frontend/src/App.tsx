import { useEffect, useState, lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient } from '@tanstack/react-query'
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister'
import ReactQueryDevtoolsConditional from './components/common/Devtools'
import ErrorBoundary from './components/common/ErrorBoundary'
import Layout from './components/Layout/Layout'
import Settings from './pages/Settings'
import Onboarding from './pages/Onboarding'
import Offline from './pages/Offline'
import StartupLoading from './pages/StartupLoading'
import { settingsApi } from './api/settings'
import { setOfflineEnqueue, setStoredLogin, isLocalOnboarded } from './api/client'
import { enqueue } from './offline/queue'
import { initSync, processQueue } from './offline/sync'
import { registerQueryClient } from './offline/queryClient'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Inbox = lazy(() => import('./pages/Inbox'))
const Tasks = lazy(() => import('./pages/Tasks'))
const Orders = lazy(() => import('./pages/Orders'))
const Products = lazy(() => import('./pages/Products'))
const Contacts = lazy(() => import('./pages/Contacts'))
const Archive = lazy(() => import('./pages/Archive'))
const CalendarPage = lazy(() => import('./pages/CalendarPage').then(m => ({ default: m.CalendarPage })))
const Channels = lazy(() => import('./pages/Channels'))
const AiSettings = lazy(() => import('./pages/AiSettings'))

const PageLoader = () => (
  <div className="flex items-center justify-center h-full min-h-[200px]">
    <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent" />
  </div>
)

setOfflineEnqueue(enqueue)
initSync()

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      gcTime: 30 * 60 * 1000,
      retry: 1,
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
      networkMode: 'always',
    },
  },
})

registerQueryClient(queryClient)
processQueue()

const persister = createSyncStoragePersister({
  storage: window.localStorage,
  key: 'BIZIBOX_RQ_CACHE',
})

function AppContent() {
  const [onboarded, setOnboarded] = useState<boolean | null>(null)
  const [startupDone, setStartupDone] = useState(false)

  useEffect(() => {
    let cancelled = false
    if (!navigator.onLine) {
      setOnboarded(isLocalOnboarded())
      return () => { cancelled = true }
    }
    const fallback = setTimeout(() => {
      if (!cancelled) setOnboarded(isLocalOnboarded())
    }, 5_000)
    settingsApi.onboardingStatus()
      .then(res => {
        if (cancelled) return
        clearTimeout(fallback)
        if (res.login) {
          setStoredLogin(res.login)
        }
        setOnboarded(res.onboarded || isLocalOnboarded())
      })
      .catch(() => {
        if (cancelled) return
        clearTimeout(fallback)
        setOnboarded(isLocalOnboarded())
      })
    return () => {
      cancelled = true
      clearTimeout(fallback)
    }
  }, [])

  if (onboarded === null) {
    return <div className="flex items-center justify-center h-screen"><p className="text-gray-400">Загрузка...</p></div>
  }

  if (!onboarded) {
    return (
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="*" element={<Onboarding onComplete={() => setOnboarded(true)} />} />
        </Routes>
      </BrowserRouter>
    )
  }

  if (!startupDone) {
    return (
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <StartupLoading onComplete={() => setStartupDone(true)} />
      </BrowserRouter>
    )
  }

  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ErrorBoundary>
      <Suspense fallback={<PageLoader />}>
      <Routes>
          <Route element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="inbox" element={<Inbox />} />
            <Route path="tasks" element={<Tasks />} />
            <Route path="orders" element={<Orders />} />
            <Route path="products" element={<Products />} />
            <Route path="contacts" element={<Contacts />} />
            <Route path="archive" element={<Archive />} />
            <Route path="channels" element={<Channels />} />
            <Route path="calendar" element={<CalendarPage />} />
            <Route path="ai" element={<AiSettings />} />
            <Route path="settings" element={<Settings />} />
          </Route>
          <Route path="offline" element={<Offline />} />
      </Routes>
      </Suspense>
      </ErrorBoundary>
    </BrowserRouter>
  )
}

function App() {
  return (
    <PersistQueryClientProvider client={queryClient} persistOptions={{ persister }}>
    <ReactQueryDevtoolsConditional />
    <AppContent />
    </PersistQueryClientProvider>
  )
}

export default App
