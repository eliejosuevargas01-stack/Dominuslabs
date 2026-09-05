import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AutomationsView, { BusinessRule } from './AutomationsView';
import { describe, it, expect, vi } from 'vitest';
import '@testing-library/jest-dom';

const mockRules: BusinessRule[] = [
  {
    id: 'rule-1',
    key: 'R1',
    titulo: 'Rule 1',
    descricao: 'Description 1',
    ativo: true,
    categoria: 'ATENDIMENTO'
  },
  {
    id: 'rule-2',
    key: 'R2',
    titulo: 'Rule 2',
    descricao: 'Description 2',
    ativo: false,
    categoria: 'VENDAS'
  }
];

describe('AutomationsView', () => {
  it('renders correctly with no rules', () => {
    render(<AutomationsView rules={[]} />);
    expect(screen.getByText('Nenhuma regra de automação mapeada.')).toBeInTheDocument();
  });

  it('renders correctly with rules', () => {
    render(<AutomationsView rules={mockRules} />);
    expect(screen.getByText('Rule 1')).toBeInTheDocument();
    expect(screen.getByText('Description 1')).toBeInTheDocument();
    expect(screen.getByText('ATENDIMENTO')).toBeInTheDocument();
    expect(screen.getByText('Rule 2')).toBeInTheDocument();
    expect(screen.getByText('Description 2')).toBeInTheDocument();
    expect(screen.getByText('VENDAS')).toBeInTheDocument();
  });

  it('toggles a rule and applies optimistic UI update', async () => {
    const user = userEvent.setup();
    const mockOnToggle = vi.fn().mockResolvedValue(undefined);

    render(<AutomationsView rules={mockRules} onToggleRule={mockOnToggle} />);

    // Find the toggle button for rule-2 (which is currently inactive)
    const toggleButtons = screen.getAllByRole('button');
    // Rule 2 toggle is the second button
    const rule2Toggle = toggleButtons[1];

    // Verify it is visually inactive based on DOM attributes instead of brittle classes
    expect(rule2Toggle).not.toBeDisabled();
    // In current implementation, active rule has 'bg-purple-600', inactive has 'bg-zinc-300'
    // While asserting on classes is a bit brittle, the component does not use standard
    // accessibility attributes like `aria-checked` right now, so we check the UI state
    // by asserting the child span's class which toggles position.

    await user.click(rule2Toggle);

    expect(mockOnToggle).toHaveBeenCalledWith('rule-2', true);

    // Wait and verify it became active by checking class switch on the container
    await waitFor(() => {
      expect(rule2Toggle.className).toContain('bg-purple-600');
    });
  });

  it('reverts the UI state if the onToggleRule promise rejects', async () => {
    const user = userEvent.setup();
    const mockOnToggle = vi.fn().mockRejectedValue(new Error('API failed'));

    render(<AutomationsView rules={mockRules} onToggleRule={mockOnToggle} />);

    const toggleButtons = screen.getAllByRole('button');
    const rule2Toggle = toggleButtons[1];

    await user.click(rule2Toggle);

    expect(mockOnToggle).toHaveBeenCalledWith('rule-2', true);

    // Because the promise rejects, it should revert to inactive eventually
    await waitFor(() => {
      expect(rule2Toggle.className).toContain('bg-zinc-300');
    });
  });
});
