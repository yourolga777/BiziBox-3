import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../../../mocks/server';
import { ToastProvider } from '../../common/Toast';
import MessageActions from '../MessageActions';
import type { Message } from '../../../types/message';

function makeMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: 1,
    contact_id: 10,
    channel: 'telegram',
    channel_message_id: 'msg_1',
    content: 'Ваш код: 123456',
    direction: 'incoming',
    status: 'unread',
    created_at: '2026-08-01T00:00:00',
    updated_at: null,
    extracted_code: '123456',
    ...overrides,
  };
}

function renderActions(message: Message) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ToastProvider>
        <MessageActions
          message={message}
          contactName="Иван"
          isAnonymous={false}
          onActionComplete={() => {}}
        />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe('MessageActions', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('показывает кнопки snooze и копировать код (AC3)', () => {
    renderActions(makeMessage());
    expect(screen.getByText('Snooze')).toBeInTheDocument();
    expect(screen.getByText('Код: 123456')).toBeInTheDocument();
    expect(screen.getByText('+ Задача')).toBeInTheDocument();
  });

  it('snooze вызывает PATCH /messages/:id/snooze (AC3)', async () => {
    const snoozed = vi.fn();
    server.use(
      http.patch('/api/messages/:id/snooze', async ({ params, request }) => {
        snoozed(params.id, await request.json());
        return HttpResponse.json(makeMessage({ id: Number(params.id) }));
      }),
    );
    renderActions(makeMessage());

    fireEvent.click(screen.getByText('Snooze'));
    fireEvent.click(await screen.findByText('1 час'));

    await waitFor(() => {
      expect(snoozed).toHaveBeenCalledTimes(1);
    });
    expect(snoozed.mock.calls[0][0]).toBe('1');
  });

  it('копирует extracted_code в буфер обмена', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    renderActions(makeMessage());

    fireEvent.click(screen.getByText('Код: 123456'));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith('123456');
    });
  });

  it('не показывает кнопку кода без extracted_code', () => {
    renderActions(makeMessage({ extracted_code: null }));
    expect(screen.queryByText(/Код:/)).not.toBeInTheDocument();
  });

  it('предзаполняет заголовок и описание из сообщения (AC1/AC2)', () => {
    renderActions(makeMessage({ content: 'Текст сообщения' }));
    fireEvent.click(screen.getByText('+ Задача'));

    const title = screen.getByPlaceholderText('Заголовок задачи') as HTMLInputElement;
    const desc = screen.getByPlaceholderText('Описание задачи (необязательно)...') as HTMLTextAreaElement;

    expect(title.value).toBe('Иван');
    expect(desc.value).toBe('Текст сообщения');
  });
});
