import { HeroImage as HeroImageType } from "@/lib/newsletter";

interface HeroImageProps {
  /** Hero image metadata from newsletter metadata_. Null/undefined = no render. */
  hero_image: HeroImageType | null | undefined;
  /** Agent accent color (unused currently, reserved for future border styling). */
  agentColor: string;
}

/**
 * Full-width hero image displayed above the newsletter body.
 * Renders a responsive `<figure>` with optional caption and credit line.
 * Returns null when hero_image is missing or has no URL.
 */
export default function HeroImage({ hero_image }: HeroImageProps) {
  if (!hero_image?.url) return null;

  return (
    <figure className="mb-10">
      <img
        src={hero_image.url}
        alt={hero_image.alt || ""}
        className="max-h-[400px] w-full rounded-lg object-cover"
        loading="eager"
      />
      {(hero_image.caption || hero_image.credit) && (
        <figcaption className="mt-2 flex items-baseline justify-between font-mono text-[12px] text-ash">
          {hero_image.caption && <span>{hero_image.caption}</span>}
          {hero_image.credit && (
            <span className="text-[11px] text-ash/60">{hero_image.credit}</span>
          )}
        </figcaption>
      )}
    </figure>
  );
}
