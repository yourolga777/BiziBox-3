import { useState, useEffect } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { GitMerge, Search, ChevronRight, CircleDashed, Tag, Check } from 'lucide-react'
import { contactSchema, type ContactFormData } from '../../schemas'
import { contactApi } from '../../api/client'
import { useFoldersQuery } from '../../hooks/queries'
import { displayName } from '../../utils/contactDisplayName'
import { CONTACT_SPHERES, CONTACT_SPHERE_META } from '../../types/contactType'
import type { Contact, ContactFolder, ContactSphere } from '../../types/contact'

function toNullableString(v: unknown): string | undefined {
  if (v === null || v === undefined || v === '') return undefined
  return String(v)
}

function toNullableNumber(v: unknown): number | null {
  if (v === null || v === undefined || v === '') return null
  return Number(v)
}

const SPHERES_WITH_FOLDERS: ContactSphere[] = ['personal', 'work', 'channels']

export default function ContactForm({
  initial,
  onSubmit,
  onCancel,
  onMerge,
}: {
  initial: Contact | null
  onSubmit: (data: ContactFormData) => Promise<void>
  onCancel: () => void
  onMerge?: (targetId: number) => Promise<void>
}) {
  const { data: folders = [] } = useFoldersQuery()
  const [showMerge, setShowMerge] = useState(false)
  const [mergeQuery, setMergeQuery] = useState('')
  const [mergeResults, setMergeResults] = useState<Contact[]>([])
  const [merging, setMerging] = useState(false)

  const { register, handleSubmit: withValidation, setError, setValue, control, formState: { errors, isSubmitting, isDirty } } = useForm<ContactFormData>({
    resolver: zodResolver(contactSchema),
    defaultValues: {
      name: initial?.name || '',
      phone: initial?.phone || '',
      email: initial?.email || '',
      telegram_username: initial?.telegram_username || '',
      notes: initial?.notes || '',
      is_favorite: initial?.is_favorite ?? false,
      life_sphere: (initial?.life_sphere || '') as ContactSphere | '',
      birthday: initial?.birthday ?? '',
      folder_ids: initial?.folders?.map(f => f.id) ?? [],
    },
  })

  const selectedSphere = useWatch({ control, name: 'life_sphere' }) as ContactSphere | ''
  const effectiveSphere: ContactSphere | '' = selectedSphere || ''

  const [expandedSphere, setExpandedSphere] = useState<ContactSphere | null>(
    initial?.life_sphere && SPHERES_WITH_FOLDERS.includes(initial.life_sphere) ? initial.life_sphere : null,
  )
  const selectedFolderIds = useWatch({ control, name: 'folder_ids' }) as number[] | undefined
  const activeFolderIds = selectedFolderIds ?? []
  const childrenOf = (parentId: number | null) =>
    folders.filter(f => (f.parent_id ?? null) === parentId)

  const renderFolderTree = (folder: ContactFolder, depth: number) => {
    const children = childrenOf(folder.id)
    const active = activeFolderIds.includes(folder.id)
    return (
      <div key={folder.id}>
        <button
          type="button"
          onClick={() => {
            const next = active
              ? activeFolderIds.filter(id => id !== folder.id)
              : [...activeFolderIds, folder.id]
            setValue('folder_ids', next)
          }}
          className={`w-full flex items-center gap-2 px-2 py-1.5 text-sm rounded-lg transition-colors ${
            active ? 'bg-blue-100 text-blue-700 font-medium' : 'text-gray-700 hover:bg-gray-50'
          }`}
          style={{ paddingLeft: 8 + depth * 14 }}
        >
          <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: folder.color || '#6b7280' }} />
          <span className="flex-1 text-left truncate">{folder.name}</span>
          {active && <Check className="w-3.5 h-3.5 text-blue-600 shrink-0" />}
        </button>
        {children.map(c => renderFolderTree(c, depth + 1))}
      </div>
    )
  }

  useEffect(() => {
    if (!isDirty) return
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [isDirty])

  const handleCancel = () => {
    if (isDirty && !window.confirm('Есть несохранённые изменения. Выйти без сохранения?')) {
      return
    }
    onCancel()
  }

  const isEditing = !!initial

  const handleValidatedSubmit = async (data: ContactFormData) => {
    if (!isEditing && !data.name?.trim() && !data.phone?.trim() && !data.email?.trim()) {
      setError('name', { type: 'manual', message: 'Укажите хотя бы имя, телефон или email' })
      return
    }
    await onSubmit(data)
  }

  const handleMergeSearch = async (q: string) => {
    setMergeQuery(q)
    if (q.trim().length < 2) {
      setMergeResults([])
      return
    }
    try {
      const results = await contactApi.search(q)
      setMergeResults(Array.isArray(results) ? results.filter(c => c.id !== initial?.id) : [])
    } catch {
      setMergeResults([])
    }
  }

  const handleMerge = async (targetId: number) => {
    if (!onMerge || merging) return
    setMerging(true)
    try {
      await onMerge(targetId)
    } finally {
      setMerging(false)
    }
  }

  return (
    <form onSubmit={withValidation(handleValidatedSubmit)} className="space-y-4">
      <div>
        <label htmlFor="contact-name" className="block text-sm font-medium text-gray-700 mb-1">Имя</label>
        <input id="contact-name" {...register('name')} className="w-full px-3 py-2 border rounded-lg" />
        {errors.name && <p className="text-xs text-red-500 mt-1">{errors.name.message}</p>}
      </div>
      <div>
        <label htmlFor="contact-phone" className="block text-sm font-medium text-gray-700 mb-1">Телефон</label>
        <input id="contact-phone" {...register('phone')} className="w-full px-3 py-2 border rounded-lg" />
        {errors.phone && <p className="text-xs text-red-500 mt-1">{errors.phone.message}</p>}
      </div>
      <div>
        <label htmlFor="contact-email" className="block text-sm font-medium text-gray-700 mb-1">Email</label>
        <input id="contact-email" type="email" {...register('email')} className="w-full px-3 py-2 border rounded-lg" />
        {errors.email && <p className="text-xs text-red-500 mt-1">{errors.email.message}</p>}
      </div>
      <div>
        <label htmlFor="contact-tg-username" className="block text-sm font-medium text-gray-700 mb-1">Telegram @username</label>
        <input id="contact-tg-username" {...register('telegram_username')} placeholder="@username" className="w-full px-3 py-2 border rounded-lg" />
        {errors.telegram_username && <p className="text-xs text-red-500 mt-1">{errors.telegram_username.message}</p>}
      </div>
      <div>
        <label htmlFor="contact-notes" className="block text-sm font-medium text-gray-700 mb-1">Заметки</label>
        <textarea id="contact-notes" {...register('notes')} rows={3} className="w-full px-3 py-2 border rounded-lg" />
        {errors.notes && <p className="text-xs text-red-500 mt-1">{errors.notes.message}</p>}
      </div>

      <div>
        <p className="block text-sm font-medium text-gray-700 mb-1">Классификация</p>
        <div className="space-y-1 border border-gray-200 rounded-lg p-2 max-h-60 overflow-y-auto">
          <button
            type="button"
            onClick={() => { setValue('life_sphere', ''); setValue('folder_ids', []) }}
            className={`w-full flex items-center gap-2 px-2 py-1.5 text-sm rounded-lg transition-colors ${
              effectiveSphere === '' ? 'bg-blue-100 text-blue-700 font-medium' : 'text-gray-700 hover:bg-gray-50'
            }`}
          >
            <CircleDashed className="w-4 h-4 text-gray-400" />
            Другое (без сферы)
          </button>
          {CONTACT_SPHERES.map(s => {
            const showFolders = SPHERES_WITH_FOLDERS.includes(s)
            const expanded = expandedSphere === s
            const isActive = effectiveSphere === s && activeFolderIds.length === 0
            return (
              <div key={s}>
                <button
                  type="button"
                    onClick={() => {
                      setValue('life_sphere', s)
                      setValue('folder_ids', [])
                      if (showFolders) setExpandedSphere(expanded ? null : s)
                    }}
                  className={`w-full flex items-center gap-2 px-2 py-1.5 text-sm rounded-lg transition-colors ${
                    isActive ? 'bg-blue-100 text-blue-700 font-medium' : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <ChevronRight className={`w-3.5 h-3.5 text-gray-400 transition-transform ${expanded ? 'rotate-90' : ''}`} />
                  <Tag className="w-4 h-4 text-gray-400" />
                  <span className="flex-1 text-left">{CONTACT_SPHERE_META[s].label}</span>
                </button>
                {showFolders && expanded && (
                  <div className="ml-3 pl-2 border-l border-gray-200">
                    <button
                      type="button"
                      onClick={() => { setValue('life_sphere', s); setValue('folder_ids', []) }}
                      className={`w-full text-left px-2 py-1.5 text-sm rounded-lg transition-colors ${
                        isActive ? 'text-blue-700 font-medium' : 'text-gray-500 hover:bg-gray-50'
                      }`}
                    >
                      Без папки
                    </button>
                    {childrenOf(null)
                      .filter(f => (f.sphere || 'personal') === s)
                      .map(f => renderFolderTree(f, 0))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
        {errors.life_sphere && <p className="text-xs text-red-500 mt-1">{errors.life_sphere.message}</p>}
        {errors.folder_ids && <p className="text-xs text-red-500 mt-1">{errors.folder_ids.message}</p>}
      </div>

      <div>
        <label htmlFor="contact-birthday" className="block text-sm font-medium text-gray-700 mb-1">День рождения</label>
        <input id="contact-birthday" type="date" {...register('birthday')} className="w-full px-3 py-2 border rounded-lg" />
        {errors.birthday && <p className="text-xs text-red-500 mt-1">{errors.birthday.message}</p>}
      </div>

      <div className="flex items-center gap-3">
        <input id="contact-is-favorite" type="checkbox" {...register('is_favorite')} className="w-4 h-4 rounded border-gray-300 text-blue-600" />
        <label htmlFor="contact-is-favorite" className="text-sm text-gray-700">Избранное</label>
      </div>

      {isEditing && onMerge && (
        <div className="border-t pt-3">
          <button
            type="button"
            onClick={() => setShowMerge(!showMerge)}
            className="inline-flex items-center gap-1.5 text-sm text-gray-600 hover:text-blue-600 transition-colors"
          >
            <GitMerge className="w-4 h-4" />
            Объединить с контактом
          </button>
          {showMerge && (
            <div className="mt-3 space-y-2">
              <div className="relative">
                <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={mergeQuery}
                  onChange={e => handleMergeSearch(e.target.value)}
                  placeholder="Поиск контакта для объединения..."
                  className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm"
                />
              </div>
              {mergeQuery.trim().length >= 2 && mergeResults.length === 0 && (
                <p className="text-xs text-gray-400">Ничего не найдено</p>
              )}
              {mergeResults.length > 0 && (
                <div className="max-h-40 overflow-y-auto space-y-1">
                  {mergeResults.map(c => (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => handleMerge(c.id)}
                      disabled={merging}
                      className="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-100 text-sm transition-colors disabled:opacity-50"
                    >
                      <span className="font-medium text-gray-900">{displayName(c)}</span>
                      {c.phone && <span className="text-gray-500 ml-2">{c.phone}</span>}
                      {c.email && !c.phone && <span className="text-gray-500 ml-2">{c.email}</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="flex justify-end gap-2 pt-2">
        <button type="button" onClick={handleCancel} className="px-4 py-2 text-sm border rounded-lg">Отмена</button>
        <button type="submit" disabled={isSubmitting || merging} className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg disabled:opacity-50">
          {isSubmitting ? 'Сохранение...' : 'Сохранить'}
        </button>
      </div>
    </form>
  )
}

export { toNullableString, toNullableNumber }
