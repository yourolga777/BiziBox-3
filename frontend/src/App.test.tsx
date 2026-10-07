import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from './mocks/server';
import App from './App';

describe('App onboarding gate', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    server.resetHandlers();
    Object.defineProperty(navigator, 'onLine', { configurable: true, value: true });
    localStorage.clear();
  });

  it('shows Загрузка... while onboarding status is pending', () => {
    server.use(http.get('/api/settings/onboarding-status', () => new Promise(() => {})));
    render(<App />);
    expect(screen.getByText('Загрузка...')).toBeInTheDocument();
  });

  it('proceeds to StartupLoading via fallback when onboarding status hangs and local onboarded flag is set', async () => {
    localStorage.setItem('bizibox_onboarded_local', '1');
    vi.useFakeTimers();
    server.use(
      http.get('/api/settings/onboarding-status', () => new Promise(() => {})),
      http.post('/api/startup/load', () => new Promise(() => {})),
    );
    render(<App />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    expect(screen.getByText('Загрузка входящих')).toBeInTheDocument();
    vi.useRealTimers();
  });

  it('shows onboarding when onboarding status returns false and no local flag is set', async () => {
    server.use(
      http.get('/api/settings/onboarding-status', () => HttpResponse.json({ onboarded: false })),
    );
    render(<App />);

    expect(await screen.findByText('Подключение Telegram')).toBeInTheDocument();
  });
});
