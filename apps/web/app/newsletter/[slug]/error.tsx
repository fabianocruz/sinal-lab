"use client";

import ErrorPage from "@/components/ui/ErrorPage";

interface ErrorProps {
  error: Error;
  reset: () => void;
}

export default function NewsletterSlugError({ error, reset }: ErrorProps) {
  return (
    <ErrorPage
      error={error}
      reset={reset}
      title="Edição não encontrada"
      message="Não foi possível carregar esta edição. Ela pode ter sido movida ou removida."
      backHref="/newsletter"
      backLabel="Ver todas as edições"
    />
  );
}
