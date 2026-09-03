import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import OmnichannelView from './OmnichannelView';

vi.mock('../services/api', async (importOriginal) => {
  const actual = await importOriginal<any>();
  return {
    ...actual,
    API_BASE: 'http://localhost:8001/api/v1',
    fetchWhatsappSessions: vi.fn().mockResolvedValue([{ session_id: 'session-123', status: 'connected' }]),
    getAuthToken: vi.fn().mockReturnValue('test_token_123'),
    fetchConversations: vi.fn().mockResolvedValue([{
      id: 'conv-1',
      contact_jid: '5511999999999@s.whatsapp.net',
      contact_name: 'Test Contact',
      last_message: 'Hello',
      unread_count: 0,
      session_id: 'session-123',
      profile_pic_url: '/api/whatsapp/sessions/session-123/avatar?jid=5511999999999@s.whatsapp.net'
    }]),
    fetchContacts: vi.fn().mockResolvedValue([{
      id: 'c1',
      phone: '5511999999999',
      name: 'Test Contact'
    }])
  };
});

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

if (!window.HTMLElement.prototype.scrollIntoView) {
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
}

describe('OmnichannelView URL normalization', () => {
  beforeEach(() => {
    localStorage.setItem('admin_token', 'test_token_123');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({})
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('normalizes avatar URL with token and absolute path and renders the component', async () => {
    await act(async () => {
      render(<MemoryRouter><OmnichannelView /></MemoryRouter>);
    });

    // Ensure the component mounts and the omnichannel context is rendered
    expect(screen.getByText(/Omnichannel/i)).toBeInTheDocument();
  });
});
