import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../../../mocks/server';
import MessageDetail from '../MessageDetail';
import type { Message } from '../../../types/message';
import type { Contact } from '../../../types/contact';

vi.mock('../../contacts/ContactDetailPanel', () => ({
  default: ({ onEdit }: { onEdit: () => void }) => <button onClick={onEdit}>Открыть форму</button>,
}));
vi.mock('../ThreadList', () => ({ ThreadList: ({ messages }: { messages: unknown[] }) => <div data-testid="thread-count">{messages.length}</div> }));
vi.mock('../ReplyBar', () => ({
  default: ({ recipientOptions }: { recipientOptions?: { value: string; label: string }[] }) => (
    <div data-testid="recipient-options" data-count={String(recipientOptions?.length ?? 0)} />
  ),
}));
vi.mock('../MessageActions', () => ({ default: () => null }));
vi.mock('../NewContactBanner', () => ({ default: () => null }));
vi.mock('../ContactSearchPopup', () => ({ default: () => null }));
vi.mock('../../../offline/db', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../offline/db')>();
  return { ...actual, getMessagesFromCache: vi.fn() };
});

import { getMessagesFromCache } from '../../../offline/db';

function makeContact(name: string): Contact {
  return {
    id: 1,
    name,
    phone: null,
    email: null,
    telegram_id: null,
    telegram_username: null,
    is_known: true,
    is_favorite: false,
    life_sphere: null,
    notes: null,
    channel_types: ['telegram'],
    contact_types: [],
    contact_type_ids: [],
    folder_id: null,
    last_message_at: null,
    deleted_at: null,
    created_at: null,
    updated_at: null,
  };
}

function makeMessage(overrides?: Partial<Message>): Message {
  return {
    id: 1,
    contact_id: 1,
    contact_name: 'Старое имя',
    channel: 'telegram',
    channel_message_id: '123',
    content: 'Привет!',
    direction: 'incoming',
    status: 'read',
    created_at: '2026-01-01T00:00:00',
    updated_at: '2026-01-01T00:00:00',
    ...overrides,
  };
}

function createWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe('MessageDetail — имя контакта после редактирования', () => {
  let currentName: string;

  beforeEach(() => {
    vi.restoreAllMocks();
    server.resetHandlers();
    currentName = 'Новое имя';
    server.use(
      http.get('/api/folders', () => HttpResponse.json([])),
      http.get('/api/templates', () => HttpResponse.json([])),
      http.get('/api/messages/dialog/1', () => HttpResponse.json([])),
      http.post('/api/messages/sync-dialog/1', () => HttpResponse.json({ new_messages: 0 })),
      http.post('/api/messages/reclassify-by-contact/1', () => HttpResponse.json({ updated: 0 })),
      http.get('/api/contacts/1', () => HttpResponse.json(makeContact(currentName))),
      http.patch('/api/contacts/1', async ({ request }) => {
        const body = (await request.json()) as { name?: string };
        currentName = body.name ?? currentName;
        return HttpResponse.json(makeContact(currentName));
      }),
    );
  });

  it('показывает свежее имя из контакта, а не устаревший contact_name сообщения', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MessageDetail message={makeMessage()} contactName="Имя из родителя" onClose={vi.fn()} onReplied={vi.fn()} />,
      { wrapper: createWrapper(qc) },
    );

    await waitFor(() => expect(screen.getByRole('button', { name: 'Новое имя' })).toBeTruthy());
    expect(screen.queryByText('Старое имя')).toBeNull();
    expect(screen.queryByText('Имя из родителя')).toBeNull();
  });

  it('инвалидирует кеши контактов и обновляет заголовок после сохранения формы', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const spy = vi.spyOn(qc, 'invalidateQueries');
    render(
      <MessageDetail message={makeMessage()} contactName={null} onClose={vi.fn()} onReplied={vi.fn()} />,
      { wrapper: createWrapper(qc) },
    );

    await waitFor(() => expect(screen.getByRole('button', { name: 'Новое имя' })).toBeTruthy());
    await userEvent.click(screen.getByRole('button', { name: 'Новое имя' }));

    const nameInput = screen.getByLabelText('Имя') as HTMLInputElement;
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, 'Обновлённое имя');
    await userEvent.click(screen.getByText('Сохранить'));

    await waitFor(() => expect(spy).toHaveBeenCalledWith({ queryKey: ['contacts'] }));
    expect(spy).toHaveBeenCalledWith({ queryKey: ['contact', 1] });
    await waitFor(() => expect(screen.getByRole('button', { name: 'Обновлённое имя' })).toBeTruthy());
    expect(screen.queryByText('Новое имя')).toBeNull();
  });
});

