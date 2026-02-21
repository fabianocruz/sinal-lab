import { AGENT_PERSONAS, AgentKey } from "@/lib/constants";

/** Background colors at 15% opacity, keyed by agent. */
const AVATAR_BG: Record<AgentKey, string> = {
  sintese: "rgba(232,255,89,0.15)",
  radar: "rgba(89,255,180,0.15)",
  codigo: "rgba(89,180,255,0.15)",
  funding: "rgba(255,138,89,0.15)",
  mercado: "rgba(196,89,255,0.15)",
};

/** Border colors at 20% opacity, keyed by agent. */
const AVATAR_BORDER: Record<AgentKey, string> = {
  sintese: "rgba(232,255,89,0.20)",
  radar: "rgba(89,255,180,0.20)",
  codigo: "rgba(89,180,255,0.20)",
  funding: "rgba(255,138,89,0.20)",
  mercado: "rgba(196,89,255,0.20)",
};

/** Pixel dimensions per size variant. */
const SIZE_PX: Record<NonNullable<AgentAvatarProps["size"]>, number> = {
  sm: 32,
  md: 48,
  lg: 64,
};

/** Font sizes per size variant (in px, applied as inline style). */
const FONT_SIZE_PX: Record<NonNullable<AgentAvatarProps["size"]>, number> = {
  sm: 11,
  md: 14,
  lg: 18,
};

export interface AgentAvatarProps {
  agentKey: AgentKey;
  size?: "sm" | "md" | "lg";
}

/** Returns the two-letter initials for a full name ("Clara Medeiros" → "CM"). */
function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length < 2) return parts[0]?.charAt(0).toUpperCase() ?? "";
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

/**
 * Circular avatar showing an agent's initials on a semi-transparent
 * background in the agent's brand color. Purely presentational — no photos
 * required.
 */
export default function AgentAvatar({ agentKey, size = "md" }: AgentAvatarProps) {
  const persona = AGENT_PERSONAS[agentKey];
  const initials = getInitials(persona.name);
  const dimension = SIZE_PX[size];
  const fontSize = FONT_SIZE_PX[size];

  return (
    <div
      aria-label={`Avatar de ${persona.name}`}
      className="flex shrink-0 items-center justify-center rounded-full font-mono font-semibold"
      style={{
        width: dimension,
        height: dimension,
        fontSize,
        backgroundColor: AVATAR_BG[agentKey],
        color: persona.color,
        border: `1px solid ${AVATAR_BORDER[agentKey]}`,
      }}
    >
      {initials}
    </div>
  );
}
