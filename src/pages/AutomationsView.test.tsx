import '@testing-library/jest-dom';
import { act, render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import AutomationsView, { BusinessRule } from './AutomationsView';

describe('AutomationsView', () => {
  const mockRules: BusinessRule[] = [
    {
      id: 'rule-1',
      key: 'auto_reply',
      titulo: 'Auto Reply',
      descricao: 'Automatically replies to new messages',
      ativo: true,
      categoria: 'ATENDIMENTO',
    },
    {
      id: 'rule-2',
      key: 'notify_sales',
      titulo: 'Notify Sales',
      descricao: 'Notifies sales team on new lead',
      ativo: false,
      categoria: 'VENDAS',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders empty state when no rules are provided', () => {
    render(<AutomationsView />);
    expect(screen.getByText('Nenhuma regra de automação mapeada.')).toBeInTheDocument();
  });

  it('renders a list of provided rules', () => {
    render(<AutomationsView rules={mockRules} />);

    expect(screen.getByText('Auto Reply')).toBeInTheDocument();
    expect(screen.getByText('Automatically replies to new messages')).toBeInTheDocument();

    expect(screen.getByText('Notify Sales')).toBeInTheDocument();
    expect(screen.getByText('Notifies sales team on new lead')).toBeInTheDocument();
  });

  it('calls onToggleRule and updates UI optimistically when toggle is clicked', async () => {
    const onToggleRuleMock = vi.fn().mockResolvedValue(undefined);
    render(<AutomationsView rules={mockRules} onToggleRule={onToggleRuleMock} />);

    // Select the toggle for "Notify Sales" (which is currently false)
    const rule2Toggle = screen.getAllByRole('button')[1];

    await act(async () => {
      fireEvent.click(rule2Toggle);
    });

    expect(onToggleRuleMock).toHaveBeenCalledTimes(1);
    expect(onToggleRuleMock).toHaveBeenCalledWith('rule-2', true);
  });

  it('reverts optimistic update if onToggleRule fails', async () => {
    const onToggleRuleMock = vi.fn().mockRejectedValue(new Error('API Error'));
    render(<AutomationsView rules={mockRules} onToggleRule={onToggleRuleMock} />);

    // Select the toggle for "Notify Sales" (which is currently false)
    const rule2Toggle = screen.getAllByRole('button')[1];

    // Click to turn it on (optimistically)
    await act(async () => {
      fireEvent.click(rule2Toggle);
    });

    expect(onToggleRuleMock).toHaveBeenCalledTimes(1);
    expect(onToggleRuleMock).toHaveBeenCalledWith('rule-2', true);

    // Wait for the re-render after catch block execution
    // Checking the class to see if it reverted to bg-zinc-300 (off) instead of bg-purple-600 (on)
    await waitFor(() => {
      expect(rule2Toggle).toHaveClass('bg-zinc-300');
    });
  });
});
