export interface Signal {
  id: string;
  platform: string;
  source_name?: string; // e.g. "fintech_brain_food" — more specific than platform
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

export interface SignalClusterFirstMover {
  handle: string;
  name?: string;
  posted_at?: string; // ISO string
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
  // Optional enrichment — populated by RADAR agent when available
  first_mover?: SignalClusterFirstMover;
}

export interface WeeklyPulse {
  id: string;
  week_number: number;
  year: number;
  slug: string;
  accelerating_themes?: Array<{ name: string; score: number; delta: number }>;
  emerging_signals?: Array<{ name: string; score: number; platforms: string[] }>;
  top_posts?: Array<{ url: string; text: string; author: string; metrics: object }>;
  top_voices?: Array<{ handle: string; name: string; signal_count: number }>;
  startups_to_watch?: Array<{ slug: string; name: string; reason: string }>;
  sector_implications?: Array<{ sector: string; implication: string }>;
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

// Monitored voice (account) tracked by RADAR agent
export interface Voice {
  id: string;
  platform: string;
  handle: string;
  display_name: string | null;
  account_type: string | null; // founder, vc, executive, thought_leader, company
  authority_score: number;
  follower_count: number | null;
  bio: string | null;
  profile_url: string | null;
  sector_tags: string[] | null;
  is_active: boolean;
  last_fetched_at: string | null;
  metadata_: Record<string, unknown> | null;
  // Fields joined from signals on the frontend
  recent_signal_count?: number;
  recent_signals?: Array<{
    text: string;
    url: string;
    platform: string;
    published_at: string;
    metrics: Record<string, number>;
  }>;
}

// Voice account type labels in Portuguese
export const VOICE_TYPE_LABELS: Record<string, string> = {
  founder: "Founders",
  vc: "VCs",
  executive: "Executivos",
  thought_leader: "Liderancas",
  company: "Empresas",
};

// Entity extracted from signals (company mention)
export interface SignalEntity {
  name: string;
  slug: string | null; // slug in our DB if known
  theme: string;
  mention_count: number;
  sentiment: number; // avg -1 to 1
}
