/**
 * Documentation-Driven Testing:
 * O comportamento esperado para testes:
 * - Arquivos de teste verificam a lógica renderizada.
 */

import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, it, expect } from 'vitest';
import ProgressBar from './ProgressBar';

describe('ProgressBar Component', () => {
  it('renders correctly with given progress', () => {
    render(<ProgressBar progress={50} />);
    expect(screen.getByText('Progresso Geral')).toBeInTheDocument();
    expect(screen.getByText('50% Concluído')).toBeInTheDocument();
  });

  it('clamps progress to a maximum of 100', () => {
    render(<ProgressBar progress={150} />);
    expect(screen.getByText('100% Concluído')).toBeInTheDocument();
  });

  it('clamps progress to a minimum of 0', () => {
    render(<ProgressBar progress={-20} />);
    expect(screen.getByText('0% Concluído')).toBeInTheDocument();
  });
});
