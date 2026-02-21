import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import SourcesList from "@/components/newsletter/SourcesList";

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

describe("SourcesList — rendering", () => {
  it("returns null when sources array is empty", () => {
    const { container } = render(<SourcesList sources={[]} />);
    expect(container.innerHTML).toBe("");
  });

  it("renders the 'Fontes' heading", () => {
    render(<SourcesList sources={["https://techcrunch.com/article"]} />);

    expect(screen.getByText("Fontes")).toBeInTheDocument();
  });

  it("has an id='fontes' on the section for anchor linking", () => {
    const { container } = render(<SourcesList sources={["https://example.com/post"]} />);

    const section = container.querySelector("section#fontes");
    expect(section).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Hostname extraction
// ---------------------------------------------------------------------------

describe("SourcesList — hostname extraction", () => {
  it("displays hostname without www prefix", () => {
    render(<SourcesList sources={["https://www.bloomberg.com/news/article"]} />);

    expect(screen.getByText("bloomberg.com")).toBeInTheDocument();
  });

  it("displays hostname for URLs without www", () => {
    render(<SourcesList sources={["https://techcrunch.com/2026/post"]} />);

    expect(screen.getByText("techcrunch.com")).toBeInTheDocument();
  });

  it("displays raw URL for invalid URLs", () => {
    render(<SourcesList sources={["not-a-url"]} />);

    expect(screen.getByText("not-a-url")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Deduplication
// ---------------------------------------------------------------------------

describe("SourcesList — deduplication", () => {
  it("deduplicates sources by hostname, keeping first occurrence", () => {
    render(
      <SourcesList
        sources={[
          "https://techcrunch.com/article-1",
          "https://techcrunch.com/article-2",
          "https://bloomberg.com/news",
        ]}
      />,
    );

    // Should show only 2 links (techcrunch + bloomberg), not 3
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(2);
    expect(screen.getByText("techcrunch.com")).toBeInTheDocument();
    expect(screen.getByText("bloomberg.com")).toBeInTheDocument();
  });

  it("keeps first URL for each hostname as the link href", () => {
    render(
      <SourcesList sources={["https://techcrunch.com/first", "https://techcrunch.com/second"]} />,
    );

    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "https://techcrunch.com/first");
  });
});

// ---------------------------------------------------------------------------
// Links
// ---------------------------------------------------------------------------

describe("SourcesList — links", () => {
  it("renders links with target=_blank and rel=noopener noreferrer", () => {
    render(<SourcesList sources={["https://example.com/post"]} />);

    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("renders the full URL as href", () => {
    render(<SourcesList sources={["https://restofworld.org/2026/latam"]} />);

    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "https://restofworld.org/2026/latam");
  });
});

// ---------------------------------------------------------------------------
// Agent color
// ---------------------------------------------------------------------------

describe("SourcesList — agent color", () => {
  it("uses default #E8FF59 for accent dots when agentColor is not provided", () => {
    const { container } = render(<SourcesList sources={["https://example.com"]} />);

    const dot = container.querySelector("[aria-hidden='true']");
    expect(dot).toHaveStyle({ backgroundColor: "#E8FF59" });
  });

  it("uses provided agentColor for accent dots", () => {
    const { container } = render(
      <SourcesList sources={["https://example.com"]} agentColor="#59FFB4" />,
    );

    const dot = container.querySelector("[aria-hidden='true']");
    expect(dot).toHaveStyle({ backgroundColor: "#59FFB4" });
  });
});

// ---------------------------------------------------------------------------
// Multiple sources
// ---------------------------------------------------------------------------

describe("SourcesList — multiple sources", () => {
  it("renders one link per unique hostname", () => {
    render(
      <SourcesList
        sources={[
          "https://techcrunch.com/ai",
          "https://bloomberg.com/tech",
          "https://restofworld.org/latam",
        ]}
      />,
    );

    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(3);
  });
});
