import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { settingsApi } from '../../api/settings';
import { OfflineError, ApiError } from '../../api/client';
import Onboarding from '../Onboarding';

vi.mock('../../api/settings', () => ({
  settingsApi: {
    onboardingConfig: vi.fn(),
    onboardingComplete: vi.fn(),
    onboardingStatus: vi.fn(),
    get: vi.fn(),
    update: vi.fn(),
    logout: vi.fn(),
  },
}));

const SAVED_DATA = {
  login: 'alice',
  telegram: { api_id: '', api_hash: '', phone: '', password_2fa: '', useCustomApi: false },
  email: { email: '', password: '', imap_host: '', smtp_host: '', imap_port: 993, smtp_port: 465 },
  vk: { group_id: '', password_2fa: '', token: '' },
  proxy: { mode: 'direct', type: 'socks5', host: '', port: '', username: '', password: '', secret: '' },
};

function renderOnFinishStep(onComplete: () => void) {
  localStorage.setItem('bizibox_onboarding', JSON.stringify({ step: 4, data: SAVED_DATA }));
  return render(<Onboarding onComplete={onComplete} />);
}

describe('Onboarding finish offline-first', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    Object.defineProperty(navigator, 'onLine', { configurable: true, value: true });
    vi.mocked(settingsApi.onboardingConfig).mockResolvedValue({});
  });

  it('completes locally when onboarding-complete fails with a network error', async () => {
    vi.mocked(settingsApi.onboardingComplete).mockRejectedValue(
      new OfflineError('Нет соединения с сервером'),
    );
    const onComplete = vi.fn();
    renderOnFinishStep(onComplete);

    fireEvent.click(screen.getByText('Завершить настройку'));

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledTimes(1);
    });
    expect(localStorage.getItem('bizibox_login')).toBe('alice');
    expect(localStorage.getItem('bizibox_onboarded_local')).toBe('1');
    expect(localStorage.getItem('bizibox_onboarding')).toBeNull();
  });

  it('does not complete and shows error on validation failure (400)', async () => {
    vi.mocked(settingsApi.onboardingComplete).mockRejectedValue(
      new ApiError(400, 'Bad Request', 'Login is required'),
    );
    const onComplete = vi.fn();
    renderOnFinishStep(onComplete);

    fireEvent.click(screen.getByText('Завершить настройку'));

    await waitFor(() => {
      expect(screen.getByText('Login is required')).toBeInTheDocument();
    });
    expect(onComplete).not.toHaveBeenCalled();
  });

  it('does not complete locally on a server error (500)', async () => {
    vi.mocked(settingsApi.onboardingComplete).mockRejectedValue(
      new ApiError(500, 'Internal Server Error', 'Внутренняя ошибка сервера'),
    );
    const onComplete = vi.fn();
    renderOnFinishStep(onComplete);

    fireEvent.click(screen.getByText('Завершить настройку'));

    await waitFor(() => {
      expect(screen.getByText('Внутренняя ошибка сервера')).toBeInTheDocument();
    });
    expect(onComplete).not.toHaveBeenCalled();
    expect(localStorage.getItem('bizibox_onboarded_local')).toBeNull();
  });
});
