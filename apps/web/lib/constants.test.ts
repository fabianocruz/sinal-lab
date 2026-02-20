import { describe, it, expect } from 'vitest';
import { AGENT_PERSONAS, AGENT_COLORS, type AgentKey } from '@/lib/constants';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const HEX_REGEX = /^#[0-9A-Fa-f]{6}$/;

const EXPECTED_AGENT_KEYS: AgentKey[] = ['sintese', 'radar', 'codigo', 'funding', 'mercado'];

const EXPECTED_AGENT_CODES: Record<AgentKey, string> = {
  sintese: 'SINTESE',
  radar: 'RADAR',
  codigo: 'CODIGO',
  funding: 'FUNDING',
  mercado: 'MERCADO',
};

// ---------------------------------------------------------------------------
// AGENT_PERSONAS shape
// ---------------------------------------------------------------------------

describe('AGENT_PERSONAS', () => {
  it('has exactly 5 entries', () => {
    expect(Object.keys(AGENT_PERSONAS)).toHaveLength(5);
  });

  it('contains all 5 expected agent keys', () => {
    for (const key of EXPECTED_AGENT_KEYS) {
      expect(
        Object.prototype.hasOwnProperty.call(AGENT_PERSONAS, key),
        `AGENT_PERSONAS missing key "${key}"`,
      ).toBe(true);
    }
  });

  it('every persona has a non-empty name', () => {
    for (const [key, persona] of Object.entries(AGENT_PERSONAS)) {
      expect(typeof persona.name, `name should be string for "${key}"`).toBe('string');
      expect(persona.name.trim().length, `name is empty for "${key}"`).toBeGreaterThan(0);
    }
  });

  it('every persona has a non-empty role', () => {
    for (const [key, persona] of Object.entries(AGENT_PERSONAS)) {
      expect(typeof persona.role, `role should be string for "${key}"`).toBe('string');
      expect(persona.role.trim().length, `role is empty for "${key}"`).toBeGreaterThan(0);
    }
  });

  it('every persona has a non-empty agentCode', () => {
    for (const [key, persona] of Object.entries(AGENT_PERSONAS)) {
      expect(typeof persona.agentCode, `agentCode should be string for "${key}"`).toBe('string');
      expect(persona.agentCode.trim().length, `agentCode is empty for "${key}"`).toBeGreaterThan(0);
    }
  });

  it('every persona has a non-empty color', () => {
    for (const [key, persona] of Object.entries(AGENT_PERSONAS)) {
      expect(typeof persona.color, `color should be string for "${key}"`).toBe('string');
      expect(persona.color.trim().length, `color is empty for "${key}"`).toBeGreaterThan(0);
    }
  });

  it('every persona has a non-empty description', () => {
    for (const [key, persona] of Object.entries(AGENT_PERSONAS)) {
      expect(typeof persona.description, `description should be string for "${key}"`).toBe('string');
      expect(persona.description.trim().length, `description is empty for "${key}"`).toBeGreaterThan(0);
    }
  });

  it('every persona has a non-empty avatarPath', () => {
    for (const [key, persona] of Object.entries(AGENT_PERSONAS)) {
      expect(typeof persona.avatarPath, `avatarPath should be string for "${key}"`).toBe('string');
      expect(persona.avatarPath.trim().length, `avatarPath is empty for "${key}"`).toBeGreaterThan(0);
    }
  });
});

// ---------------------------------------------------------------------------
// Agent codes
// ---------------------------------------------------------------------------

describe('AGENT_PERSONAS agentCode values', () => {
  it('sintese has agentCode SINTESE', () => {
    expect(AGENT_PERSONAS.sintese.agentCode).toBe('SINTESE');
  });

  it('radar has agentCode RADAR', () => {
    expect(AGENT_PERSONAS.radar.agentCode).toBe('RADAR');
  });

  it('codigo has agentCode CODIGO', () => {
    expect(AGENT_PERSONAS.codigo.agentCode).toBe('CODIGO');
  });

  it('funding has agentCode FUNDING', () => {
    expect(AGENT_PERSONAS.funding.agentCode).toBe('FUNDING');
  });

  it('mercado has agentCode MERCADO', () => {
    expect(AGENT_PERSONAS.mercado.agentCode).toBe('MERCADO');
  });

  it('all agentCodes match expected uppercase values', () => {
    for (const key of EXPECTED_AGENT_KEYS) {
      expect(AGENT_PERSONAS[key].agentCode).toBe(EXPECTED_AGENT_CODES[key]);
    }
  });

  it('all agentCodes are uppercase strings', () => {
    for (const [key, persona] of Object.entries(AGENT_PERSONAS)) {
      expect(
        persona.agentCode,
        `agentCode for "${key}" should be uppercase`,
      ).toBe(persona.agentCode.toUpperCase());
    }
  });

  it('all agentCodes are unique', () => {
    const codes = Object.values(AGENT_PERSONAS).map((p) => p.agentCode);
    const unique = new Set(codes);
    expect(unique.size).toBe(codes.length);
  });
});

