import '@testing-library/jest-dom/vitest';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { cleanup } from '@testing-library/react';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

// jsdom doesn't implement matchMedia or ResizeObserver. Chakra UI touches
// matchMedia for color-mode detection and Framer Motion's layout animations
// can probe ResizeObserver; without stubs, mounting almost any component
// under test throws before assertions even run.
if (typeof window !== 'undefined' && !window.matchMedia) {
  window.matchMedia = (query: string): MediaQueryList =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList;
}

if (typeof window !== 'undefined' && typeof window.ResizeObserver === 'undefined') {
  class ResizeObserverMock {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  }
  window.ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver;
}

// Shared MSW server used by hook/integration tests that exercise real HTTP
// calls (e.g. useJobs.test.tsx). No handlers are registered by default -
// each test registers only the endpoints it needs via `server.use(...)`, and
// `onUnhandledRequest: 'error'` makes any un-mocked call fail loudly instead
// of hanging or hitting the network.
export const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

afterEach(() => {
  server.resetHandlers();
  cleanup();
});

afterAll(() => server.close());

export { http, HttpResponse };
