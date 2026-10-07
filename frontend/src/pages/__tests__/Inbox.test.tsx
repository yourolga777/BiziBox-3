import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';
import { ToastProvider } from '../../components/common/Toast';
import Inbox from '../Inbox';

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <ToastProvider>{children}</ToastProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };
}

describe('Inbox page', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    server.resetHandlers();
    server.use(
      http.get('/api/messages/threads', () => HttpResponse.json([])),
      http.get('/api/messages/inbox', () => HttpResponse.json([])),
      http.get('/api/messages/spam/count', () => HttpResponse.json({ count: 0 })),
      http.get('/api/channels', () => HttpResponse.json([])),
      http.get('/api/contacts', () => HttpResponse.json([])),
      http.get('/api/folders', () => HttpResponse.json([])),
    );
  });

  it('рендерит заголовок и фильтры (AC2)', async () => {
    render(<Inbox />, { wrapper: createWrapper() });

    expect(await screen.findByText('Telegram')).toBeInTheDocument();
    expect(screen.getByText('Входящие')).toBeInTheDocument();
    expect(screen.getByText('Email')).toBeInTheDocument();
  });

  it('показывает empty state при пустом inbox (AC4)', async () => {
    render(<Inbox />, { wrapper: createWrapper() });

    expect(await screen.findByText('Нет сообщений')).toBeInTheDocument();
  });

  it('показывает вкладку «Другое» для неклассифицированных контактов', async () => {
    render(<Inbox />, { wrapper: createWrapper() });

    expect(await screen.findByText('Другое')).toBeInTheDocument();
  });
});