describe('MessageDetail — кнопка спам', () => {
  let contactIsSpam: boolean;
  let patchBody: Record<string, unknown> | null;

  beforeEach(() => {
    vi.restoreAllMocks();
    server.resetHandlers();
    contactIsSpam = false;
    patchBody = null;
    server.use(
      http.get('/api/folders', () => HttpResponse.json([])),
      http.get('/api/templates', () => HttpResponse.json([])),
      http.get('/api/messages/dialog/1', () => HttpResponse.json([])),
      http.post('/api/messages/sync-dialog/1', () => HttpResponse.json({ new_messages: 0 })),
      http.get('/api/contacts/1', () => HttpResponse.json(makeContact('Контакт Спам'))),
      http.patch('/api/contacts/1', async ({ request }) => {
        patchBody = (await request.json()) as Record<string, unknown>;
        contactIsSpam = (patchBody.life_sphere as string) === 'spam' ? true : contactIsSpam;
        const updated = makeContact('Контакт Спам');
        updated.life_sphere = contactIsSpam ? 'spam' : 'personal';
        return HttpResponse.json(updated);
      }),
    );
  });

  it('отправляет life_sphere: spam при клике на кнопку Спам', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    let spamParam: string | null = null;
    server.use(
      http.get('/api/folders', () => HttpResponse.json([])),
      http.get('/api/templates', () => HttpResponse.json([])),
      http.get('/api/messages/dialog/1', () => HttpResponse.json([])),
      http.get('/api/contacts/1', () => HttpResponse.json(makeContact('Контакт Спам'))),
      http.post('/api/contacts/1/set-spam', async ({ request }) => {
        spamParam = new URL(request.url).searchParams.get('spam');
        const updated = makeContact('Контакт Спам');
        updated.life_sphere = spamParam === 'true' ? 'spam' : 'personal';
        return HttpResponse.json(updated);
      }),
    );
    render(
      <MessageDetail message={makeMessage()} contactName="Контакт Спам" onClose={vi.fn()} onReplied={vi.fn()} />,
      { wrapper: createWrapper(qc) },
    );

    await waitFor(() => expect(screen.getByTitle('Пометить как спам')).toBeTruthy());
    await userEvent.click(screen.getByTitle('Пометить как спам'));

    await waitFor(() => expect(spamParam).toBe('true'));
  });
});

