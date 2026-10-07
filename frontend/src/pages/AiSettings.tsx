import { Sparkles } from 'lucide-react'
import Card from '../components/common/Card'

function AiSettings() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Sparkles className="w-6 h-6 text-primary" />
        <h2 className="text-2xl font-semibold text-gray-900">AI-ассистент</h2>
      </div>

      <Card>
        <div className="text-center py-12">
          <Sparkles className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900">AI-ассистент будет позже</h3>
          <p className="text-gray-500 mt-2 max-w-md mx-auto">
            Мы работаем над умным помощником, который поможет разбирать сообщения,
            подсказывать ответы и создавать задачи. Эта функция появится в будущих обновлениях.
          </p>
        </div>
      </Card>
    </div>
  )
}

export default AiSettings
