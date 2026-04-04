"use client";

interface WatchlistButtonProps {
  slug: string;
  isWatched: boolean;
  onToggle: (slug: string) => void;
}

export default function WatchlistButton({ slug, isWatched, onToggle }: WatchlistButtonProps) {
  function handleClick(e: React.MouseEvent) {
    // Prevent the parent Link from navigating when clicking the bookmark
    e.preventDefault();
    e.stopPropagation();
    onToggle(slug);
  }

  return (
    <button
      onClick={handleClick}
      aria-label={isWatched ? "Remover dos temas monitorados" : "Monitorar este tema"}
      aria-pressed={isWatched}
      title={isWatched ? "Remover da watchlist" : "Adicionar a watchlist"}
      className={[
        "flex h-7 w-7 shrink-0 items-center justify-center rounded-md transition-all duration-200",
        isWatched ? "text-signal hover:text-signal/70" : "text-[#4A4A56] hover:text-ash",
      ].join(" ")}
    >
      {isWatched ? (
        // Filled bookmark
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          className="h-4 w-4"
          aria-hidden="true"
        >
          <path d="M6.32 2.577a49.255 49.255 0 0111.36 0c1.497.174 2.57 1.46 2.57 2.93V21a.75.75 0 01-1.085.67L12 18.089l-7.165 3.583A.75.75 0 013.75 21V5.507c0-1.47 1.073-2.756 2.57-2.93z" />
        </svg>
      ) : (
        // Outline bookmark
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
          className="h-4 w-4"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z"
          />
        </svg>
      )}
    </button>
  );
}
