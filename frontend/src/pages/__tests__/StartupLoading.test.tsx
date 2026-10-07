import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { StrictMode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';
import StartupLoading from '../StartupLoading';

const LOAD_RESULT = {
  channels: [
    { type: 'telegram', name: 'Telegram', connected: true, new_messages: 12, error: null },
    { type: 'email', name: 'Email', connected: true, new_messages: 5, error: null },
  ],
  total_new: 17,
};

function renderWithRouter() {
  return render(
    <MemoryRouter>
      <StartupLoading onComplete={() => {}} />
    </MemoryRouter>
  );
}

describe('StartupLoading', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    server.resetHandlers();
    Object.defineProperty(navigator, 'onLine', { configurable: true, value: true });
  });

  it('shows spinner while loading', () => {
    server.use(http.post('/api/startup/load', () => new Promise(() => {})));
    renderWithRouter();
    expect(screen.getByText('Загрузка входящих')).toBeInTheDocument();
    expect(screen.getByText(/Подключаем каналы/)).toBeInTheDocument();
  });

  it('shows statistics after load completes', async () => {
    server.use(http.post('/api/startup/load', () => HttpResponse.json(LOAD_RESULT)));
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('новых сообщений')).toBeInTheDocument();
    });
    expect(screen.getByText('17')).toBeInTheDocument();
    expect(screen.getByText('Telegram')).toBeInTheDocument();
    expect(screen.getByText('+12')).toBeInTheDocument();
    expect(screen.getByText('Email')).toBeInTheDocument();
    expect(screen.getByText('+5')).toBeInTheDocument();
  });

  it('shows disconnected badge and hint for failed channel', async () => {
    server.use(
      http.post('/api/startup/load', () =>
        HttpResponse.json({
          channels: [
            { type: 'telegram', name: 'Telegram', connected: false, new_messages: 0, error: null },
          ],
          total_new: 0,
        }),
      ),
    );
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Не подключён')).toBeInTheDocument();
    });
    expect(screen.getByText(/не удалось подключить/i)).toBeInTheDocument();
  });

  it('shows error screen on 4xx and does not call onComplete', async () => {
    const onComplete = vi.fn();
    server.use(
      http.post('/api/startup/load', () => HttpResponse.json({ detail: 'boom' }, { status: 422 })),
    );
    render(
      <MemoryRouter>
        <StartupLoading onComplete={onComplete} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Не удалось загрузить')).toBeInTheDocument();
    });
    expect(onComplete).not.toHaveBeenCalled();
  });

  it('calls onComplete on 5xx (backend unreachable → offline mode)', async () => {
    const onComplete = vi.fn();
    server.use(
      http.post('/api/startup/load', () => HttpResponse.json({ detail: 'boom' }, { status: 500 })),
    );
    render(
      <MemoryRouter>
        <StartupLoading onComplete={onComplete} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledTimes(1);
    });
  });

  it('calls onComplete when offline without blocking entry', async () => {
    const onComplete = vi.fn();
    Object.defineProperty(navigator, 'onLine', { configurable: true, value: false });
    render(
      <MemoryRouter>
        <StartupLoading onComplete={onComplete} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledTimes(1);
    });
  });

  it('calls onComplete after fallback timeout when server hangs', async () => {
    vi.useFakeTimers();
    const onComplete = vi.fn();
    server.use(http.post('/api/startup/load', () => new Promise(() => {})));
    render(
      <MemoryRouter>
        <StartupLoading onComplete={onComplete} />
      </MemoryRouter>
    );

    await vi.advanceTimersByTimeAsync(8000);
    expect(onComplete).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });

  it('calls onComplete when continue clicked', async () => {
    const onComplete = vi.fn();
    server.use(http.post('/api/startup/load', () => HttpResponse.json(LOAD_RESULT)));
    render(
      <MemoryRouter>
        <StartupLoading onComplete={onComplete} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('новых сообщений')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Продолжить'));
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  describe('under StrictMode (double effect invocation)', () => {
    function renderStrict() {
      return render(
        <StrictMode>
          <MemoryRouter>
            <StartupLoading onComplete={() => {}} />
          </MemoryRouter>
        </StrictMode>
      );
    }

    it('shows statistics after load completes (regression: effect must not hang)', async () => {
      server.use(http.post('/api/startup/load', () => HttpResponse.json(LOAD_RESULT)));
      renderStrict();

      await waitFor(() => {
        expect(screen.getByText('новых сообщений')).toBeInTheDocument();
      });
      expect(screen.getByText('17')).toBeInTheDocument();
    });

    it('does not fire a second startup/load POST (single-flight)', async () => {
      let calls = 0;
      server.use(http.post('/api/startup/load', () => {
        calls += 1;
        return HttpResponse.json(LOAD_RESULT);
      }));
      renderStrict();

      await waitFor(() => {
        expect(screen.getByText('новых сообщений')).toBeInTheDocument();
      });
      expect(calls).toBe(1);
    });

    it('calls onComplete via fallback timeout when server hangs', async () => {
      vi.useFakeTimers();
      const onComplete = vi.fn();
      server.use(http.post('/api/startup/load', () => new Promise(() => {})));
      render(
        <StrictMode>
          <MemoryRouter>
            <StartupLoading onComplete={onComplete} />
          </MemoryRouter>
        </StrictMode>
      );

      await vi.advanceTimersByTimeAsync(8000);
      expect(onComplete).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });
  });
});