describe('MessageDetail — автопрочтение диалога', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    server.resetHandlers();
    server.use(
      http.get('/api/folders', () => HttpResponse.json([])),
      http.get('/api/templates', () => HttpResponse.json([])),
      http.post('/api/messages/sync-dialog/1', () => HttpResponse.json({ new_messages: 0 })),
      http.post('/api/messages/reclassify-by-contact/1', () => HttpResponse.json({ updated: 0 })),
      http.get('/api/contacts/1', () => HttpResponse.json(makeContact('Контакт'))),
    );
  });

  it('помечает весь чат прочитанным после таймера', async () => {
    let markReadCalled = false;
    server.use(
      http.get('/api/messages/dialog/1', () =>
        HttpResponse.json([
          makeMessage({ id: 1, status: 'unread' }),
          makeMessage({ id: 2, status: 'unread' }),
          makeMessage({ id: 3, status: 'read' }),
        ])),
      http.post('/api/messages/contact/1/mark-read', () => {
        markReadCalled = true;
        return HttpResponse.json({ updated: 2 });
      }),
    );

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MessageDetail message={makeMessage({ status: 'unread' })} contactName={null} onClose={vi.fn()} onReplied={vi.fn()} />,
      { wrapper: createWrapper(qc) },
    );

    await waitFor(() => expect(markReadCalled).toBe(true), { timeout: 3000 });
  });

  it('обновляет статус в кеше messages после прочтения', async () => {
    server.use(
      http.get('/api/messages/dialog/1', () =>
        HttpResponse.json([makeMessage({ id: 1, status: 'unread' })])),
      http.post('/api/messages/contact/1/mark-read', () => HttpResponse.json({ updated: 1 })),
    );

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    qc.setQueryData(['messages', 'inbox'], [makeMessage({ id: 1, status: 'unread' })]);
    render(
      <MessageDetail message={makeMessage({ status: 'unread' })} contactName={null} onClose={vi.fn()} onReplied={vi.fn()} />,
      { wrapper: createWrapper(qc) },
    );

    await waitFor(
      () => {
        const cached = qc.getQueryData<Message[]>(['messages', 'inbox']);
        expect(cached?.[0].status).toBe('read');
      },
      { timeout: 3000 },
    );
  });

  it('инвалидирует threads после прочтения', async () => {
    server.use(
      http.get('/api/messages/dialog/1', () =>
        HttpResponse.json([makeMessage({ id: 1, status: 'unread' })])),
      http.post('/api/messages/contact/1/mark-read', () => HttpResponse.json({ updated: 1 })),
    );

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries');
    render(
      <MessageDetail message={makeMessage({ status: 'unread' })} contactName={null} onClose={vi.fn()} onReplied={vi.fn()} />,
      { wrapper: createWrapper(qc) },
    );

    await waitFor(
      () => expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['threads'] }),
      { timeout: 3000 },
    );
  });

  it('вызывает mark-read даже если на загруженной странице нет непрочитанных', async () => {
    let markReadCalled = false;
    server.use(
      http.get('/api/messages/dialog/1', () =>
        HttpResponse.json([makeMessage({ id: 1, status: 'read' })])),
      http.post('/api/messages/contact/1/mark-read', () => {
        markReadCalled = true;
        return HttpResponse.json({ updated: 0 });
      }),
    );

    vi.useFakeTimers();
    try {
      const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
      render(
        <MessageDetail message={makeMessage({ status: 'read' })} contactName={null} onClose={vi.fn()} onReplied={vi.fn()} />,
        { wrapper: createWrapper(qc) },
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(4000);
      });

      expect(markReadCalled).toBe(true);
    } finally {
      vi.useRealTimers();
    }
  });

  it('не отправляет bulk-запрос, если диалог закрыт до таймера', async () => {
    let bulkCalled = false;
    server.use(
      http.get('/api/messages/dialog/1', () =>
        HttpResponse.json([makeMessage({ id: 1, status: 'unread' })])),
      http.post('/api/messages/contact/1/mark-read', () => {
        bulkCalled = true;
        return HttpResponse.json({ updated: 1 });
      }),
    );

    vi.useFakeTimers();
    try {
      const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
      const { unmount } = render(
        <MessageDetail message={makeMessage({ status: 'unread' })} contactName={null} onClose={vi.fn()} onReplied={vi.fn()} />,
        { wrapper: createWrapper(qc) },
      );

      unmount();

      await act(async () => {
        await vi.advanceTimersByTimeAsync(4000);
      });

      expect(bulkCalled).toBe(false);
    } finally {
      vi.useRealTimers();
    }
  });
});

