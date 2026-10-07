import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../../../mocks/server';
import TasksBoard from '../TasksBoard';

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

describe('TasksBoard', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders new and completed task columns from useTasksQuery', async () => {
    render(<TasksBoard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Задачи')).toBeInTheDocument();
      expect(screen.getByText('Позвонить клиенту')).toBeInTheDocument();
      expect(screen.getByText('Подготовить отчёт')).toBeInTheDocument();
    });

    expect(screen.getByText('Новая')).toBeInTheDocument();
    expect(screen.getByText('В работе')).toBeInTheDocument();
    expect(screen.getByText('Выполнена')).toBeInTheDocument();
  });

  it('shows empty state when there are no tasks', async () => {
    server.use(
      http.get('/api/tasks', () => HttpResponse.json([])),
    );

    render(<TasksBoard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getAllByText('Нет задач').length).toBeGreaterThan(0);
    });
  });

  it('toggles task status via useUpdateTaskMutation', async () => {
    const user = userEvent.setup();
    render(<TasksBoard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Позвонить клиенту')).toBeInTheDocument();
    });

    const toggleBtn = screen.getByRole('button', { name: 'Выполнено' });
    await user.click(toggleBtn);
  });
});