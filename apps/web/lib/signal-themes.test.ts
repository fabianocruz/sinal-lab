import { describe, it, expect } from "vitest";
import { SIGNAL_THEMES, THEME_COLORS, SECTOR_TAG_TO_THEME } from "@/lib/signal";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const HEX_REGEX = /^#[0-9A-Fa-f]{6}$/;

const EXPECTED_THEME_KEYS = [
  "AI",
  "Fintech",
  "AI in Banking",
  "Funding",
  "VC",
  "HealthTech",
  "DevTools",
  "Startup Ops",
  "Cybersecurity",
  "Regulation",
  "RetailTech",
  "CleanTech",
  "EdTech",
];

// ---------------------------------------------------------------------------
// SIGNAL_THEMES
// ---------------------------------------------------------------------------

describe("SIGNAL_THEMES", () => {
  it("has exactly 13 themes", () => {
    expect(SIGNAL_THEMES).toHaveLength(13);
  });

  it("contains all expected theme keys", () => {
    const keys = SIGNAL_THEMES.map((t) => t.key);
    for (const expected of EXPECTED_THEME_KEYS) {
      expect(keys, `missing theme "${expected}"`).toContain(expected);
    }
  });

  it("has no duplicate keys", () => {
    const keys = SIGNAL_THEMES.map((t) => t.key);
    expect(new Set(keys).size).toBe(keys.length);
  });

  it("every theme has a non-empty label", () => {
    for (const theme of SIGNAL_THEMES) {
      expect(theme.label.trim().length, `empty label for "${theme.key}"`).toBeGreaterThan(0);
    }
  });

  it("every theme has a valid hex color", () => {
    for (const theme of SIGNAL_THEMES) {
      expect(HEX_REGEX.test(theme.color), `invalid color "${theme.color}" for "${theme.key}"`).toBe(
        true,
      );
    }
  });

  it("all theme colors are unique", () => {
    const colors = SIGNAL_THEMES.map((t) => t.color);
    expect(new Set(colors).size).toBe(colors.length);
  });
});

// ---------------------------------------------------------------------------
// THEME_COLORS derived lookup
// ---------------------------------------------------------------------------

describe("THEME_COLORS", () => {
  it("has exactly 13 entries", () => {
    expect(Object.keys(THEME_COLORS)).toHaveLength(13);
  });

  it("has an entry for every SIGNAL_THEMES key", () => {
    for (const theme of SIGNAL_THEMES) {
      expect(THEME_COLORS[theme.key], `missing THEME_COLORS["${theme.key}"]`).toBe(theme.color);
    }
  });
});

// ---------------------------------------------------------------------------
// SECTOR_TAG_TO_THEME
// ---------------------------------------------------------------------------

describe("SECTOR_TAG_TO_THEME", () => {
  it("all values are valid theme keys", () => {
    const validKeys = new Set(SIGNAL_THEMES.map((t) => t.key));
    for (const [tag, themeKey] of Object.entries(SECTOR_TAG_TO_THEME)) {
      expect(
        validKeys.has(themeKey),
        `SECTOR_TAG_TO_THEME["${tag}"] = "${themeKey}" is not a valid theme key`,
      ).toBe(true);
    }
  });

  it("every theme has at least one tag mapping", () => {
    const coveredThemes = new Set(Object.values(SECTOR_TAG_TO_THEME));
    for (const expected of EXPECTED_THEME_KEYS) {
      expect(coveredThemes.has(expected), `no tag maps to theme "${expected}"`).toBe(true);
    }
  });

  it("all keys are lowercase", () => {
    for (const tag of Object.keys(SECTOR_TAG_TO_THEME)) {
      expect(tag, `tag "${tag}" should be lowercase`).toBe(tag.toLowerCase());
    }
  });
});
