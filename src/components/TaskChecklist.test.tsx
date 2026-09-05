
import { beforeAll, afterAll } from 'vitest';

const originalConsoleError = console.error;
beforeAll(() => {
  console.error = vi.fn();
});
afterAll(() => {
  console.error = originalConsoleError;
});
/**
 * Documentation-Driven Testing:
 * O comportamento esperado para testes:
 * - Arquivos de teste verificam a lógica renderizada de TaskChecklist
 * - Testar o comportamento das chamadas de API mockadas e permissões.
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import TaskChecklist from './TaskChecklist';
import * as api from '../services/api';
import { toast } from 'sonner';

// Mock the API module
vi.mock('../services/api', () => ({
  fetchTasks: vi.fn(),
  createTask: vi.fn(),
  updateTask: vi.fn(),
}));

// Mock sonner
vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
  },
}));

describe('TaskChecklist Component', () => {
  const mockTasks = [
    { id: 1, name: 'Task 1', status: 'PENDING' },
    { id: 2, name: 'Task 2', status: 'DONE' },
    { id: 3, name: 'Task 3', status: 'DONE', completed_by_github: true },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    render(<TaskChecklist projectId="1" admin={true} />);
    expect(screen.getByText(/Carregando checklist\.\.\./i)).toBeInTheDocument();
  });

  it('renders tasks after fetching', async () => {
    vi.mocked(api.fetchTasks).mockResolvedValue(mockTasks);

    render(<TaskChecklist projectId="1" admin={true} />);

    await waitFor(() => {
      expect(screen.queryByText(/Carregando checklist\.\.\./i)).not.toBeInTheDocument();
    });

    expect(screen.getByText('Task 1')).toBeInTheDocument();
    expect(screen.getByText('Task 2')).toBeInTheDocument();
    expect(screen.getByText('Task 3')).toBeInTheDocument();
  });

  it('renders empty state when no tasks are returned', async () => {
    vi.mocked(api.fetchTasks).mockResolvedValue([]);

    render(<TaskChecklist projectId="1" admin={true} />);

    await waitFor(() => {
      expect(screen.queryByText(/Carregando checklist\.\.\./i)).not.toBeInTheDocument();
    });

    expect(screen.getByText('Nenhuma tarefa cadastrada.')).toBeInTheDocument();
  });

  it('displays an error message when fetching tasks fails', async () => {
    vi.mocked(api.fetchTasks).mockRejectedValue(new Error('Network error'));

    render(<TaskChecklist projectId="1" admin={true} />);

    await waitFor(() => {
      expect(screen.getByText('Erro ao carregar tarefas.')).toBeInTheDocument();
    });

    expect(toast.error).toHaveBeenCalledWith('Ocorreu um erro na operacao.');
  });

  it('allows admin to add a new task', async () => {
    vi.mocked(api.fetchTasks).mockResolvedValue(mockTasks);
    vi.mocked(api.createTask).mockResolvedValue({ id: 4, name: 'New Task', status: 'PENDING' });
    const mockOnTasksUpdated = vi.fn();

    render(<TaskChecklist projectId="1" admin={true} onTasksUpdated={mockOnTasksUpdated} />);

    await waitFor(() => {
      expect(screen.queryByText(/Carregando checklist\.\.\./i)).not.toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText('Nova tarefa...');
    const addButton = screen.getByRole('button', { name: /Adicionar nova tarefa/i });

    fireEvent.change(input, { target: { value: 'New Task' } });
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(api.createTask).toHaveBeenCalledWith("1", { name: 'New Task', status: 'PENDING' });
    });

    expect(mockOnTasksUpdated).toHaveBeenCalled();
    expect(screen.getByText('New Task')).toBeInTheDocument();
  });

  it('does not allow admin to add an empty task', async () => {
    vi.mocked(api.fetchTasks).mockResolvedValue(mockTasks);

    render(<TaskChecklist projectId="1" admin={true} />);

    await waitFor(() => {
      expect(screen.queryByText(/Carregando checklist\.\.\./i)).not.toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText('Nova tarefa...');
    const addButton = screen.getByRole('button', { name: /Adicionar nova tarefa/i });

    fireEvent.change(input, { target: { value: '   ' } }); // only whitespace
    fireEvent.click(addButton);

    expect(api.createTask).not.toHaveBeenCalled();
  });

  it('does not render the add task form for non-admins', async () => {
    vi.mocked(api.fetchTasks).mockResolvedValue(mockTasks);

    render(<TaskChecklist projectId="1" admin={false} />);

    await waitFor(() => {
      expect(screen.queryByText(/Carregando checklist\.\.\./i)).not.toBeInTheDocument();
    });

    expect(screen.queryByPlaceholderText('Nova tarefa...')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Adicionar nova tarefa/i })).not.toBeInTheDocument();
  });

  it('allows admin to toggle a task status', async () => {
    vi.mocked(api.fetchTasks).mockResolvedValue(mockTasks);
    vi.mocked(api.updateTask).mockResolvedValue({});
    const mockOnTasksUpdated = vi.fn();

    render(<TaskChecklist projectId="1" admin={true} onTasksUpdated={mockOnTasksUpdated} />);

    await waitFor(() => {
      expect(screen.queryByText(/Carregando checklist\.\.\./i)).not.toBeInTheDocument();
    });

    const task1 = screen.getByText('Task 1');
    fireEvent.click(task1.closest('li')!);

    await waitFor(() => {
      expect(api.updateTask).toHaveBeenCalledWith(1, { status: 'DONE' });
    });

    expect(mockOnTasksUpdated).toHaveBeenCalled();
  });

  it('does not allow non-admins to toggle a task status', async () => {
    vi.mocked(api.fetchTasks).mockResolvedValue(mockTasks);

    render(<TaskChecklist projectId="1" admin={false} />);

    await waitFor(() => {
      expect(screen.queryByText(/Carregando checklist\.\.\./i)).not.toBeInTheDocument();
    });

    const task1 = screen.getByText('Task 1');
    fireEvent.click(task1.closest('li')!);

    expect(api.updateTask).not.toHaveBeenCalled();
  });

  it('does not allow admin to toggle a github completed task', async () => {
    vi.mocked(api.fetchTasks).mockResolvedValue(mockTasks);

    render(<TaskChecklist projectId="1" admin={true} />);

    await waitFor(() => {
      expect(screen.queryByText(/Carregando checklist\.\.\./i)).not.toBeInTheDocument();
    });

    const task3 = screen.getByText('Task 3');
    fireEvent.click(task3.closest('li')!);

    expect(api.updateTask).not.toHaveBeenCalled();
  });

  it('handles errors when toggling a task fails', async () => {
    vi.mocked(api.fetchTasks).mockResolvedValue(mockTasks);
    vi.mocked(api.updateTask).mockRejectedValue(new Error('Update failed'));

    render(<TaskChecklist projectId="1" admin={true} />);

    await waitFor(() => {
      expect(screen.queryByText(/Carregando checklist\.\.\./i)).not.toBeInTheDocument();
    });

    const task1 = screen.getByText('Task 1');
    fireEvent.click(task1.closest('li')!);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Ocorreu um erro na operacao.');
    });
  });

  it('handles errors when adding a task fails', async () => {
    vi.mocked(api.fetchTasks).mockResolvedValue(mockTasks);
    vi.mocked(api.createTask).mockRejectedValue(new Error('Create failed'));

    render(<TaskChecklist projectId="1" admin={true} />);

    await waitFor(() => {
      expect(screen.queryByText(/Carregando checklist\.\.\./i)).not.toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText('Nova tarefa...');
    const addButton = screen.getByRole('button', { name: /Adicionar nova tarefa/i });

    fireEvent.change(input, { target: { value: 'New Task' } });
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Ocorreu um erro na operacao.');
      expect(screen.getByText('Erro ao criar tarefa.')).toBeInTheDocument();
    });
  });
});
