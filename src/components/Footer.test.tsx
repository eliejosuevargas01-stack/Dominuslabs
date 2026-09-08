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

  it('renders styled column headers with updated high-contrast class', () => {
    renderWithRouter(<Footer />);
    const solucaoHeader = screen.getByRole('heading', { name: /Soluções/i });
    const navegacaoHeader = screen.getByRole('heading', { name: /Navegação/i });
    const contatoHeader = screen.getByRole('heading', { name: /Contato/i });

    expect(solucaoHeader).toHaveClass('text-slate-100');
    expect(navegacaoHeader).toHaveClass('text-slate-100');
    expect(contatoHeader).toHaveClass('text-slate-100');
  });

  it('renders contact information with direct email and WhatsApp link', () => {
    renderWithRouter(<Footer />);
    expect(screen.getByText('contato@dominuslabs.online')).toBeInTheDocument();
    const whatsappLink = screen.getByRole('link', { name: /Falar no WhatsApp/i });
    expect(whatsappLink).toHaveAttribute('href', 'https://wa.me/5547991362164');
  });
});
