import React, { useEffect, useRef, useState } from 'react';

import {
  isAuthenticatedMediaUrl,
  useAuthenticatedBlobUrl,
} from '../services/authenticatedMedia';

function useNearViewport<T extends Element>(enabled: boolean): {
  elementRef: React.RefObject<T | null>;
  isNearViewport: boolean;
} {
  const elementRef = useRef<T>(null);
  const [isNearViewport, setIsNearViewport] = useState(
    !enabled || typeof IntersectionObserver === 'undefined',
  );

  useEffect(() => {
    if (!enabled || typeof IntersectionObserver === 'undefined' || !elementRef.current) return undefined;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setIsNearViewport(true);
          observer.disconnect();
        }
      },
      { rootMargin: '240px' },
    );
    observer.observe(elementRef.current);
    return () => observer.disconnect();
  }, [enabled]);

  return { elementRef, isNearViewport };
}

interface AuthenticatedImageProps extends Omit<React.ImgHTMLAttributes<HTMLImageElement>, 'src'> {
  sourceUrl: string;
  deferUntilVisible?: boolean;
  onResourceError?: () => void;
}

export const AuthenticatedImage: React.FC<AuthenticatedImageProps> = ({
  sourceUrl,
  deferUntilVisible = true,
  onResourceError,
  ...imageProps
}) => {
  const shouldDefer = deferUntilVisible && isAuthenticatedMediaUrl(sourceUrl);
  const { elementRef: imageRef, isNearViewport } = useNearViewport<HTMLImageElement>(shouldDefer);
  const shouldLoad = !shouldDefer || isNearViewport;
  const { resolvedUrl, isLoading, hasError } = useAuthenticatedBlobUrl(sourceUrl, shouldLoad);

  useEffect(() => {
    if (hasError) onResourceError?.();
  }, [hasError, onResourceError]);

  return (
    <img
      {...imageProps}
      ref={imageRef}
      src={resolvedUrl ?? undefined}
      aria-busy={isLoading || undefined}
    />
  );
};

interface AuthenticatedVideoProps extends Omit<React.VideoHTMLAttributes<HTMLVideoElement>, 'src'> {
  sourceUrl: string;
}

export const AuthenticatedVideo: React.FC<AuthenticatedVideoProps> = ({
  sourceUrl,
  ...videoProps
}) => {
  const shouldDefer = isAuthenticatedMediaUrl(sourceUrl);
  const { elementRef: videoRef, isNearViewport } = useNearViewport<HTMLVideoElement>(shouldDefer);
  const shouldLoad = !shouldDefer || isNearViewport;
  const { resolvedUrl, isLoading } = useAuthenticatedBlobUrl(sourceUrl, shouldLoad);

  return (
    <video
      {...videoProps}
      ref={videoRef}
      src={resolvedUrl ?? undefined}
      aria-busy={isLoading || undefined}
    />
  );
};
