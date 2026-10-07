import { describe, it, expect, vi } from 'vitest'
import { render, fireEvent, screen } from '@testing-library/react'
import FolderTree from '../FolderTree'
import type { ContactFolder } from '../../../types/contact'

const FOLDER_DRAG_TYPE = 'application/x-bizibox-folder'

function createDataTransfer(initial: Record<string, string> = {}): DataTransfer {
  const store = { ...initial }
  return {
    getData: (type: string) => store[type] ?? '',
    setData: (type: string, value: string) => { store[type] = value },
    effectAllowed: 'move',
    dropEffect: 'move',
  } as unknown as DataTransfer
}

function makeFolder(id: number, name: string, overrides: Partial<ContactFolder> = {}): ContactFolder {
  return {
    id,
    name,
    color: null,
    sort_order: id,
    is_default: false,
    category_key: null,
    sphere: 'personal',
    parent_id: null,
    created_at: null,
    ...overrides,
  }
}

describe('FolderTree', () => {
  it('рендерит корневые папки и подпапки с отступом', () => {
    const folders = [
      makeFolder(1, 'Родитель'),
      makeFolder(2, 'Дитя', { parent_id: 1 }),
    ]
    render(<FolderTree folders={folders} />)

    expect(screen.getByText('Родитель')).toBeInTheDocument()
    expect(screen.getByText('Дитя')).toBeInTheDocument()
  })

  it('вызывает onSelect при клике на папку', () => {
    const onSelect = vi.fn()
    render(<FolderTree folders={[makeFolder(1, 'Личные')]} onSelect={onSelect} />)

    fireEvent.click(screen.getByText('Личные'))
    expect(onSelect).toHaveBeenCalledWith(1)
  })

  it('drop контакта вызывает onDropContact с id контактa и папки', () => {
    const onDropContact = vi.fn()
    render(
      <FolderTree folders={[makeFolder(1, 'Личные')]} onDropContact={onDropContact} />,
    )

    const row = screen.getByText('Личные').closest('div') as HTMLElement
    fireEvent.drop(row, { dataTransfer: createDataTransfer({ 'text/plain': '42' }) })

    expect(onDropContact).toHaveBeenCalledWith(42, 1)
  })

  it('drop папки на sibling вызывает onReorder с новым порядком', () => {
    const onReorder = vi.fn()
    const folders = [
      makeFolder(1, 'Первая'),
      makeFolder(2, 'Вторая'),
      makeFolder(3, 'Третья'),
    ]
    render(<FolderTree folders={folders} onReorder={onReorder} />)

    const second = screen.getByText('Вторая').closest('div') as HTMLElement
    const third = screen.getByText('Третья').closest('div') as HTMLElement

    fireEvent.dragStart(second, { dataTransfer: createDataTransfer() })
    fireEvent.drop(third, { dataTransfer: createDataTransfer({ [FOLDER_DRAG_TYPE]: '2' }) })

    expect(onReorder).toHaveBeenCalledWith([1, 3, 2])
  })

  it('drop папки на папку другого уровня не вызывает onReorder', () => {
    const onReorder = vi.fn()
    const folders = [
      makeFolder(1, 'Родитель'),
      makeFolder(2, 'Дитя', { parent_id: 1 }),
    ]
    render(<FolderTree folders={folders} onReorder={onReorder} />)

    const child = screen.getByText('Дитя').closest('div') as HTMLElement
    const root = screen.getByText('Родитель').closest('div') as HTMLElement

    fireEvent.dragStart(child, { dataTransfer: createDataTransfer() })
    fireEvent.drop(root, { dataTransfer: createDataTransfer({ [FOLDER_DRAG_TYPE]: '2' }) })

    expect(onReorder).not.toHaveBeenCalled()
  })

  it('кнопка удаления системной папки отключена (negative)', () => {
    render(
      <FolderTree
        folders={[makeFolder(1, 'Системная', { is_default: true })]}
        onDelete={vi.fn()}
      />,
    )

    const deleteButton = screen.getByTitle('Системные папки нельзя удалить')
    expect(deleteButton).toBeDisabled()
  })
})
