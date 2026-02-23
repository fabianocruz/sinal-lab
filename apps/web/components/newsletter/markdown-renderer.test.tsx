import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";

// ---------------------------------------------------------------------------
// Unmock react-markdown so we can test the real MarkdownRenderer output.
// The global setup.tsx mocks react-markdown; we undo that here.
// ---------------------------------------------------------------------------
vi.unmock("react-markdown");
vi.unmock("remark-gfm");

import MarkdownRenderer from "@/components/newsletter/MarkdownRenderer";

// ---------------------------------------------------------------------------
// Headings
// ---------------------------------------------------------------------------

describe("MarkdownRenderer — headings", () => {
  it("renders h2 with agent-colored left border", () => {
    const { container } = render(
      <MarkdownRenderer content="## Section Title" agentColor="#59FFB4" />,
    );

    const h2 = container.querySelector("h2");
    expect(h2).toBeInTheDocument();
    expect(h2).toHaveTextContent("Section Title");
    expect(h2).toHaveStyle({ borderColor: "#59FFB4" });
  });

  it("renders h3 without border", () => {
    const { container } = render(<MarkdownRenderer content="### Sub Section" />);

    const h3 = container.querySelector("h3");
    expect(h3).toBeInTheDocument();
    expect(h3).toHaveTextContent("Sub Section");
  });

  it("renders h4", () => {
    const { container } = render(<MarkdownRenderer content="#### Detail" />);

    const h4 = container.querySelector("h4");
    expect(h4).toBeInTheDocument();
    expect(h4).toHaveTextContent("Detail");
  });
});

// ---------------------------------------------------------------------------
// Inline formatting
// ---------------------------------------------------------------------------

describe("MarkdownRenderer — inline formatting", () => {
  it("renders bold text as <strong>", () => {
    render(<MarkdownRenderer content="This is **bold** text." />);

    const strong = screen.getByText("bold");
    expect(strong.tagName).toBe("STRONG");
  });

  it("renders italic text as <em>", () => {
    render(<MarkdownRenderer content="This is *italic* text." />);

    const em = screen.getByText("italic");
    expect(em.tagName).toBe("EM");
  });
});

// ---------------------------------------------------------------------------
// Links
// ---------------------------------------------------------------------------

describe("MarkdownRenderer — links", () => {
  it("renders external links with target=_blank and rel=noopener noreferrer", () => {
    render(<MarkdownRenderer content="Visit [Example](https://example.com) now." />);

    const link = screen.getByRole("link", { name: "Example" });
    expect(link).toHaveAttribute("href", "https://example.com");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });
});

// ---------------------------------------------------------------------------
// Blockquotes
// ---------------------------------------------------------------------------

describe("MarkdownRenderer — blockquotes", () => {
  it("renders blockquote with agent-colored left border", () => {
    const { container } = render(
      <MarkdownRenderer content="> A quote here." agentColor="#FF8A59" />,
    );

    const blockquote = container.querySelector("blockquote");
    expect(blockquote).toBeInTheDocument();
    expect(blockquote).toHaveStyle({ borderColor: "#FF8A59" });
  });
});

// ---------------------------------------------------------------------------
// Lists
// ---------------------------------------------------------------------------

describe("MarkdownRenderer — lists", () => {
  it("renders unordered list", () => {
    const { container } = render(<MarkdownRenderer content={"- Item A\n- Item B\n- Item C"} />);

    const ul = container.querySelector("ul");
    expect(ul).toBeInTheDocument();

    const items = container.querySelectorAll("li");
    expect(items).toHaveLength(3);
  });

  it("renders ordered list", () => {
    const { container } = render(<MarkdownRenderer content={"1. First\n2. Second"} />);

    const ol = container.querySelector("ol");
    expect(ol).toBeInTheDocument();

    const items = container.querySelectorAll("li");
    expect(items).toHaveLength(2);
  });
});

// ---------------------------------------------------------------------------
// Code
// ---------------------------------------------------------------------------

describe("MarkdownRenderer — code", () => {
  it("renders inline code", () => {
    render(<MarkdownRenderer content="Use `console.log` for debugging." />);

    const code = screen.getByText("console.log");
    expect(code.tagName).toBe("CODE");
  });

  it("renders code block in <pre>", () => {
    const { container } = render(<MarkdownRenderer content={"```js\nconst x = 1;\n```"} />);

    const pre = container.querySelector("pre");
    expect(pre).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Tables (GFM)
// ---------------------------------------------------------------------------

describe("MarkdownRenderer — tables", () => {
  it("renders a GFM table", () => {
    const md = "| Name | Value |\n|------|-------|\n| A    | 1     |\n| B    | 2     |";
    const { container } = render(<MarkdownRenderer content={md} />);

    const table = container.querySelector("table");
    expect(table).toBeInTheDocument();

    const headers = container.querySelectorAll("th");
    expect(headers).toHaveLength(2);
    expect(headers[0]).toHaveTextContent("Name");
    expect(headers[1]).toHaveTextContent("Value");

    const cells = container.querySelectorAll("td");
    expect(cells).toHaveLength(4);
  });
});

// ---------------------------------------------------------------------------
// Horizontal rule
// ---------------------------------------------------------------------------

describe("MarkdownRenderer — hr", () => {
  it("renders horizontal rule", () => {
    const { container } = render(<MarkdownRenderer content={"Above\n\n---\n\nBelow"} />);

    const hr = container.querySelector("hr");
    expect(hr).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Paragraphs
// ---------------------------------------------------------------------------

describe("MarkdownRenderer — paragraphs", () => {
  it("renders paragraphs with text-silver class", () => {
    const { container } = render(<MarkdownRenderer content="A plain paragraph." />);

    const p = container.querySelector("p");
    expect(p).toBeInTheDocument();
    expect(p?.className).toContain("text-silver");
  });
});

// ---------------------------------------------------------------------------
// Default agentColor
// ---------------------------------------------------------------------------

describe("MarkdownRenderer — defaults", () => {
  it("uses #E8FF59 as default agent color for h2 border", () => {
    const { container } = render(<MarkdownRenderer content="## Default Color" />);

    const h2 = container.querySelector("h2");
    expect(h2).toHaveStyle({ borderColor: "#E8FF59" });
  });
});

// ---------------------------------------------------------------------------
// Images
// ---------------------------------------------------------------------------

describe("MarkdownRenderer — images", () => {
  it("renders img tag from markdown with figure wrapper", () => {
    const { container } = render(
      <MarkdownRenderer content="![Alt text](https://example.com/photo.jpg)" />,
    );

    const figure = container.querySelector("figure");
    expect(figure).toBeInTheDocument();

    const img = container.querySelector("img");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "https://example.com/photo.jpg");
    expect(img).toHaveAttribute("alt", "Alt text");
    expect(img).toHaveAttribute("loading", "lazy");
  });

  it("uses alt text as figcaption", () => {
    const { container } = render(
      <MarkdownRenderer content="![Caption text](https://example.com/photo.jpg)" />,
    );

    const caption = container.querySelector("figcaption");
    expect(caption).toBeInTheDocument();
    expect(caption).toHaveTextContent("Caption text");
  });

  it("omits figcaption when alt is empty", () => {
    const { container } = render(<MarkdownRenderer content="![](https://example.com/photo.jpg)" />);

    const caption = container.querySelector("figcaption");
    expect(caption).not.toBeInTheDocument();
  });
});
