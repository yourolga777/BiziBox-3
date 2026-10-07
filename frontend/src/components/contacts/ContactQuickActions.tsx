import { Menu } from '@headlessui/react'
import { MessageCircle, ListTodo, ShieldAlert, ShieldCheck, Star, MoreVertical, EyeOff, Trash2, Ban } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { taskApi, messageApi, contactApi } from '../../api/client'
import { useUpdateContactMutation } from '../../hooks/queries'
import { useToast } from '../common/Toast'
import type { Contact } from '../../types/contact'

export default function ContactQuickActions({ contact }: { contact: Contact }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const updateContact = useUpdateContactMutation()
  const { showToast } = useToast()

  const openDialog = () => navigate(`/inbox?contact_id=${contact.id}`)

  const createTask = () => {
    taskApi
      .create({
        title: `Задача: ${contact.name || 'Без имени'}`,
        contact_id: contact.id,
      })
      .catch(() => {})
  }

  const toggleFavorite = () => {
    updateContact.mutate({ id: contact.id, data: { is_favorite: !contact.is_favorite } })
  }

  const toggleSpam = () => {
    const isSpam = contact.life_sphere === 'spam'
    contactApi.setSpam(contact.id, !isSpam).then(() => {
      queryClient.invalidateQueries({ queryKey: ['messages'] })
      queryClient.invalidateQueries({ queryKey: ['inbox'] })
      queryClient.invalidateQueries({ queryKey: ['feed'] })
      queryClient.invalidateQueries({ queryKey: ['threads'] })
      queryClient.invalidateQueries({ queryKey: ['contacts'] })
      queryClient.invalidateQueries({ queryKey: ['contact', contact.id] })
    }).catch(() => {})
  }

  const toggleBlock = async () => {
    if (contact.is_blocked) {
      try {
        await contactApi.unblock(contact.id)
        queryClient.invalidateQueries({ queryKey: ['contacts'] })
        queryClient.invalidateQueries({ queryKey: ['contact', contact.id] })
        showToast('Контакт разблокирован', 'success')
      } catch {
        showToast('Не удалось разблокировать', 'error')
      }
    } else {
      if (!confirm(`Заблокировать контакт «${contact.name || 'Без имени'}»?`)) return
      try {
        await contactApi.block(contact.id)
        queryClient.invalidateQueries({ queryKey: ['contacts'] })
        queryClient.invalidateQueries({ queryKey: ['contact', contact.id] })
        showToast('Контакт заблокирован', 'success')
      } catch {
        showToast('Не удалось заблокировать', 'error')
      }
    }
  }

  const markUnread = async () => {
    try {
      await messageApi.markContactUnread(contact.id)
      queryClient.invalidateQueries({ queryKey: ['messages'] })
      queryClient.invalidateQueries({ queryKey: ['threads'] })
      showToast('Помечено как непрочитанное', 'success')
    } catch {
      showToast('Не удалось пометить', 'error')
    }
  }

  const deleteChat = async () => {
    if (!confirm(`Удалить все сообщения диалога с «${contact.name || 'контактом'}»?`)) return
    try {
      await messageApi.deleteContact(contact.id)
      queryClient.invalidateQueries({ queryKey: ['messages'] })
      queryClient.invalidateQueries({ queryKey: ['threads'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'metrics'] })
      showToast('Диалог удалён', 'success')
    } catch {
      showToast('Не удалось удалить диалог', 'error')
    }
  }

  return (
    <Menu as="div" className="relative shrink-0" onClick={(e) => e.stopPropagation()}>
      <Menu.Button
        className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600"
        title="Действия"
      >
        <MoreVertical className="w-4 h-4" />
      </Menu.Button>
      <Menu.Items className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-xl shadow-lg z-20 min-w-[180px] p-1">
        <Menu.Item>
          {({ active }) => (
            <button
              onClick={openDialog}
              className={`w-full flex items-center gap-2 text-left px-3 py-1.5 rounded-lg text-sm ${active ? 'bg-gray-50' : ''}`}
            >
              <MessageCircle className="w-4 h-4 text-gray-400" />
              Написать
            </button>
          )}
        </Menu.Item>
        <Menu.Item>
          {({ active }) => (
            <button
              onClick={createTask}
              className={`w-full flex items-center gap-2 text-left px-3 py-1.5 rounded-lg text-sm ${active ? 'bg-gray-50' : ''}`}
            >
              <ListTodo className="w-4 h-4 text-gray-400" />
              + Задача
            </button>
          )}
        </Menu.Item>
        <Menu.Item>
          {({ active }) => (
            <button
              onClick={toggleFavorite}
              className={`w-full flex items-center gap-2 text-left px-3 py-1.5 rounded-lg text-sm ${active ? 'bg-gray-50' : ''}`}
            >
              <Star className={`w-4 h-4 ${contact.is_favorite ? 'fill-amber-400 text-amber-400' : 'text-gray-400'}`} />
              {contact.is_favorite ? 'Убрать из избранного' : 'В избранное'}
            </button>
          )}
        </Menu.Item>
        <Menu.Item>
          {({ active }) => (
            <button
              onClick={markUnread}
              className={`w-full flex items-center gap-2 text-left px-3 py-1.5 rounded-lg text-sm ${active ? 'bg-gray-50' : ''}`}
            >
              <EyeOff className="w-4 h-4 text-gray-400" />
              Пометить непрочитанным
            </button>
          )}
        </Menu.Item>
        <Menu.Item>
          {({ active }) => (
            <button
              onClick={deleteChat}
              className={`w-full flex items-center gap-2 text-left px-3 py-1.5 rounded-lg text-sm text-red-600 ${active ? 'bg-red-50' : ''}`}
            >
              <Trash2 className="w-4 h-4 text-red-400" />
              Удалить диалог
            </button>
          )}
        </Menu.Item>
        <Menu.Item>
          {({ active }) => (
            <button
              onClick={toggleSpam}
              className={`w-full flex items-center gap-2 text-left px-3 py-1.5 rounded-lg text-sm ${contact.life_sphere === 'spam' ? '' : 'text-red-600'} ${active ? (contact.life_sphere === 'spam' ? 'bg-gray-50' : 'bg-red-50') : ''}`}
            >
              {contact.life_sphere === 'spam' ? <ShieldCheck className="w-4 h-4 text-green-500" /> : <ShieldAlert className="w-4 h-4 text-red-400" />}
              {contact.life_sphere === 'spam' ? 'Не спам' : 'Пометить спамом'}
            </button>
          )}
        </Menu.Item>
        <Menu.Item>
          {({ active }) => (
            <button
              onClick={toggleBlock}
              className={`w-full flex items-center gap-2 text-left px-3 py-1.5 rounded-lg text-sm ${contact.is_blocked ? 'text-green-600' : 'text-red-600'} ${active ? (contact.is_blocked ? 'bg-green-50' : 'bg-red-50') : ''}`}
            >
              {contact.is_blocked ? <ShieldCheck className="w-4 h-4 text-green-500" /> : <Ban className="w-4 h-4 text-red-400" />}
              {contact.is_blocked ? 'Разблокировать' : 'Заблокировать'}
            </button>
          )}
        </Menu.Item>
      </Menu.Items>
    </Menu>
  )
}
