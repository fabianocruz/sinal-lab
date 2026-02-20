import React from 'react';
import '@testing-library/jest-dom/vitest';

// Mock next/link to render a plain anchor tag
vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
  notFound: vi.fn(),
}));

// Mock next/font/google to return CSS variable objects
vi.mock('next/font/google', () => ({
  DM_Serif_Display: () => ({ variable: '--font-display' }),
  IBM_Plex_Sans: () => ({ variable: '--font-body' }),
  IBM_Plex_Mono: () => ({ variable: '--font-mono' }),
}));
