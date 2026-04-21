import MarkdownRenderer from "@/components/newsletter/MarkdownRenderer";

interface FeedEditorialBannerProps {
  title: string;
  bodyMd: string;
  publishedAt?: string | null;
}

const ACCENT_COLOR = "#E8FF59"; // Signal yellow — matches Ana Torres / feed persona

/**
 * Weekly editor's pick for /feed. Populated by FEED_CURATOR agent's
 * ContentPiece (slug: feed-curated).
 *
 * Falls back to nothing when body_md is empty (caller checks before
 * rendering). Signed by Ana Torres (editorial persona).
 */
export default function FeedEditorialBanner({
  title,
  bodyMd,
  publishedAt,
}: FeedEditorialBannerProps) {
  const dateStr = publishedAt
    ? new Date(publishedAt).toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "long",
        year: "numeric",
      })
    : null;

  return (
    <section
      aria-label="Destaque editorial da semana"
      className="my-8 rounded-2xl border border-[rgba(232,255,89,0.12)] bg-[rgba(232,255,89,0.03)] px-6 py-8 md:px-10 md:py-10"
    >
      <div className="mb-5 flex items-center gap-2">
        <span
          className="inline-block h-1.5 w-1.5 rounded-full"
          style={{ backgroundColor: ACCENT_COLOR }}
          aria-hidden="true"
        />
        <span
          className="font-mono text-[11px] uppercase tracking-[2px]"
          style={{ color: ACCENT_COLOR }}
        >
          Destaque da Semana &middot; Ana Torres
        </span>
      </div>

      <h2 className="mb-4 font-display text-[clamp(22px,3vw,32px)] leading-tight text-sinal-white">
        {title}
      </h2>

      <div className="prose-sinal max-w-[720px]">
        <MarkdownRenderer content={bodyMd} agentColor={ACCENT_COLOR} />
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-[rgba(255,255,255,0.06)] pt-4 text-[12px] text-ash">
        <span className="font-mono uppercase tracking-[1px]">Editora: Ana Torres</span>
        {dateStr && (
          <>
            <span aria-hidden="true">&middot;</span>
            <span>Atualizado em {dateStr}</span>
          </>
        )}
      </div>
    </section>
  );
}