// ---------------------------------------------------------------------------
// Agent colors
// ---------------------------------------------------------------------------

describe('AGENT_PERSONAS color values', () => {
  it('all persona colors are valid 6-digit hex strings', () => {
    for (const [key, persona] of Object.entries(AGENT_PERSONAS)) {
      expect(
        HEX_REGEX.test(persona.color),
        `color "${persona.color}" for persona "${key}" is not a valid hex color`,
      ).toBe(true);
    }
  });

  it('has correct color for sintese (#E8FF59)', () => {
    expect(AGENT_PERSONAS.sintese.color).toBe('#E8FF59');
  });

  it('has correct color for radar (#59FFB4)', () => {
    expect(AGENT_PERSONAS.radar.color).toBe('#59FFB4');
  });

  it('has correct color for codigo (#59B4FF)', () => {
    expect(AGENT_PERSONAS.codigo.color).toBe('#59B4FF');
  });

  it('has correct color for funding (#FF8A59)', () => {
    expect(AGENT_PERSONAS.funding.color).toBe('#FF8A59');
  });

  it('has correct color for mercado (#C459FF)', () => {
    expect(AGENT_PERSONAS.mercado.color).toBe('#C459FF');
  });

  it('all persona colors are unique', () => {
    const colors = Object.values(AGENT_PERSONAS).map((p) => p.color);
    const unique = new Set(colors);
    expect(unique.size).toBe(colors.length);
  });
});

// ---------------------------------------------------------------------------
// AgentKey type — verified via keyof typeof AGENT_PERSONAS
// ---------------------------------------------------------------------------

describe('AgentKey type', () => {
  it('AGENT_PERSONAS includes all 5 expected AgentKey values as keys', () => {
    const keys = Object.keys(AGENT_PERSONAS) as AgentKey[];
    expect(keys).toHaveLength(5);
    expect(keys).toContain('sintese');
    expect(keys).toContain('radar');
    expect(keys).toContain('codigo');
    expect(keys).toContain('funding');
    expect(keys).toContain('mercado');
  });

  it('does not include unexpected keys', () => {
    const keys = Object.keys(AGENT_PERSONAS);
    for (const key of keys) {
      expect(EXPECTED_AGENT_KEYS).toContain(key);
    }
  });
});

// ---------------------------------------------------------------------------
// AGENT_COLORS
// ---------------------------------------------------------------------------

describe('AGENT_COLORS', () => {
  it('has exactly 5 entries', () => {
    expect(Object.keys(AGENT_COLORS)).toHaveLength(5);
  });

  it('has an entry for every AgentKey', () => {
    for (const key of EXPECTED_AGENT_KEYS) {
      expect(
        Object.prototype.hasOwnProperty.call(AGENT_COLORS, key),
        `AGENT_COLORS missing key "${key}"`,
      ).toBe(true);
    }
  });

  it('all values are non-empty strings (Tailwind class names)', () => {
    for (const [key, value] of Object.entries(AGENT_COLORS)) {
      expect(typeof value, `AGENT_COLORS["${key}"] should be a string`).toBe('string');
      expect(value.trim().length, `AGENT_COLORS["${key}"] should not be empty`).toBeGreaterThan(0);
    }
  });

  it('has correct Tailwind class for sintese', () => {
    expect(AGENT_COLORS.sintese).toBe('agent-sintese');
  });

  it('has correct Tailwind class for radar', () => {
    expect(AGENT_COLORS.radar).toBe('agent-radar');
  });

  it('has correct Tailwind class for codigo', () => {
    expect(AGENT_COLORS.codigo).toBe('agent-codigo');
  });

  it('has correct Tailwind class for funding', () => {
    expect(AGENT_COLORS.funding).toBe('agent-funding');
  });

  it('has correct Tailwind class for mercado', () => {
    expect(AGENT_COLORS.mercado).toBe('agent-mercado');
  });
});
