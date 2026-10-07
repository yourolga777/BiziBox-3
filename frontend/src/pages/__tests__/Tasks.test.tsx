import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';
import Tasks from '../Tasks';

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/tasks']}>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

describe('Tasks page', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    server.resetHandlers();
    server.use(
      http.get('/api/tasks', () =>
        HttpResponse.json([
          { id: 101, contact_id: 1, title: 'Позвонить клиенту', description: null, status: 'new', due_date: '2027-08-10T10:00:00', created_at: '2026-08-01T00:00:00', updated_at: '2026-08-01T00:00:00' },
          { id: 102, contact_id: null, title: 'Подготовить отчёт', description: null, status: 'completed', due_date: '2026-08-02T00:00:00', created_at: '2026-07-30T00:00:00', updated_at: '2026-08-02T00:00:00' },
        ]),
      ),
      http.get('/api/tasks/101', () =>
        HttpResponse.json({
          id: 101, contact_id: 1, title: 'Позвонить клиенту', description: null, status: 'new', due_date: '2027-08-10T10:00:00', created_at: '2026-08-01T00:00:00', updated_at: '2026-08-01T00:00:00', contact_name: 'Иван', comments: [],
        }),
      ),
      http.get('/api/contacts', () =>
        HttpResponse.json([
          { id: 1, name: 'Иван', phone: null, email: null, telegram_id: null, telegram_username: null, is_known: false, is_favorite: false, life_sphere: null, notes: null, channel_types: [], folder_id: null, last_message_at: null, deleted_at: null, created_at: null, updated_at: null },
        ]),
      ),
    );
  });

  it('renders tasks loaded via useTasksQuery and aggregate counts', async () => {
    render(<Tasks />, { wrapper: createWrapper() });

    await screen.findByText('Позвонить клиенту');
    expect(screen.getByText('Подготовить отчёт')).toBeInTheDocument();

    const totals = screen.getAllByRole('heading');
    expect(totals.some(h => h.textContent === 'Задачи')).toBe(true);
    expect(screen.getByText('Всего').nextElementSibling?.textContent).toBe('2');
    expect(screen.getByText('Новых').nextElementSibling?.textContent).toBe('1');
    expect(screen.getAllByText('В работе')[0].nextElementSibling?.textContent).toBe('0');
    expect(screen.getByText('Выполнено').nextElementSibling?.textContent).toBe('1');
  });

  it('renders kanban columns with correct status labels', async () => {
    render(<Tasks />, { wrapper: createWrapper() });

    await screen.findByText('Позвонить клиенту');

    expect(screen.getByRole('heading', { name: 'Новая' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'В работе' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Выполнена' })).toBeInTheDocument();

    // "Позвонить клиенту" is in the Новая column, "Подготовить отчёт" is in Выполнена
    expect(screen.getByRole('button', { name: /Позвонить клиенту/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Подготовить отчёт/ })).toBeInTheDocument();
  });

  it('opens task detail modal on card click', async () => {
    render(<Tasks />, { wrapper: createWrapper() });
    await screen.findByText('Позвонить клиенту');

    const card = screen.getByRole('button', { name: /Позвонить клиенту/ });
    await userEvent.click(card);

    expect(await screen.findAllByText(/Иван/)).not.toHaveLength(0);
    expect(screen.getByText('Контакт')).toBeInTheDocument();
  });

  it('карточка задачи перетаскивается целиком (без отдельной ручки)', async () => {
    render(<Tasks />, { wrapper: createWrapper() });
    await screen.findByText('Позвонить клиенту');

    const card = screen.getByRole('button', { name: /Позвонить клиенту/ });
    expect(card.className).toContain('cursor-grab');
  });

  it('показывает бейдж напоминания на карточке (AC3)', async () => {
    server.use(
      http.get('/api/tasks', () =>
        HttpResponse.json([
          { id: 103, contact_id: null, title: 'С напоминанием', description: null, status: 'new', due_date: '2026-08-10T10:00:00', reminder_minutes: 30, created_at: '2026-08-01T00:00:00', updated_at: '2026-08-01T00:00:00' },
        ]),
      ),
    );
    render(<Tasks />, { wrapper: createWrapper() });

    await screen.findByText('С напоминанием');
    expect(screen.getByText('30 мин')).toBeInTheDocument();
  });
});