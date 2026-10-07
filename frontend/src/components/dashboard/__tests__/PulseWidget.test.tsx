import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../../../mocks/server';
import PulseWidget from '../PulseWidget';

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

describe('PulseWidget', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('shows loading state initially', () => {
    server.use(http.get('/api/dashboard/metrics', () => new Promise(() => {})));
    const { container } = render(<PulseWidget />, { wrapper: createWrapper() });
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('renders metric values after loading', async () => {
    render(<PulseWidget />, { wrapper: createWrapper() });

    await waitFor(() => {
      const values = screen.getAllByText('42');
      expect(values.length).toBeGreaterThan(0);
    });
  });

  it('shows error state on fetch failure', async () => {
    server.use(http.get('/api/dashboard/metrics', () => HttpResponse.error()));

    render(<PulseWidget />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Failed to fetch')).toBeInTheDocument();
    });
  });
});