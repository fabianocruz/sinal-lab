import { describe, it, expect } from 'vitest';
import {
  MOCK_NEWSLETTERS,
  CARD_GRADIENTS,
  AGENT_HEX,
  type Newsletter,
} from '@/lib/newsletter';
import type { AgentKey } from '@/lib/constants';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const VALID_AGENT_KEYS: AgentKey[] = ['sintese', 'radar', 'codigo', 'funding', 'mercado'];
const VALID_GRADIENT_INDEXES = [1, 2, 3, 4, 5, 6] as const;
const HEX_REGEX = /^#[0-9A-Fa-f]{6}$/;
const CSS_GRADIENT_REGEX = /linear-gradient\(/;

// ---------------------------------------------------------------------------
// MOCK_NEWSLETTERS
// ---------------------------------------------------------------------------

describe('MOCK_NEWSLETTERS', () => {
  it('has exactly 7 items', () => {
    expect(MOCK_NEWSLETTERS).toHaveLength(7);
  });

  it('every newsletter has required fields: slug, edition, title, agent, body', () => {
    for (const newsletter of MOCK_NEWSLETTERS) {
      expect(newsletter.slug, `slug missing on edition ${newsletter.edition}`).toBeTruthy();
      expect(typeof newsletter.edition, `edition not a number on slug "${newsletter.slug}"`).toBe('number');
      expect(newsletter.title, `title missing on slug "${newsletter.slug}"`).toBeTruthy();
      expect(newsletter.agent, `agent missing on slug "${newsletter.slug}"`).toBeTruthy();
      expect(newsletter.body, `body missing on slug "${newsletter.slug}"`).toBeTruthy();
    }
  });

  it('every newsletter has all Newsletter interface fields', () => {
    const requiredFields: (keyof Newsletter)[] = [
      'slug',
      'edition',
      'date',
      'dateISO',
      'title',
      'subtitle',
      'agent',
      'agentLabel',
      'dqScore',
      'likes',
      'gradientIndex',
      'body',
    ];

    for (const newsletter of MOCK_NEWSLETTERS) {
      for (const field of requiredFields) {
        expect(
          Object.prototype.hasOwnProperty.call(newsletter, field),
          `field "${field}" missing on slug "${newsletter.slug}"`,
        ).toBe(true);
      }
    }
  });

  it('slugs are unique', () => {
    const slugs = MOCK_NEWSLETTERS.map((n) => n.slug);
    const uniqueSlugs = new Set(slugs);
    expect(uniqueSlugs.size).toBe(MOCK_NEWSLETTERS.length);
  });

  it('slugs are non-empty strings', () => {
    for (const newsletter of MOCK_NEWSLETTERS) {
      expect(typeof newsletter.slug).toBe('string');
      expect(newsletter.slug.trim().length).toBeGreaterThan(0);
    }
  });

  it('edition numbers are unique', () => {
    const editions = MOCK_NEWSLETTERS.map((n) => n.edition);
    const uniqueEditions = new Set(editions);
    expect(uniqueEditions.size).toBe(MOCK_NEWSLETTERS.length);
  });

  it('edition numbers are in descending order', () => {
    const editions = MOCK_NEWSLETTERS.map((n) => n.edition);
    for (let i = 0; i < editions.length - 1; i++) {
      expect(editions[i]).toBeGreaterThan(editions[i + 1]);
    }
  });

  it('agents are valid AgentKey values', () => {
    for (const newsletter of MOCK_NEWSLETTERS) {
      expect(
        VALID_AGENT_KEYS.includes(newsletter.agent),
        `invalid agent "${newsletter.agent}" on slug "${newsletter.slug}"`,
      ).toBe(true);
    }
  });

  it('gradientIndex values are between 1 and 6 inclusive', () => {
    for (const newsletter of MOCK_NEWSLETTERS) {
      expect(
        VALID_GRADIENT_INDEXES.includes(newsletter.gradientIndex),
        `invalid gradientIndex ${newsletter.gradientIndex} on slug "${newsletter.slug}"`,
      ).toBe(true);
    }
  });

  it('edition numbers are positive integers', () => {
    for (const newsletter of MOCK_NEWSLETTERS) {
      expect(Number.isInteger(newsletter.edition)).toBe(true);
      expect(newsletter.edition).toBeGreaterThan(0);
    }
  });

  it('likes are non-negative integers', () => {
    for (const newsletter of MOCK_NEWSLETTERS) {
      expect(Number.isInteger(newsletter.likes)).toBe(true);
      expect(newsletter.likes).toBeGreaterThanOrEqual(0);
    }
  });

  it('dqScore is either a non-empty string or null', () => {
    for (const newsletter of MOCK_NEWSLETTERS) {
      const { dqScore } = newsletter;
      if (dqScore !== null) {
        expect(typeof dqScore).toBe('string');
        expect(dqScore.trim().length).toBeGreaterThan(0);
      } else {
        expect(dqScore).toBeNull();
      }
    }
  });

  it('dateISO fields are valid ISO 8601 date strings (YYYY-MM-DD)', () => {
    const ISO_DATE_REGEX = /^\d{4}-\d{2}-\d{2}$/;
    for (const newsletter of MOCK_NEWSLETTERS) {
      expect(
        ISO_DATE_REGEX.test(newsletter.dateISO),
        `invalid dateISO "${newsletter.dateISO}" on slug "${newsletter.slug}"`,
      ).toBe(true);
    }
  });

  it('body fields are non-empty strings with meaningful content', () => {
    for (const newsletter of MOCK_NEWSLETTERS) {
      expect(typeof newsletter.body).toBe('string');
      // Bodies should have at least 100 characters of actual content
      expect(newsletter.body.trim().length).toBeGreaterThan(100);
    }
  });

  it('all 5 valid agent keys are represented across all newsletters', () => {
    const usedAgents = new Set(MOCK_NEWSLETTERS.map((n) => n.agent));
    for (const key of VALID_AGENT_KEYS) {
      expect(
        usedAgents.has(key),
        `agent key "${key}" not used in any newsletter`,
      ).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// CARD_GRADIENTS
// ---------------------------------------------------------------------------

describe('CARD_GRADIENTS', () => {
  it('has exactly 6 entries', () => {
    expect(Object.keys(CARD_GRADIENTS)).toHaveLength(6);
  });

  it('has entries for indexes 1 through 6', () => {
    for (const index of VALID_GRADIENT_INDEXES) {
      expect(
        Object.prototype.hasOwnProperty.call(CARD_GRADIENTS, index),
        `missing key ${index}`,
      ).toBe(true);
    }
  });

  it('all values are valid CSS gradient strings containing linear-gradient(', () => {
    for (const [index, value] of Object.entries(CARD_GRADIENTS)) {
      expect(
        CSS_GRADIENT_REGEX.test(value),
        `CARD_GRADIENTS[${index}] is not a valid CSS gradient string`,
      ).toBe(true);
    }
  });

  it('all gradient values are non-empty strings', () => {
    for (const [index, value] of Object.entries(CARD_GRADIENTS)) {
      expect(typeof value, `CARD_GRADIENTS[${index}] should be a string`).toBe('string');
      expect(value.trim().length, `CARD_GRADIENTS[${index}] should not be empty`).toBeGreaterThan(0);
    }
  });

  it('each gradient value ends with the #2A2A32 base color', () => {
    for (const [index, value] of Object.entries(CARD_GRADIENTS)) {
      expect(
        value.includes('#2A2A32'),
        `CARD_GRADIENTS[${index}] missing base color #2A2A32`,
      ).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// AGENT_HEX
// ---------------------------------------------------------------------------

describe('AGENT_HEX', () => {
  it('has exactly 5 entries', () => {
    expect(Object.keys(AGENT_HEX)).toHaveLength(5);
  });

  it('has an entry for every valid AgentKey', () => {
    for (const key of VALID_AGENT_KEYS) {
      expect(
        Object.prototype.hasOwnProperty.call(AGENT_HEX, key),
        `AGENT_HEX missing key "${key}"`,
      ).toBe(true);
    }
  });

  it('all values are valid 6-digit hex color strings', () => {
    for (const [key, hex] of Object.entries(AGENT_HEX)) {
      expect(
        HEX_REGEX.test(hex),
        `AGENT_HEX["${key}"] = "${hex}" is not a valid hex color`,
      ).toBe(true);
    }
  });

  it('has correct hex value for sintese (#E8FF59)', () => {
    expect(AGENT_HEX.sintese).toBe('#E8FF59');
  });

  it('has correct hex value for radar (#59FFB4)', () => {
    expect(AGENT_HEX.radar).toBe('#59FFB4');
  });

  it('has correct hex value for codigo (#59B4FF)', () => {
    expect(AGENT_HEX.codigo).toBe('#59B4FF');
  });

  it('has correct hex value for funding (#FF8A59)', () => {
    expect(AGENT_HEX.funding).toBe('#FF8A59');
  });

  it('has correct hex value for mercado (#C459FF)', () => {
    expect(AGENT_HEX.mercado).toBe('#C459FF');
  });

  it('all hex values are unique (no two agents share the same color)', () => {
    const values = Object.values(AGENT_HEX);
    const unique = new Set(values);
    expect(unique.size).toBe(values.length);
  });
});
