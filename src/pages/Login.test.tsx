import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { BrowserRouter } from 'react-router-dom';

const { toastError, toastSuccess } = vi.hoisted(() => ({ toastError: vi.fn(), toastSuccess: vi.fn() }));
vi.mock('sonner', () => ({ toast: { success: toastSuccess, error: toastError } }));

import { loginUser } from '../services/api';
vi.mock('../services/api', () => ({
  loginUser: vi.fn(),
}));

import Login from './Login';

describe('Login', () => {
  beforeEach(() => {
    toastError.mockClear();
    toastSuccess.mockClear();
    vi.mocked(loginUser).mockClear();
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderComponent = () => {
    return render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    );
  };

  it('displays error message and toast when login fails', async () => {
    const user = userEvent.setup();
    vi.mocked(loginUser).mockRejectedValue(new Error('Login failed'));

    renderComponent();

    const usernameInput = screen.getByRole('textbox', { name: /usuário/i });
    const passwordInput = screen.getByPlaceholderText(/••••••••/i);
    const submitButton = screen.getByRole('button', { name: /entrar na plataforma/i });

    await user.type(usernameInput, 'testuser');
    await user.type(passwordInput, 'wrongpass');
    await user.click(submitButton);

    await waitFor(() => {
      expect(loginUser).toHaveBeenCalledWith('testuser', 'wrongpass');
    });

    const errorMessage = 'Credenciais inválidas ou erro no servidor. Tente novamente.';
    expect(toastError).toHaveBeenCalledWith(errorMessage);
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });
});
