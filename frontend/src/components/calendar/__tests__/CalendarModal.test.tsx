import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../../../mocks/server';
import { CalendarModal } from '../CalendarModal';

const createEventMock = vi.hoisted(() => vi.fn())

vi.mock('../../../api/calendar', async () => {
  const actual = await vi.importActual<typeof import('../../../api/calendar')>('../../../api/calendar')
  return { ...actual, calendarApi: { ...actual.calendarApi, createEvent: createEventMock } }
})

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe('CalendarModal', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    createEventMock.mockReset()
    createEventMock.mockResolvedValue({
      id: 1,
      title: 'Событие',
      date: '2026-08-07',
      time: '09:00',
      description: null,
      reminder_minutes: null,
      recurrence: null,
      contact_id: null,
      created_at: '2026-08-07T09:00:00',
      updated_at: '2026-08-07T09:00:00',
    })
    server.use(
      http.get('/api/contacts', () => HttpResponse.json([])),
    )
  });

  it('создаёт событие через calendarApi (AC2)', async () => {
    const onClose = vi.fn();
    const onCreated = vi.fn();
    const date = new Date(2026, 7, 7);

    render(
      <CalendarModal isOpen onClose={onClose} date={date} onCreated={onCreated} />,
      { wrapper: createWrapper() },
    );

    await userEvent.type(screen.getByLabelText('Заголовок *'), 'Событие');
    await userEvent.selectOptions(screen.getByLabelText('Повторение'), 'weekly');
    await userEvent.click(screen.getByRole('button', { name: 'Создать' }));

    await waitFor(() => {
      expect(createEventMock).toHaveBeenCalledTimes(1);
      expect(onCreated).toHaveBeenCalledTimes(1);
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    const body = createEventMock.mock.calls[0][0];
    expect(body.title).toBe('Событие');
    expect(body.date).toBe('2026-08-07');
    expect(body.recurrence).toBe('weekly');
  });

  it('не отправляет без заголовка (AC4 negative)', async () => {
    const onCreated = vi.fn();
    render(
      <CalendarModal isOpen onClose={vi.fn()} date={new Date()} onCreated={onCreated} />,
      { wrapper: createWrapper() },
    );

    const submit = screen.getByRole('button', { name: 'Создать' });
    expect(submit).toBeDisabled();
    await userEvent.click(submit);
    expect(onCreated).not.toHaveBeenCalled();
    expect(createEventMock).not.toHaveBeenCalled();
  });
});
