import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const apiMocks = vi.hoisted(() => ({
  API_BASE: 'https://app.example/api/v1',
  fetchWithAuth: vi.fn(),
}));

vi.mock('../services/api', () => apiMocks);

import { AuthenticatedImage } from './AuthenticatedMedia';

describe('AuthenticatedImage', () => {
  const createObjectURL = vi.fn(() => 'blob:authenticated-media');
  const revokeObjectURL = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: createObjectURL,
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: revokeObjectURL,
    });
    apiMocks.fetchWithAuth.mockResolvedValue({
      ok: true,
      status: 200,
      blob: async () => new Blob(['authenticated-image'], { type: 'image/png' }),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loads a private proxy through Authorization and revokes the Blob URL', async () => {
    const { unmount } = render(
      <AuthenticatedImage
        sourceUrl="https://app.example/api/v1/whatsapp/sessions/session-a/avatar?jid=contact%40s.whatsapp.net&token=legacy-jwt"
        deferUntilVisible={false}
        alt="Avatar privado"
      />,
    );

    await waitFor(() => expect(screen.getByAltText('Avatar privado')).toHaveAttribute('src', 'blob:authenticated-media'));
    expect(apiMocks.fetchWithAuth).toHaveBeenCalledTimes(1);
    const [requestedUrl, options, contentType] = apiMocks.fetchWithAuth.mock.calls[0] as [
      string,
      RequestInit,
      null,
    ];
    const parsedUrl = new URL(requestedUrl);
    expect(parsedUrl.searchParams.get('jid')).toBe('contact@s.whatsapp.net');
    expect(parsedUrl.searchParams.has('token')).toBe(false);
    expect(options.signal).toBeInstanceOf(AbortSignal);
    expect(contentType).toBeNull();

    unmount();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:authenticated-media');
  });

  it('keeps public CDN images direct and never sends the Bearer token', () => {
    render(
      <AuthenticatedImage
        sourceUrl="https://pps.whatsapp.net/avatar.jpg"
        alt="Avatar público"
      />,
    );

    expect(screen.getByAltText('Avatar público')).toHaveAttribute('src', 'https://pps.whatsapp.net/avatar.jpg');
    expect(apiMocks.fetchWithAuth).not.toHaveBeenCalled();
  });
});
