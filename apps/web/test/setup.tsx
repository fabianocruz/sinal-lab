import React from "react";
import "@testing-library/jest-dom/vitest";

// Mock next/link to render a plain anchor tag
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
  notFound: vi.fn(),
}));

// Mock next/font/google to return CSS variable objects
vi.mock("next/font/google", () => ({
  DM_Serif_Display: () => ({ variable: "--font-display" }),
  IBM_Plex_Sans: () => ({ variable: "--font-body" }),
  IBM_Plex_Mono: () => ({ variable: "--font-mono" }),
}));

// Mock next-auth/react — default to unauthenticated so Navbar tests are not
// affected by auth state. Individual tests can override useSession as needed.
vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: null, status: "unauthenticated" }),
  SessionProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock react-markdown — split content by blank lines and render each block as
// a <p> so gating tests can still find individual paragraphs with getByText().
// MarkdownRenderer-specific tests unmock this to test the real component.
vi.mock("react-markdown", () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown">
      {children.split("\n\n").filter(Boolean).map((block: string, i: number) => (
        <p key={i}>{block}</p>
      ))}
    </div>
  ),
}));
vi.mock("remark-gfm", () => ({ default: () => {} }));

// Mock IntersectionObserver (not available in jsdom)
class MockIntersectionObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
vi.stubGlobal("IntersectionObserver", MockIntersectionObserver);
