import type { Metadata } from "next";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import FeedbackWidget from "@/components/feedback/FeedbackWidget";

export const metadata: Metadata = {
  title: "Feedback | Sinal",
  description: "Seu feedback melhora a proxima edicao automaticamente.",
  robots: "noindex",
};

export default function FeedbackPage({
  searchParams,
}: {
  searchParams: { score?: string; source?: string; edition?: string; slug?: string };
}) {
  const initialScore = searchParams.score ? parseInt(searchParams.score, 10) : undefined;
  const source = searchParams.source || "newsletter";
  const edition = searchParams.edition ? parseInt(searchParams.edition, 10) : undefined;
  const slug = searchParams.slug || undefined;

  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        <div className="mx-auto max-w-container px-6 py-20 md:px-10">
          <div className="mx-auto max-w-[480px]">
            <FeedbackWidget
              initialScore={initialScore}
              source={source}
              edition={edition}
              contentSlug={slug}
            />
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
