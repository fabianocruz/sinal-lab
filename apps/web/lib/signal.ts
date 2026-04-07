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

// ---------------------------------------------------------------------------
// Signal Themes — single source of truth for the 13-theme taxonomy
// ---------------------------------------------------------------------------

export const SIGNAL_THEMES = [
  { key: "AI", label: "AI", color: "#59FFB4" },
  { key: "Fintech", label: "Fintech", color: "#E8FF59" },
  { key: "AI in Banking", label: "AI in Banking", color: "#59B4FF" },
  { key: "Funding", label: "Funding", color: "#FF8A59" },
  { key: "VC", label: "VC", color: "#B59FFF" },
  { key: "HealthTech", label: "HealthTech", color: "#59D4FF" },
  { key: "DevTools", label: "DevTools", color: "#C459FF" },
  { key: "Startup Ops", label: "Startup Ops", color: "#FF6B8A" },
  { key: "Cybersecurity", label: "Cybersecurity", color: "#FF5E5E" },
  { key: "Regulation", label: "Regulation", color: "#8A8A96" },
  { key: "RetailTech", label: "RetailTech", color: "#FFB859" },
  { key: "CleanTech", label: "CleanTech", color: "#59FF8A" },
  { key: "EdTech", label: "EdTech", color: "#FF59D4" },
] as const;

export type SignalThemeKey = (typeof SIGNAL_THEMES)[number]["key"];

/** Quick lookup: theme key → hex color */
export const THEME_COLORS: Record<string, string> = Object.fromEntries(
  SIGNAL_THEMES.map((t) => [t.key, t.color]),
);

/**
 * Maps voice sector_tags and common aliases to canonical theme keys.
 * Every theme must have at least one entry so that VoicesPanel can match
 * voices to signals via theme-based fallback.
 */
export const SECTOR_TAG_TO_THEME: Record<string, string> = {
  // AI
  ai: "AI",
  "artificial intelligence": "AI",
  "machine learning": "AI",
  developer: "AI",
  infrastructure: "AI",
  // Fintech
  fintech: "Fintech",
  payments: "Fintech",
  crypto: "Fintech",
  blockchain: "Fintech",
  "digital assets": "Fintech",
  // AI in Banking
  banking: "AI in Banking",
  "banking ai": "AI in Banking",
  kyc: "AI in Banking",
  aml: "AI in Banking",
  regtech: "AI in Banking",
  insurtech: "AI in Banking",
  // Funding
  funding: "Funding",
  "venture capital": "Funding",
  investor: "Funding",
  vc: "Funding",
  angel: "Funding",
  // VC
  lp: "VC",
  gp: "VC",
  "fund manager": "VC",
  // HealthTech
  healthtech: "HealthTech",
  health: "HealthTech",
  telemedicine: "HealthTech",
  biotech: "HealthTech",
  medtech: "HealthTech",
  // DevTools
  devtools: "DevTools",
  "developer tools": "DevTools",
  observability: "DevTools",
  "ci/cd": "DevTools",
  api: "DevTools",
  // Startup Ops
  "startup ops": "Startup Ops",
  hiring: "Startup Ops",
  culture: "Startup Ops",
  scaling: "Startup Ops",
  founder: "Startup Ops",
  // Cybersecurity
  cybersecurity: "Cybersecurity",
  security: "Cybersecurity",
  appsec: "Cybersecurity",
  privacy: "Cybersecurity",
  // Regulation
  regulation: "Regulation",
  compliance: "Regulation",
  lgpd: "Regulation",
  "open finance": "Regulation",
  // RetailTech
  retailtech: "RetailTech",
  "e-commerce": "RetailTech",
  ecommerce: "RetailTech",
  marketplace: "RetailTech",
  logistics: "RetailTech",
  // CleanTech
  cleantech: "CleanTech",
  "clean energy": "CleanTech",
  sustainability: "CleanTech",
  "carbon credits": "CleanTech",
  // EdTech
  edtech: "EdTech",
  education: "EdTech",
  "online learning": "EdTech",
  "corporate training": "EdTech",
};

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
// Backend uses "exec", frontend historically used "executive" — support both.
export const VOICE_TYPE_LABELS: Record<string, string> = {
  founder: "Founders",
  vc: "VCs",
  exec: "Executivos",
  executive: "Executivos",
  thought_leader: "Liderancas",
  company: "Empresas",
};

// ---------------------------------------------------------------------------
// Curated Feed Item — produced by the Feed Curator Agent
// ---------------------------------------------------------------------------

export interface VideoEmbed {
  platform: string;
  embed_url: string;
  thumbnail: string | null;
}

export interface CuratedFeedItem {
  id: string;
  editorial_headline: string;
  editorial_context: string | null;
  original_text: string;
  original_url: string;
  platform: string;
  author_handle: string;
  author_display_name: string;
  thumbnail_url: string | null;
  video_embed: VideoEmbed | null;
  theme: string;
  category: string;
  relevance_score: number;
  metrics: Record<string, number> | null;
  curated_at: string;
}

// ---------------------------------------------------------------------------
// Entity extracted from signals (company mention)
// ---------------------------------------------------------------------------

export interface SignalEntity {
  name: string;
  slug: string | null; // slug in our DB if known
  theme: string;
  mention_count: number;
  sentiment: number; // avg -1 to 1
}
