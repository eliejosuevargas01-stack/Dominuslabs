import '@testing-library/jest-dom';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import Login from './Login';
import * as api from '../services/api';
import { toast } from 'sonner';

// Mock the services
vi.mock('../services/api', () => ({
  loginUser: vi.fn(),
}));

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock sonner
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock lucide-react to avoid issues with icon rendering
vi.mock('lucide-react', () => ({
  Lock: () => <span data-testid="icon-lock" />,
  User: () => <span data-testid="icon-user" />,
  Loader2: () => <span data-testid="icon-loader2" />,
  Sparkles: () => <span data-testid="icon-sparkles" />,
  Eye: () => <span data-testid="icon-eye" />,
  EyeOff: () => <span data-testid="icon-eye-off" />,
}));

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderLogin = () => {
    return render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );
  };

  it('renders login form correctly', () => {
    renderLogin();
    expect(screen.getByPlaceholderText('ex: admin')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /entrar na plataforma/i })).toBeInTheDocument();
  });

  it('toggles password visibility when the eye icon is clicked', () => {
    renderLogin();
    const passwordInput = screen.getByPlaceholderText('••••••••');
    const toggleButton = screen.getByRole('button', { name: /mostrar senha/i });

    expect(passwordInput).toHaveAttribute('type', 'password');

    fireEvent.click(toggleButton);

    expect(passwordInput).toHaveAttribute('type', 'text');
    expect(screen.getByRole('button', { name: /ocultar senha/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /ocultar senha/i }));
    expect(passwordInput).toHaveAttribute('type', 'password');
  });

  it('shows validation error if form is submitted empty', async () => {
    renderLogin();

    fireEvent.submit(screen.getByRole('button', { name: /entrar na plataforma/i }).closest('form')!);

    await waitFor(() => {
      expect(screen.getByText('Por favor preencha todos os campos.')).toBeInTheDocument();
    });
    expect(api.loginUser).not.toHaveBeenCalled();
  });

  it('shows validation error if only username is provided', async () => {
    renderLogin();
    const usernameInput = screen.getByPlaceholderText('ex: admin');

    fireEvent.change(usernameInput, { target: { value: 'admin' } });
    fireEvent.submit(screen.getByRole('button', { name: /entrar na plataforma/i }).closest('form')!);

    await waitFor(() => {
      expect(screen.getByText('Por favor preencha todos os campos.')).toBeInTheDocument();
    });
    expect(api.loginUser).not.toHaveBeenCalled();
  });

  it('handles successful login and redirects to /project-hub', async () => {
    (api.loginUser as vi.Mock).mockResolvedValueOnce({
      access_token: 'mock-access-token',
      refresh_token: 'mock-refresh-token',
      whatsapp_token: 'mock-wa-token'
    });

    renderLogin();

    fireEvent.change(screen.getByPlaceholderText('ex: admin'), { target: { value: 'testuser' } });
    fireEvent.change(screen.getByPlaceholderText('••••••••'), { target: { value: 'password123' } });

    fireEvent.submit(screen.getByRole('button', { name: /entrar na plataforma/i }).closest('form')!);

    await waitFor(() => {
      expect(api.loginUser).toHaveBeenCalledWith('testuser', 'password123');
    });

    expect(localStorage.getItem('admin_token')).toBe('mock-access-token');
    expect(localStorage.getItem('admin_refresh_token')).toBe('mock-refresh-token');
    expect(localStorage.getItem('whatsapp_token')).toBe('mock-wa-token');

    expect(mockNavigate).toHaveBeenCalledWith('/project-hub');
    expect(toast.success).toHaveBeenCalledWith('Login efetuado com sucesso!');
  });

  it('handles failed login and shows error toast', async () => {
    (api.loginUser as vi.Mock).mockRejectedValueOnce(new Error('Invalid credentials'));

    renderLogin();

    fireEvent.change(screen.getByPlaceholderText('ex: admin'), { target: { value: 'testuser' } });
    fireEvent.change(screen.getByPlaceholderText('••••••••'), { target: { value: 'wrongpass' } });

    fireEvent.submit(screen.getByRole('button', { name: /entrar na plataforma/i }).closest('form')!);

    await waitFor(() => {
      expect(api.loginUser).toHaveBeenCalledWith('testuser', 'wrongpass');
    });

    expect(toast.error).toHaveBeenCalledWith('Credenciais inválidas ou erro no servidor. Tente novamente.');
    expect(screen.getByText('Credenciais inválidas ou erro no servidor. Tente novamente.')).toBeInTheDocument();
  });

  it('redirects automatically if already logged in', () => {
    localStorage.setItem('admin_token', 'existing-token');

    renderLogin();

    expect(mockNavigate).toHaveBeenCalledWith('/project-hub');
  });
});
