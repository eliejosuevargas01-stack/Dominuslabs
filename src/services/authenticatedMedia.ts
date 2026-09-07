import { useEffect, useState } from 'react';

import { API_BASE, fetchWithAuth } from './api';

const isProtectedMediaPath = (pathname: string): boolean => (
  /\/whatsapp\/sessions\/[^/]+\/(avatar|media)$/.test(pathname)
  || /\/crm\/(avatar|media)$/.test(pathname)
  || /\/api\/sessions\/[^/]+\/(avatar|media)$/.test(pathname)
  || pathname === '/avatar'
  || pathname === '/media'
);

function parseResourceUrl(sourceUrl: string): URL | null {
  try {
    const apiBaseUrl = new URL(API_BASE, window.location.origin);
    return new URL(sourceUrl, apiBaseUrl.origin);
  } catch {
    return null;
  }
}
export function isAuthenticatedMediaUrl(sourceUrl: string): boolean {
  const parsed = parseResourceUrl(sourceUrl);
  if (!parsed) return false;

  const apiBaseUrl = new URL(API_BASE, window.location.origin);
  return parsed.origin === apiBaseUrl.origin && isProtectedMediaPath(parsed.pathname);
}

export function sanitizeAuthenticatedMediaUrl(sourceUrl: string): string {
  const parsed = parseResourceUrl(sourceUrl);
  if (!parsed || !isAuthenticatedMediaUrl(sourceUrl)) return sourceUrl;

  parsed.searchParams.delete('token');
  return parsed.toString();
}

interface AuthenticatedBlobUrlState {
  resolvedUrl: string | null;
  isLoading: boolean;
  hasError: boolean;
}

export function useAuthenticatedBlobUrl(
  sourceUrl: string | null,
  enabled: boolean = true,
): AuthenticatedBlobUrlState {
  const protectedResource = Boolean(sourceUrl && isAuthenticatedMediaUrl(sourceUrl));
  const safeSourceUrl = sourceUrl ? sanitizeAuthenticatedMediaUrl(sourceUrl) : null;
  const [blobState, setBlobState] = useState<{
    sourceUrl: string | null;
    objectUrl: string | null;
    isLoading: boolean;
    hasError: boolean;
  }>({ sourceUrl: null, objectUrl: null, isLoading: false, hasError: false });

  useEffect(() => {
    if (!safeSourceUrl || !protectedResource || !enabled) return undefined;

    const controller = new AbortController();
    let disposed = false;
    let createdObjectUrl: string | null = null;
    // This reset is part of the external request lifecycle and prevents a
    // revoked Blob URL from a previous source from being rendered again.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setBlobState({
      sourceUrl: safeSourceUrl,
      objectUrl: null,
      isLoading: true,
      hasError: false,
    });

    void fetchWithAuth(safeSourceUrl, { signal: controller.signal }, null)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Falha ao carregar mídia autenticada (${response.status}).`);
        }
        const blob = await response.blob();
        createdObjectUrl = URL.createObjectURL(blob);
        if (disposed) {
          URL.revokeObjectURL(createdObjectUrl);
          createdObjectUrl = null;
          return;
        }
        setBlobState({
          sourceUrl: safeSourceUrl,
          objectUrl: createdObjectUrl,
          isLoading: false,
          hasError: false,
        });
      })
      .catch((error: unknown) => {
        if (disposed || (error instanceof DOMException && error.name === 'AbortError')) return;
        setBlobState({
          sourceUrl: safeSourceUrl,
          objectUrl: null,
          isLoading: false,
          hasError: true,
        });
      });

    return () => {
      disposed = true;
      controller.abort();
      if (createdObjectUrl) URL.revokeObjectURL(createdObjectUrl);
    };
  }, [enabled, protectedResource, safeSourceUrl]);

  if (!safeSourceUrl) {
    return { resolvedUrl: null, isLoading: false, hasError: false };
  }
  if (!protectedResource) {
    return { resolvedUrl: safeSourceUrl, isLoading: false, hasError: false };
  }
  if (!enabled || blobState.sourceUrl !== safeSourceUrl) {
    return { resolvedUrl: null, isLoading: enabled, hasError: false };
  }
  return {
    resolvedUrl: blobState.objectUrl,
    isLoading: blobState.isLoading,
    hasError: blobState.hasError,
  };
}
