import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/dashboard/metrics', () =>
    HttpResponse.json({
      total_messages_today: 42,
      total_tasks_today: 8,
      new_contacts_today: 5,
      total_messages: 1247,
      total_tasks: 89,
      total_contacts: 56,
      messages_yesterday: 38,
      tasks_yesterday: 6,
      contacts_yesterday: 3,
      unread_messages: 12,
      unread_chats: 4,
      answered_messages: 30,
      completed_tasks: 40,
      new_messages: 42,
      new_tasks: 8,
      messages_today_active: 42,
      active_tasks: 12,
      channel_distribution: [
        { channel: 'telegram', count: 40 },
        { channel: 'email', count: 16 },
      ],
      top_contacts: [
        { contact_id: 1, contact_name: 'Иван Петров', message_count: 120 },
        { contact_id: 2, contact_name: 'Анна Смирнова', message_count: 84 },
      ],
      last_activity: new Date().toISOString(),
      last_updated: new Date().toISOString(),
      pulse_animation: { type: 'balanced', intensity: 0.6 },
    }),
  ),

  http.get('/api/contacts/:id/timeline', () =>
    HttpResponse.json([
      { type: 'message', title: 'Новое сообщение', subtitle: 'Привет!', created_at: '2026-07-08T12:00:00', link: null },
      { type: 'task', title: 'Задача №5', subtitle: 'Позвонить', created_at: '2026-07-07T10:00:00', link: '/tasks/5' },
    ]),
  ),

  http.get('/api/contacts/:id/notes', () =>
    HttpResponse.json([
      { id: 1, content: 'Позвонить после обеда', author: 'me', created_at: '2026-07-08T12:00:00' },
    ]),
  ),

  http.post('/api/contacts/:id/notes', () =>
    HttpResponse.json({ id: 2, content: 'Новая заметка', author: 'me', created_at: '2026-07-08T13:00:00' }, { status: 201 }),
  ),

  http.get('/api/contacts/1', () =>
    HttpResponse.json({
      id: 1,
      name: 'Иван Петров',
    }),
  ),

  http.get('/api/tasks', () =>
    HttpResponse.json([
      { id: 101, contact_id: 1, title: 'Позвонить клиенту', description: null, status: 'new', due_date: '2026-08-10T10:00:00', created_at: '2026-08-01T00:00:00', updated_at: '2026-08-01T00:00:00' },
      { id: 102, contact_id: null, title: 'Подготовить отчёт', description: null, status: 'completed', due_date: '2026-08-02T00:00:00', created_at: '2026-07-30T00:00:00', updated_at: '2026-08-02T00:00:00' },
    ]),
  ),

  http.patch('/api/tasks/:id', ({ params }) =>
    HttpResponse.json({
      id: Number(params.id),
      title: 'Обновлённая задача',
      description: null,
      status: 'completed',
      due_date: '2026-08-10T10:00:00',
      created_at: '2026-08-01T00:00:00',
      updated_at: '2026-08-07T00:00:00',
    }),
  ),

  http.post('/api/tasks', () =>
    HttpResponse.json({
      id: 103,
      contact_id: null,
      title: 'Купить офисные стулья',
      description: null,
      status: 'new',
      due_date: '2026-08-07T09:00:00',
      created_at: '2026-08-07T00:00:00',
      updated_at: '2026-08-07T00:00:00',
    }, { status: 201 }),
  ),

  http.get('/api/contacts', () =>
    HttpResponse.json([
      { id: 1, name: 'Иван Петров', phone: null, email: null, life_sphere: 'personal', is_favorite: false, messages_count: 120 },
      { id: 2, name: 'Анна Смирнова', phone: null, email: null, life_sphere: 'personal', is_favorite: false, messages_count: 84 },
      { id: 3, name: 'Рабочий', phone: null, email: null, life_sphere: 'work', is_favorite: false, messages_count: 5 },
    ]),
  ),

  http.get('/api/contacts/duplicates', () =>
    HttpResponse.json([]),
  ),

  http.get('/api/folders', () =>
    HttpResponse.json([
      { id: 1, name: 'Рабочие', color: '#3b82f6', sort_order: 0, is_default: false, category_key: null, sphere: 'work', parent_id: null, created_at: '2026-07-01T00:00:00' },
      { id: 2, name: 'Личные', color: '#22c55e', sort_order: 1, is_default: true, category_key: null, sphere: 'personal', parent_id: null, created_at: '2026-07-01T00:00:00' },
    ]),
  ),

  http.post('/api/folders', async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({
      id: 10,
      name: body.name ?? 'Новая папка',
      color: body.color ?? null,
      sort_order: 0,
      is_default: false,
      category_key: body.category_key ?? null,
      sphere: body.sphere ?? null,
      parent_id: body.parent_id ?? null,
      created_at: '2026-07-01T00:00:00',
    }, { status: 201 })
  }),

  http.patch('/api/folders/:id', async ({ request, params }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({
      id: Number(params.id),
      name: body.name ?? 'Папка',
      color: body.color ?? null,
      sort_order: 0,
      is_default: false,
      category_key: null,
      sphere: body.sphere ?? null,
      parent_id: body.parent_id ?? null,
      created_at: '2026-07-01T00:00:00',
    })
  }),

  http.delete('/api/folders/:id', () =>
    HttpResponse.json(null, { status: 204 }),
  ),

  http.patch('/api/messages/:id', ({ params }) =>
    HttpResponse.json({
      id: Number(params.id),
      contact_id: 1,
      channel: 'telegram',
      channel_message_id: null,
      content: 'Хочу заказать пиццу',
      direction: 'incoming',
      status: 'read',
      created_at: '2026-08-15T09:30:00',
      updated_at: '2026-08-15T10:05:00',
      sync_pending: false,
    }),
  ),
]
