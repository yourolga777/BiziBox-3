import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../../../mocks/server';
import NoteList from '../NoteList';

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

describe('NoteList', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders notes', async () => {
    render(<NoteList contactId={1} />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Позвонить после обеда')).toBeInTheDocument();
    });
  });

  it('shows empty state', async () => {
    server.use(http.get('/api/contacts/1/notes', () => HttpResponse.json([])));

    render(<NoteList contactId={1} />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Нет заметок')).toBeInTheDocument();
    });
  });
});
