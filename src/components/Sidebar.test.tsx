import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Sidebar from './Sidebar';

describe('Sidebar Component', () => {
  const mockHandleLogout = vi.fn();
  const mockSetIsCollapsed = vi.fn();

  const defaultProps = {
    handleLogout: mockHandleLogout,
    isCollapsed: false,
    setIsCollapsed: mockSetIsCollapsed,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all main elements', () => {
    render(
      <MemoryRouter>
        <Sidebar {...defaultProps} />
      </MemoryRouter>
    );

    // Check for logo text
    expect(screen.getByText('Dominuslabs')).toBeInTheDocument();

    // Check for some main links
    expect(screen.getByText('Resumo Operacional')).toBeInTheDocument();
    expect(screen.getByText('CRM & Pipeline Pedidos')).toBeInTheDocument();
    expect(screen.getByText('Project Hub')).toBeInTheDocument();
    expect(screen.getByText('Sair')).toBeInTheDocument();
  });

  it('calls handleLogout when logout button is clicked', () => {
    render(
      <MemoryRouter>
        <Sidebar {...defaultProps} />
      </MemoryRouter>
    );

    const logoutButton = screen.getByTitle('Sair');
    fireEvent.click(logoutButton);

    expect(mockHandleLogout).toHaveBeenCalledTimes(1);
  });

  it('calls setIsCollapsed when collapse toggle is clicked', () => {
    render(
      <MemoryRouter>
        <Sidebar {...defaultProps} />
      </MemoryRouter>
    );

    const toggleButton = screen.getByTitle('Recolher menu');
    fireEvent.click(toggleButton);

    expect(mockSetIsCollapsed).toHaveBeenCalledWith(true);
  });

  it('shows expand icon and correct title when collapsed', () => {
    render(
      <MemoryRouter>
        <Sidebar {...defaultProps} isCollapsed={true} />
      </MemoryRouter>
    );

    const toggleButton = screen.getByTitle('Expandir menu');
    expect(toggleButton).toBeInTheDocument();
  });

  it('highlights the active route correctly', () => {
    render(
      <MemoryRouter initialEntries={['/crm']}>
        <Sidebar {...defaultProps} />
      </MemoryRouter>
    );

    const crmLink = screen.getByTitle('CRM & Pipeline Pedidos');
    expect(crmLink).toHaveClass('bg-purple-50 text-purple-700');
  });

  it('highlights Project Hub for sub-routes correctly', () => {
    render(
      <MemoryRouter initialEntries={['/project-hub/projects/1']}>
        <Sidebar {...defaultProps} />
      </MemoryRouter>
    );

    const projectHubLink = screen.getByTitle('Project Hub');
    expect(projectHubLink).toHaveClass('bg-purple-50 text-purple-700');
  });

  it('toggles mobile menu on hamburger click', () => {
    render(
      <MemoryRouter>
        <Sidebar {...defaultProps} />
      </MemoryRouter>
    );

    const hamburger = screen.getByLabelText('Abrir menu');
    fireEvent.click(hamburger);

    const closeButton = screen.getByLabelText('Fechar menu');
    expect(closeButton).toBeInTheDocument();

    fireEvent.click(closeButton);
    expect(screen.getByLabelText('Abrir menu')).toBeInTheDocument();
  });
});
