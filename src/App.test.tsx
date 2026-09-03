import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from './App';

describe('ProtectedRoute', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  const renderProtectedRoute = (token: string | null) => {
    if (token !== null) {
      localStorage.setItem('admin_token', token);
    }

    render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route path="/login" element={<div data-testid="login-page">Login Page</div>} />
          <Route
            path="/protected"
            element={
              <ProtectedRoute>
                <div data-testid="protected-content">Protected Content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );
  };

  it('renders children when valid token exists', () => {
    renderProtectedRoute('valid-token');
    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
    expect(screen.queryByTestId('login-page')).not.toBeInTheDocument();
  });

  it('redirects to login when token is missing', () => {
    renderProtectedRoute(null);
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    expect(localStorage.getItem('admin_token')).toBeNull();
  });

  it('redirects to login when token is "null"', () => {
    renderProtectedRoute('null');
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    expect(localStorage.getItem('admin_token')).toBeNull();
  });

  it('redirects to login when token is "undefined"', () => {
    renderProtectedRoute('undefined');
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    expect(localStorage.getItem('admin_token')).toBeNull();
  });

  it('redirects to login when token is an empty string', () => {
    renderProtectedRoute('');
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    expect(localStorage.getItem('admin_token')).toBeNull();
  });
});
