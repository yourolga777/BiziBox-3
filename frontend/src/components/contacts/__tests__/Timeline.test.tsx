import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../../../mocks/server';
import Timeline from '../Timeline';

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={qc}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

describe('Timeline', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    server.resetHandlers();
    server.use(
      http.get('/api/contacts/:id/timeline', () =>
        HttpResponse.json([
          { type: 'message', title: 'Новое сообщение', subtitle: 'Привет!', created_at: '2026-07-08T12:00:00', link: null },
          { type: 'order', title: 'Заказ №5', subtitle: 'Сумма 1200 ₽', created_at: '2026-07-07T10:00:00', link: '/orders/5' },
          { type: 'task', title: 'Задача: Позвонить', subtitle: 'Статус: новая', created_at: '2026-07-06T09:00:00', link: null },
        ]),
      ),
    );
  });

  it('shows only orders and tasks, hides messages', async () => {
    render(<Timeline contactId={1} />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText('Заказ №5')).toBeTruthy());
    expect(screen.getByText('Задача: Позвонить')).toBeTruthy();
    expect(screen.queryByText('Новое сообщение')).toBeNull();
  });
});
