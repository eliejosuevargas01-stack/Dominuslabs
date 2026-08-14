import { describe, it, expect, afterEach } from 'vitest';
import { getDynamicApiUrl } from '../../services/api';

describe('getDynamicApiUrl', () => {
  const originalLocation = window.location;

  const setLocation = (hostname: string, protocol: string = 'http:') => {
    // Delete the window.location and mock it
    // @ts-ignore
    delete window.location;
    window.location = {
      ...originalLocation,
      hostname,
      protocol,
    };
  };

  afterEach(() => {
    window.location = originalLocation;
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
