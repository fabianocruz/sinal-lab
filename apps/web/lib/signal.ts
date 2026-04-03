export interface Signal {
  id: string;
  platform: string;
  post_url: string;
  author_handle: string;
  author_display_name: string;
  text: string;
  published_at: string;
  metrics: { likes?: number; replies?: number; reposts?: number };
  theme: string;
  sub_theme: string;
  sentiment: number;
  authority_score: number;
}

export interface SignalCluster {
  id: string;
  name: string;
  slug: string;
  theme: string;
  sub_theme: string;
  description: string;
  signal_count: number;
  composite_score: number;
  dimensions: Record<string, number>;
  narrative_stage: string; // emerging, accelerating, peaking, declining
  top_voices: Array<{ handle: string; name: string; authority: number }>;
  top_posts: Array<{ url: string; text: string; author: string; platform: string }>;
  week_number: number;
  year: number;
}

export interface WeeklyPulse {
  id: string;
  week_number: number;
  year: number;
  slug: string;
  accelerating_themes: Array<{ name: string; score: number; delta: number }>;
  emerging_signals: Array<{ name: string; score: number; platforms: string[] }>;
  top_posts: Array<{ url: string; text: string; author: string; metrics: object }>;
  top_voices: Array<{ handle: string; name: string; signal_count: number }>;
  startups_to_watch: Array<{ slug: string; name: string; reason: string }>;
  sector_implications: Array<{ sector: string; implication: string }>;
  status: string;
}

export interface SignalStats {
  total_signals: number;
  total_clusters: number;
  total_voices: number;
  platforms: Record<string, number>;
  themes: Record<string, number>;
}

// Platform colors for visual identity
export const PLATFORM_COLORS: Record<string, string> = {
  twitter: "#1DA1F2",
  reddit: "#FF4500",
  bluesky: "#0085FF",
  linkedin: "#0A66C2",
  rss: "#EE802F",
};

// Narrative stage colors
export const STAGE_COLORS: Record<string, string> = {
  emerging: "#59FFB4",
  accelerating: "#E8FF59",
  peaking: "#FF8A59",
  declining: "#8A8A96",
};

// Stage labels in Portuguese
export const STAGE_LABELS: Record<string, string> = {
  emerging: "Emergindo",
  accelerating: "Acelerando",
  peaking: "No pico",
  declining: "Declinando",
};

// Platform display names
export const PLATFORM_LABELS: Record<string, string> = {
  twitter: "Twitter/X",
  reddit: "Reddit",
  bluesky: "Bluesky",
  linkedin: "LinkedIn",
  rss: "RSS",
};
