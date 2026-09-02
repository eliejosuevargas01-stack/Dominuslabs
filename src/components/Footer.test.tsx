import '@testing-library/jest-dom';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Footer from './Footer';
import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('Footer Component', () => {
  beforeEach(() => {
    // Mock window.scrollTo
    window.scrollTo = vi.fn();
  });

  const renderWithRouter = (ui: React.ReactElement) => {
    return render(<BrowserRouter>{ui}</BrowserRouter>);
  };

  it('renders without crashing', () => {
    renderWithRouter(<Footer />);
    expect(screen.getAllByText('Dominuslabs').length).toBeGreaterThan(0);
  });

  it('renders the correct social media links', () => {
    renderWithRouter(<Footer />);
    const linkedinLink = screen.getByTitle('LinkedIn de Eliezer');
    const instagramLink = screen.getByTitle('Instagram de Eliezer');

    expect(linkedinLink).toHaveAttribute('href', 'https://www.linkedin.com/in/eliezer-josue-vargas-gamboa-1b2074417/');
    expect(instagramLink).toHaveAttribute('href', 'https://www.instagram.com/eliejosuevargas01/');
  });

  it('scrolls to top when scroll to top button is clicked', () => {
    renderWithRouter(<Footer />);
    const scrollToTopBtn = screen.getByTitle('Voltar ao topo');
    fireEvent.click(scrollToTopBtn);

    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, behavior: 'smooth' });
  });

  it('calls onTabSelect and scrolls to top when a tab is clicked', () => {
    const mockOnTabSelect = vi.fn();
    renderWithRouter(<Footer onTabSelect={mockOnTabSelect} />);

    const completedCasesBtn = screen.getByText('Cases Concluídos');
    fireEvent.click(completedCasesBtn);

    expect(mockOnTabSelect).toHaveBeenCalledWith('completed');
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, behavior: 'smooth' });
  });

  it('renders Links when onTabSelect is not provided', () => {
    renderWithRouter(<Footer />);
    const casesLinks = screen.getAllByRole('link', { name: /Cases de Sucesso|Cases Concluídos|Em Progresso/i });
    expect(casesLinks.length).toBeGreaterThan(0);
  });
});
