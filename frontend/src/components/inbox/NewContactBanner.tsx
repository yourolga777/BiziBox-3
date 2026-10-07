import { UserPlus, Edit3, Users } from 'lucide-react'

export default function NewContactBanner({
  onFillData, onLinkExisting, onCreateNew,
}: {
  onFillData: () => void
  onLinkExisting: () => void
  onCreateNew?: () => void
}) {
  return (
    <div className="border-b border-yellow-200 bg-yellow-50 p-4 shrink-0">
      <div className="flex items-start gap-3">
        <div className="p-1.5 bg-yellow-100 rounded-full mt-0.5">
          <UserPlus className="w-4 h-4 text-yellow-600" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-semibold text-yellow-800">Новый контакт</p>
          <p className="text-xs text-yellow-700 mt-0.5">
            Контакт создан автоматически из сообщения. Заполните данные или привяжите к существующему.
          </p>
          <div className="flex items-center gap-2 mt-3">
            {onCreateNew && (
              <button
                onClick={onCreateNew}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-green-700 bg-green-100 rounded-lg hover:bg-green-200 transition-colors"
              >
                <UserPlus className="w-3.5 h-3.5" />
                Создать новый
              </button>
            )}
            <button
              onClick={onFillData}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-yellow-800 bg-yellow-100 rounded-lg hover:bg-yellow-200 transition-colors"
            >
              <Edit3 className="w-3.5 h-3.5" />
              Редактировать карточку
            </button>
            <button
              onClick={onLinkExisting}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-100 rounded-lg hover:bg-blue-200 transition-colors"
            >
              <Users className="w-3.5 h-3.5" />
              Добавить в существующий
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
