"use client";

import ErrorPage from "@/components/ui/ErrorPage";

interface ErrorProps {
  error: Error;
  reset: () => void;
}

export default function NewsletterArchiveError({ error, reset }: ErrorProps) {
  return (
    <ErrorPage
      error={error}
      reset={reset}
      title="Erro"
      message="Não foi possível carregar o arquivo de edições. Tente novamente."
      backHref="/"
      backLabel="Voltar ao início"
    />
  );
}
