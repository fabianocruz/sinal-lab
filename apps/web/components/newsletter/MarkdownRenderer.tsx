"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

interface MarkdownRendererProps {
  content: string;
  agentColor?: string;
}

export default function MarkdownRenderer({
  content,
  agentColor = "#E8FF59",
}: MarkdownRendererProps) {
  const components: Components = {
    h2: ({ children }) => (
      <h2
        className="mt-10 mb-4 border-l-2 pl-4 font-display text-[22px] leading-[1.3] text-bone"
        style={{ borderColor: agentColor }}
      >
        {children}
      </h2>
    ),
    h3: ({ children }) => (
      <h3 className="mt-8 mb-3 font-display text-[18px] leading-[1.3] text-bone">{children}</h3>
    ),
    h4: ({ children }) => (
      <h4 className="mt-6 mb-2 font-display text-[16px] leading-[1.4] text-bone">{children}</h4>
    ),
    p: ({ node, children }) => {
      // Standalone images are wrapped in <p> by react-markdown — unwrap to avoid
      // invalid DOM nesting (<figure> inside <p>).
      const hasImage = node?.children?.some(
        (child) => "tagName" in child && child.tagName === "img",
      );
      if (hasImage) return <>{children}</>;
      return <p className="mb-6 text-[16px] leading-[1.8] text-silver last:mb-0">{children}</p>;
    },
    a: ({ href, children }) => (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-signal underline underline-offset-2 transition-colors hover:text-signal-dim"
      >
        {children}
      </a>
    ),
    strong: ({ children }) => <strong className="font-semibold text-bone">{children}</strong>,
    em: ({ children }) => <em className="italic text-silver">{children}</em>,
    blockquote: ({ children }) => (
      <blockquote
        className="my-6 border-l-2 pl-4 text-ash italic"
        style={{ borderColor: agentColor }}
      >
        {children}
      </blockquote>
    ),
    ul: ({ children }) => <ul className="mb-6 list-disc pl-6 text-silver">{children}</ul>,
    ol: ({ children }) => <ol className="mb-6 list-decimal pl-6 text-silver">{children}</ol>,
    li: ({ children }) => <li className="mb-2 leading-[1.7]">{children}</li>,
    code: ({ className, children }) => {
      const isBlock = className?.includes("language-");
      if (isBlock) {
        return <code className="block text-[14px] text-silver">{children}</code>;
      }
      return (
        <code className="rounded bg-sinal-slate px-1.5 py-0.5 font-mono text-[14px] text-signal">
          {children}
        </code>
      );
    },
    pre: ({ children }) => (
      <pre className="my-6 overflow-x-auto rounded-lg bg-sinal-graphite p-4 font-mono text-[14px]">
        {children}
      </pre>
    ),
    table: ({ children }) => (
      <div className="my-6 overflow-x-auto">
        <table className="w-full border-collapse text-[14px] text-silver">{children}</table>
      </div>
    ),
    thead: ({ children }) => (
      <thead className="border-b border-[rgba(255,255,255,0.1)]">{children}</thead>
    ),
    th: ({ children }) => (
      <th className="px-3 py-2 text-left font-mono text-[11px] uppercase tracking-[1px] text-ash">
        {children}
      </th>
    ),
    td: ({ children }) => (
      <td className="border-b border-[rgba(255,255,255,0.06)] px-3 py-2">{children}</td>
    ),
    hr: () => <hr className="my-8 border-[rgba(255,255,255,0.06)]" />,
    img: ({ src, alt }) => (
      <figure className="my-8">
        <img src={src} alt={alt || ""} className="w-full rounded-lg" loading="lazy" />
        {alt && (
          <figcaption className="mt-2 text-center font-mono text-[12px] text-ash">{alt}</figcaption>
        )}
      </figure>
    ),
  };

  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
      {content}
    </ReactMarkdown>
  );
}
