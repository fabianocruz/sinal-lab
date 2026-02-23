import { FeaturedVideo } from "@/lib/newsletter";

interface VideoEmbedProps {
  /** Video metadata from newsletter metadata_. Null/undefined = no render. */
  video: FeaturedVideo | null | undefined;
}

/** Extract provider and video ID from a YouTube or Vimeo URL. Returns null for unrecognized URLs. */
function parseVideoId(url: string): { provider: "youtube" | "vimeo"; id: string } | null {
  // YouTube: youtube.com/watch?v=ID or youtu.be/ID
  const ytMatch = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)/);
  if (ytMatch) return { provider: "youtube", id: ytMatch[1] };

  // Vimeo: vimeo.com/ID
  const vimeoMatch = url.match(/vimeo\.com\/(\d+)/);
  if (vimeoMatch) return { provider: "vimeo", id: vimeoMatch[1] };

  return null;
}

function getEmbedUrl(provider: "youtube" | "vimeo", id: string): string {
  if (provider === "youtube") return `https://www.youtube-nocookie.com/embed/${id}`;
  return `https://player.vimeo.com/video/${id}`;
}

/**
 * Responsive 16:9 video embed for YouTube and Vimeo.
 * Uses youtube-nocookie.com for privacy. Returns null for missing/unrecognized URLs.
 */
export default function VideoEmbed({ video }: VideoEmbedProps) {
  if (!video?.url) return null;

  const parsed = parseVideoId(video.url);
  if (!parsed) return null;

  const embedUrl = getEmbedUrl(parsed.provider, parsed.id);

  return (
    <figure className="mb-10">
      <div className="aspect-video overflow-hidden rounded-lg">
        <iframe
          src={embedUrl}
          title={video.title || "Video"}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          className="h-full w-full border-0"
        />
      </div>
      {video.caption && (
        <figcaption className="mt-2 font-mono text-[12px] text-ash">{video.caption}</figcaption>
      )}
    </figure>
  );
}