describe('MessageDetail — оффлайн переписка из кэша', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    server.resetHandlers();
    vi.mocked(getMessagesFromCache).mockReset();
    server.use(
      http.get('/api/folders', () => HttpResponse.json([])),
      http.get('/api/templates', () => HttpResponse.json([])),
      http.post('/api/messages/sync-dialog/1', () => HttpResponse.json({ new_messages: 0 })),
      http.post('/api/messages/reclassify-by-contact/1', () => HttpResponse.json({ updated: 0 })),
      http.get('/api/contacts/1', () => HttpResponse.json(makeContact('Контакт'))),
      http.patch('/api/contacts/1', () => HttpResponse.json(makeContact('Контакт'))),
    );
  });

  it('показывает сообщения из кэша, когда getDialog недоступен', async () => {
    vi.mocked(getMessagesFromCache).mockResolvedValue([
      makeMessage({ id: 5, contact_id: 1, content: 'Кэшированное сообщение' }),
      makeMessage({ id: 6, contact_id: 1, content: 'Ещё одно' }),
    ] as never);
    server.use(
      http.get('/api/messages/dialog/1', () => HttpResponse.json({}, { status: 500 })),
    );

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MessageDetail message={makeMessage()} contactName={null} onClose={vi.fn()} onReplied={vi.fn()} />,
      { wrapper: createWrapper(qc) },
    );

    await waitFor(() => expect(screen.getByTestId('thread-count')).toHaveTextContent('2'));
  });

  it('AC5: offline без кэша — пустая переписка без падения', async () => {
    vi.mocked(getMessagesFromCache).mockResolvedValue([] as never);
    server.use(
      http.get('/api/messages/dialog/1', () => HttpResponse.json({}, { status: 500 })),
    );

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MessageDetail message={makeMessage()} contactName={null} onClose={vi.fn()} onReplied={vi.fn()} />,
      { wrapper: createWrapper(qc) },
    );

    await waitFor(() => expect(screen.getByTestId('thread-count')).toHaveTextContent('0'));
  });

  it('фильтрует кэш по contact_id конкретного диалога', async () => {
    vi.mocked(getMessagesFromCache).mockResolvedValue([
      makeMessage({ id: 5, contact_id: 1, content: 'Мой диалог' }),
      makeMessage({ id: 9, contact_id: 99, content: 'Чужой диалог' }),
    ] as never);
    server.use(
      http.get('/api/messages/dialog/1', () => HttpResponse.json({}, { status: 500 })),
    );

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MessageDetail message={makeMessage()} contactName={null} onClose={vi.fn()} onReplied={vi.fn()} />,
      { wrapper: createWrapper(qc) },
    );

    await waitFor(() => expect(screen.getByTestId('thread-count')).toHaveTextContent('1'));
  });
});


describe('MessageDetail — выбор получателя', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    server.resetHandlers();
    server.use(
      http.get('/api/folders', () => HttpResponse.json([])),
      http.get('/api/templates', () => HttpResponse.json([])),
      http.get('/api/messages/dialog/1', () => HttpResponse.json([])),
      http.post('/api/messages/sync-dialog/1', () => HttpResponse.json({ new_messages: 0 })),
      http.post('/api/messages/reclassify-by-contact/1', () => HttpResponse.json({ updated: 0 })),
    );
  });

  it('строит опции получателя из полей контакта и identifiers', async () => {
    const contact = {
      ...makeContact('Контакт'),
      telegram_id: '12345',
      identifiers: [
        { channel: 'telegram_username', value: '@second' },
        { channel: 'telegram_id', value: '777000' },
      ],
    };
    server.use(http.get('/api/contacts/1', () => HttpResponse.json(contact)));

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MessageDetail message={makeMessage()} contactName={null} onClose={vi.fn()} onReplied={vi.fn()} />,
      { wrapper: createWrapper(qc) },
    );

    await waitFor(() => expect(screen.getByTestId('recipient-options')).toHaveAttribute('data-count', '3'));
  });

  it('без альтернативных адресов — только один получатель (negative)', async () => {
    const contact = { ...makeContact('Контакт'), telegram_id: '12345' };
    server.use(http.get('/api/contacts/1', () => HttpResponse.json(contact)));

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MessageDetail message={makeMessage()} contactName={null} onClose={vi.fn()} onReplied={vi.fn()} />,
      { wrapper: createWrapper(qc) },
    );

    await waitFor(() => expect(screen.getByTestId('recipient-options')).toHaveAttribute('data-count', '1'));
  });
});