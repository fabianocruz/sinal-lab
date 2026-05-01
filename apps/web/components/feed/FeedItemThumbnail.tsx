"use client";

import { useState } from "react";

interface FeedItemThumbnailProps {
  src: string;
  href: string;
}

/**
 * Thumbnail image with graceful failure: when the underlying URL returns
 * an error (403 from Reddit, broken host, etc.), the entire thumbnail
 * block is removed from the DOM so the card collapses cleanly instead
 * of showing a hollow placeholder with alt text.
 */
export default function FeedItemThumbnail({ src, href }: FeedItemThumbnailProps) {
  const [errored, setErrored] = useState(false);

  if (errored) return null;

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="shrink-0"
      tabIndex={-1}
      aria-hidden="true"
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt=""
        className="h-24 w-40 rounded-lg object-cover"
        loading="lazy"
        onError={() => setErrored(true)}
      />
    </a>
  );
}
