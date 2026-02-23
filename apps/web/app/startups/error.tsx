"use client";

import ErrorPage from "@/components/ui/ErrorPage";

interface ErrorProps {
  error: Error;
  reset: () => void;
}

export default function StartupsError({ error, reset }: ErrorProps) {
  return (
    <ErrorPage
      error={error}
      reset={reset}
      title="Erro"
      message="Nao foi possivel carregar o mapa de startups. Tente novamente."
      backHref="/"
      backLabel="Voltar ao inicio"
    />
  );
}
