import { WifiOff, RefreshCw } from 'lucide-react'

function Offline() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-6">
      <div className="flex flex-col items-center gap-4 text-center max-w-sm">
        <div className="w-16 h-16 rounded-full bg-amber-100 flex items-center justify-center">
          <WifiOff size={32} className="text-amber-600" />
        </div>
        <h1 className="text-xl font-semibold text-gray-900">Нет подключения</h1>
        <p className="text-sm text-gray-500">
          Проверьте соединение с интернетом и попробуйте снова. Некоторые данные могут быть сохранены в кеше.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-xl text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <RefreshCw size={16} />
          Обновить
        </button>
      </div>
    </div>
  )
}

export default Offline
