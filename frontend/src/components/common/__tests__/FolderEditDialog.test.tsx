import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../../../mocks/server';
import { ToastProvider } from '../../common/Toast';
import FolderEditDialog from '../FolderEditDialog';

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={qc}>
        <ToastProvider>{children}</ToastProvider>
      </QueryClientProvider>
    );
  };
}

const FOLDERS = [
  { id: 1, name: 'Рабочие', color: '#3b82f6', sort_order: 0, is_default: true, category_key: null, created_at: '2026-07-01T00:00:00' },
  { id: 2, name: 'Личные', color: '#22c55e', sort_order: 1, is_default: false, category_key: null, created_at: '2026-07-01T00:00:00' },
];

function seedFolders() {
  server.use(
    http.get('/api/folders', () => HttpResponse.json(FOLDERS)),
  );
}

describe('FolderEditDialog', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    server.use(
      http.post('/api/folders', async ({ request }) => {
        const body = await request.json() as Record<string, unknown>;
        return HttpResponse.json({
          id: 10,
          name: body.name ?? 'Новая папка',
          color: body.color ?? null,
          sort_order: 0,
          is_default: false,
          category_key: body.category_key ?? null,
          created_at: '2026-07-01T00:00:00',
        }, { status: 201 });
      }),
      http.delete('/api/folders/:id', () => HttpResponse.json(null, { status: 204 })),
    );
  });

  it('список папок рендерится (AC2), но не падает на пустом списке (AC5)', async () => {
    server.use(http.get('/api/folders', () => HttpResponse.json([])));
    render(<FolderEditDialog open onClose={() => {}} />, { wrapper: createWrapper() });

    expect(screen.getByText('Папки')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByPlaceholderText('Название новой папки')).toBeInTheDocument();
    });
  });

  it('показывает все папки', async () => {
    seedFolders();
    render(<FolderEditDialog open onClose={() => {}} />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getAllByText('Рабочие').length).toBeGreaterThan(0);
    });
    expect(screen.getAllByText('Личные').length).toBeGreaterThan(0);
  });

  it('создание папки вызывает POST /api/folders (AC1)', async () => {
    seedFolders();
    const postFolder = vi.fn();
    server.use(
      http.post('/api/folders', async ({ request }) => {
        postFolder(await request.json());
        return HttpResponse.json({
          id: 10,
          name: 'Новая папка',
          color: null,
          sort_order: 0,
          is_default: false,
          category_key: null,
          created_at: '2026-07-01T00:00:00',
        }, { status: 201 });
      }),
    );
    render(<FolderEditDialog open onClose={() => {}} />, { wrapper: createWrapper() });

    const input = await screen.findByPlaceholderText('Название новой папки');
    fireEvent.change(input, { target: { value: 'Новая папка' } });
    fireEvent.click(screen.getByRole('button', { name: 'Создать' }));

    await waitFor(() => {
      expect(postFolder).toHaveBeenCalledTimes(1);
    });
    const folderBody = postFolder.mock.calls[0][0] as Record<string, unknown>;
    expect(folderBody.name).toBe('Новая папка');
  });

  it('удаление папки вызывает DELETE /api/folders/:id (AC4)', async () => {
    seedFolders();
    const deleted = vi.fn();
    server.use(
      http.delete('/api/folders/:id', ({ params }) => {
        deleted(params.id);
        return HttpResponse.json(null, { status: 204 });
      }),
    );
    render(<FolderEditDialog open onClose={() => {}} />, { wrapper: createWrapper() });

    const deleteButtons = await screen.findAllByTitle('Удалить');
    expect(deleteButtons.length).toBeGreaterThan(0);
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Удалить папку?')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: 'Да, удалить' }));

    await waitFor(() => {
      expect(deleted).toHaveBeenCalled();
    });
  });

  it('удаление папки требует подтверждения (AC4 negative)', async () => {
    seedFolders();
    const deleted = vi.fn();
    server.use(
      http.delete('/api/folders/:id', () => {
        deleted();
        return HttpResponse.json(null, { status: 204 });
      }),
    );
    render(<FolderEditDialog open onClose={() => {}} />, { wrapper: createWrapper() });

    const deleteButtons = await screen.findAllByTitle('Удалить');
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Удалить папку?')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: 'Отмена' }));

    expect(deleted).not.toHaveBeenCalled();
    expect(screen.queryByText('Удалить папку?')).not.toBeInTheDocument();
  });

  it('create-режим открывает форму создания, а не список папок', async () => {
    seedFolders();
    render(<FolderEditDialog open onClose={() => {}} initialMode="create" />, { wrapper: createWrapper() });

    expect(screen.getByText('Новая папка')).toBeInTheDocument();
    expect(await screen.findByPlaceholderText('Название новой папки')).toBeInTheDocument();
    expect(screen.queryByText('Папки')).not.toBeInTheDocument();
  });

  it('create-режим закрывает диалог после успешного создания', async () => {
    seedFolders();
    const onClose = vi.fn();
    render(<FolderEditDialog open onClose={onClose} initialMode="create" />, { wrapper: createWrapper() });

    const input = await screen.findByPlaceholderText('Название новой папки');
    fireEvent.change(input, { target: { value: 'Работа' } });
    fireEvent.click(screen.getByRole('button', { name: 'Создать' }));

    await waitFor(() => {
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('редактирование папки показывает явную кнопку «Сохранить»', async () => {
    seedFolders();
    render(<FolderEditDialog open onClose={() => {}} />, { wrapper: createWrapper() });

    const renameButtons = await screen.findAllByTitle('Переименовать');
    fireEvent.click(renameButtons[0]);

    const saveButton = await screen.findByRole('button', { name: 'Сохранить' });
    expect(saveButton).toBeInTheDocument();
  });
});
