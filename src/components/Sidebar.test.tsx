import '@testing-library/jest-dom';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Sidebar from './Sidebar';

describe('Sidebar Component', () => {
  const defaultProps = {
    handleLogout: vi.fn(),
    isCollapsed: false,
    setIsCollapsed: vi.fn(),
  };

  const renderSidebar = (props = defaultProps, initialRoute = '/') => {
    return render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <Sidebar {...props} />
      </MemoryRouter>
    );
  };

  it('renders Order Manager (PDV) link with ShoppingBag icon', () => {
    renderSidebar();

    const orderManagerLink = screen.getByRole('link', { name: /Order Manager \(PDV\)/i });
    expect(orderManagerLink).toBeInTheDocument();
    expect(orderManagerLink).toHaveAttribute('href', '/order-manager');

    const icon = orderManagerLink.querySelector('svg');
    expect(icon).toBeInTheDocument();
    expect(icon).toHaveClass('lucide-shopping-bag');
  });

  it('highlights the active link according to current path', () => {
    renderSidebar(defaultProps, '/order-manager');

    const orderManagerLink = screen.getByRole('link', { name: /Order Manager \(PDV\)/i });
    expect(orderManagerLink).toHaveClass('bg-purple-50', 'text-purple-700');

    const icon = orderManagerLink.querySelector('svg');
    expect(icon).toHaveClass('text-purple-600');
  });

  it('toggles mobile menu when clicking hamburger button', () => {
    renderSidebar();

    const openMenuBtn = screen.getByRole('button', { name: /Abrir menu/i });
    expect(openMenuBtn).toBeInTheDocument();

    fireEvent.click(openMenuBtn);

    const closeMenuBtn = screen.getByRole('button', { name: /Fechar menu/i });
    expect(closeMenuBtn).toBeInTheDocument();
  });

  it('renders mobile backdrop overlay when open and closes menu on backdrop click', () => {
    const { container } = renderSidebar();

    // Backdrop should not be present initially
    expect(container.querySelector('.bg-black\\/50')).not.toBeInTheDocument();

    // Open mobile menu
    const openMenuBtn = screen.getByRole('button', { name: /Abrir menu/i });
    fireEvent.click(openMenuBtn);

    // Backdrop should be rendered
    const backdrop = container.querySelector('.bg-black\\/50');
    expect(backdrop).toBeInTheDocument();
    expect(backdrop).toHaveClass('fixed', 'inset-0', 'z-30');

    // Clicking backdrop closes the menu
    fireEvent.click(backdrop!);
    expect(container.querySelector('.bg-black\\/50')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Abrir menu/i })).toBeInTheDocument();
  });

  it('calls setIsCollapsed when clicking collapse toggle button', () => {
    const setIsCollapsed = vi.fn();
    renderSidebar({ ...defaultProps, setIsCollapsed });

    const collapseBtn = screen.getByRole('button', { name: /Recolher menu/i });
    fireEvent.click(collapseBtn);

    expect(setIsCollapsed).toHaveBeenCalledWith(true);
  });

  it('calls handleLogout when clicking logout button', () => {
    const handleLogout = vi.fn();
    renderSidebar({ ...defaultProps, handleLogout });

    const logoutBtn = screen.getByTitle('Sair');
    fireEvent.click(logoutBtn);

    expect(handleLogout).toHaveBeenCalledTimes(1);
  });
});
