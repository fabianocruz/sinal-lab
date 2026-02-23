"use client";

import ErrorPage from "@/components/ui/ErrorPage";

interface ErrorProps {
  error: Error;
  reset: () => void;
}

export default function StartupDetailError({ error, reset }: ErrorProps) {
  return (
    <ErrorPage
      error={error}
      reset={reset}
      title="Erro"
      message="Nao foi possivel carregar esta startup. Tente novamente."
      backHref="/startups"
      backLabel="Ver todas as startups"
    />
  );
}
