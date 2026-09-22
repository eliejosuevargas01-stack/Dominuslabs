import '@testing-library/jest-dom';

// In Node 26 + Vitest 4.x, the Web Storage API (localStorage/sessionStorage) may be
// defined globally by Node but non-functional without --localstorage-file.
// Some tests also stub `window` (via vi.stubGlobal) which removes window.localStorage.
// We install a shared in-memory polyfill at both globalThis.localStorage and
// globalThis._testLocalStorage (the latter as a fallback when window is stubbed).
function makeStorage(): Storage {
  const store: Record<string, string> = {};
  return {
    getItem: (key: string) => (key in store ? store[key] : null),
    setItem: (key: string, value: string) => { store[key] = String(value); },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { Object.keys(store).forEach(k => delete store[k]); },
    get length() { return Object.keys(store).length; },
    key: (index: number) => Object.keys(store)[index] ?? null,
  } as Storage;
}

const _storage = makeStorage();

// Install on globalThis.localStorage (overrides broken Node 26 Web Storage)
Object.defineProperty(globalThis, 'localStorage', {
  value: _storage,
  writable: true,
  configurable: true,
});

// Install as backup key for when vi.stubGlobal('window', ...) removes window.localStorage
Object.defineProperty(globalThis, '_testLocalStorage', {
  value: _storage,
  writable: true,
  configurable: true,
});

Object.defineProperty(globalThis, 'sessionStorage', {
  value: makeStorage(),
  writable: true,
  configurable: true,
});
