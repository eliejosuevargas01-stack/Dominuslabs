import { describe, it, expect, afterEach } from 'vitest';
import { getDynamicApiUrl } from '../../services/api';

describe('getDynamicApiUrl', () => {
  const originalLocation = window.location;

  const setLocation = (hostname: string, protocol: string = 'http:') => {
    // Delete the window.location and mock it
    // @ts-ignore
    delete window.location;
    // @ts-ignore
    window.location = {
      ...originalLocation,
      hostname,
      protocol,
    } as any;
  };

  afterEach(() => {
    // @ts-ignore
    window.location = originalLocation as any;
  });

  it('should return local API URL with port 8001 when hostname is localhost', () => {
    setLocation('localhost');
    const result = getDynamicApiUrl();
    expect(result).toBe('http://localhost:8001/api/v1');
  });

  it('should return local API URL with port 8001 when hostname is 127.0.0.1', () => {
    setLocation('127.0.0.1');
    const result = getDynamicApiUrl();
    expect(result).toBe('http://127.0.0.1:8001/api/v1');
  });

  it('should return ngrok API URL without port when hostname ends with .ngrok-free.dev', () => {
    setLocation('test.ngrok-free.dev', 'https:');
    const result = getDynamicApiUrl();
    expect(result).toBe('https://test.ngrok-free.dev/api/v1');
  });

  it('should return ngrok API URL without port when hostname ends with .ngrok.io', () => {
    setLocation('my-app.ngrok.io', 'https:');
    const result = getDynamicApiUrl();
    expect(result).toBe('https://my-app.ngrok.io/api/v1');
  });

  it('should return standard fallback URL without port for any other hostname', () => {
    setLocation('production.example.com', 'https:');
    const result = getDynamicApiUrl();
    expect(result).toBe('https://production.example.com/api/v1');
  });

  it('should maintain the correct protocol based on window.location.protocol', () => {
    setLocation('example.com', 'http:');
    const resultHttp = getDynamicApiUrl();
    expect(resultHttp).toBe('http://example.com/api/v1');

    setLocation('example.com', 'https:');
    const resultHttps = getDynamicApiUrl();
    expect(resultHttps).toBe('https://example.com/api/v1');
  });
});

describe('Silent Reauth System', () => {
  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('detects expired tokens correctly', async () => {
    const { isTokenExpired } = await import('../../services/api');
    // Token with exp in the past
    const pastExp = Math.floor(Date.now() / 1000) - 100;
    const expiredToken = `eyJhbGciOiJIUzI1NiJ9.${btoa(JSON.stringify({ exp: pastExp }))}.sig`;
    expect(isTokenExpired(expiredToken)).toBe(true);

    // Token with exp in the future
    const futureExp = Math.floor(Date.now() / 1000) + 3600;
    const validToken = `eyJhbGciOiJIUzI1NiJ9.${btoa(JSON.stringify({ exp: futureExp }))}.sig`;
    expect(isTokenExpired(validToken)).toBe(false);
  });

  it('renews expired token silently using refresh token', async () => {
    const { getValidAccessToken } = await import('../../services/api');
    const pastExp = Math.floor(Date.now() / 1000) - 100;
    const expiredToken = `eyJhbGciOiJIUzI1NiJ9.${btoa(JSON.stringify({ exp: pastExp }))}.sig`;
    const newAccessToken = 'fresh_access_token';

    localStorage.setItem('admin_token', expiredToken);
    localStorage.setItem('admin_refresh_token', 'valid_refresh_token');

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        access_token: newAccessToken,
        refresh_token: 'new_refresh_token',
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const token = await getValidAccessToken();
    expect(token).toBe(newAccessToken);
    expect(localStorage.getItem('admin_token')).toBe(newAccessToken);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/auth/refresh'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ refresh_token: 'valid_refresh_token' }),
      })
    );
  });

  it('deduplicates concurrent refresh requests using mutex', async () => {
    const { getValidAccessToken } = await import('../../services/api');
    const pastExp = Math.floor(Date.now() / 1000) - 100;
    const expiredToken = `eyJhbGciOiJIUzI1NiJ9.${btoa(JSON.stringify({ exp: pastExp }))}.sig`;

    localStorage.setItem('admin_token', expiredToken);
    localStorage.setItem('admin_refresh_token', 'valid_refresh_token');

    const fetchMock = vi.fn().mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve({
        ok: true,
        json: async () => ({
          access_token: 'shared_new_token',
          refresh_token: 'shared_new_refresh_token',
        }),
      }), 10))
    );
    vi.stubGlobal('fetch', fetchMock);

    // Dispara 5 requisições de token concorrentes
    const [t1, t2, t3, t4, t5] = await Promise.all([
      getValidAccessToken(),
      getValidAccessToken(),
      getValidAccessToken(),
      getValidAccessToken(),
      getValidAccessToken(),
    ]);

    expect(t1).toBe('shared_new_token');
    expect(t2).toBe('shared_new_token');
    expect(t3).toBe('shared_new_token');
    expect(t4).toBe('shared_new_token');
    expect(t5).toBe('shared_new_token');
    // Deve ter chamado o endpoint /auth/refresh APENAS UMA VEZ
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe('connectWhatsappSession', () => {
  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('throws an error with the detail message from the response if it is a non-ok response', async () => {
    const { connectWhatsappSession } = await import('../../services/api');

    // Set up a valid token so fetchWithAuth doesn't throw early
    const futureExp = Math.floor(Date.now() / 1000) + 3600;
    const validToken = `eyJhbGciOiJIUzI1NiJ9.${btoa(JSON.stringify({ exp: futureExp }))}.sig`;
    localStorage.setItem('admin_token', validToken);

    const errorMessage = 'Custom backend error message';
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: errorMessage }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(connectWhatsappSession('session123')).rejects.toThrow(errorMessage);
  });

  it('throws a default error if the non-ok response does not contain a detail message or is invalid JSON', async () => {
    const { connectWhatsappSession } = await import('../../services/api');

    // Set up a valid token so fetchWithAuth doesn't throw early
    const futureExp = Math.floor(Date.now() / 1000) + 3600;
    const validToken = `eyJhbGciOiJIUzI1NiJ9.${btoa(JSON.stringify({ exp: futureExp }))}.sig`;
    localStorage.setItem('admin_token', validToken);

    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => { throw new Error('Invalid JSON'); },
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(connectWhatsappSession('session123')).rejects.toThrow('Falha ao solicitar código QR.');
  });
});
