/**
 * colorUtils.ts
 * Central color resolution logic for the Kerala Elections 2026 dashboard.
 *
 * Rules:
 *  - LDF / UDF / NDA parties  →  alliance color
 *  - OTH parties              →  their own party color_code from DB
 *  - IND (party-supported)    →  lightened version of PARENT party's color
 *    e.g. "IND (CPI(M))" → lighter red, "IND (INL)" → lighter green
 *  - Pure IND                 →  grey (#6B7280)
 */

import type { Party } from '../types';

// ── Alliance canonical colors ────────────────────────────────────────────────
export const ALLIANCE_COLORS: Record<string, string> = {
  LDF: '#D42B2B',
  UDF: '#1A8FE3',
  NDA: '#F7921C',
  OTH: '#9CA3AF',
};

export const PURE_IND_COLOR = '#6B7280';

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Returns true for exactly the code 'IND' (pure independent, no party support). */
export function isRawIND(code: string): boolean {
  return code === 'IND';
}

/**
 * Returns true for party-supported independents, e.g. "IND (CPI(M))", "IND (INL)".
 * These are separate Party records whose code matches /^IND \(.+\)$/.
 */
export function isSupportedIND(code: string): boolean {
  return /^IND \(.+\)$/.test(code);
}

/**
 * Extract the parent party code from a supported-IND code.
 * "IND (CPI(M))" → "CPI(M)"
 * "IND (INL)"    → "INL"
 */
export function parentPartyCode(code: string): string {
  const m = code.match(/^IND \((.+)\)$/);
  return m ? m[1] : '';
}

/**
 * Lighten a hex color by blending it toward white.
 * factor: 0 = original, 1 = white. Default 0.45 gives a soft tint.
 */
export function lightenHex(hex: string, factor = 0.45): string {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  const lr = Math.round(r + (255 - r) * factor);
  const lg = Math.round(g + (255 - g) * factor);
  const lb = Math.round(b + (255 - b) * factor);
  return `#${lr.toString(16).padStart(2, '0')}${lg.toString(16).padStart(2, '0')}${lb.toString(16).padStart(2, '0')}`;
}

/**
 * Resolve the display color for a party, using DB party list for color_code lookup.
 *
 * Priority:
 *  1. Pure IND                        → PURE_IND_COLOR grey
 *  2. Supported IND (IND (xxx))       → lightenHex(parent party's color_code)
 *  3. OTH alliance party              → party's own color_code from DB (fallback: grey)
 *  4. Alliance party (LDF/UDF/NDA)    → ALLIANCE_COLORS[alliance]
 */
export function resolvePartyColor(
  code: string,
  alliance: string,
  parties: Party[],
): string {
  // 1. Pure IND
  if (isRawIND(code)) return PURE_IND_COLOR;

  // 2. Supported IND — use lightened parent party color
  if (isSupportedIND(code)) {
    const parent = parentPartyCode(code);
    const parentParty = parties.find(p => p.code === parent);
    const parentColor = parentParty?.color_code ?? ALLIANCE_COLORS[alliance] ?? PURE_IND_COLOR;
    return lightenHex(parentColor, 0.45);
  }

  // 3. OTH alliance → use the party's own color_code
  if (alliance === 'OTH') {
    const party = parties.find(p => p.code === code);
    return party?.color_code ?? PURE_IND_COLOR;
  }

  // 4. Alliance party
  return ALLIANCE_COLORS[alliance] ?? PURE_IND_COLOR;
}

/**
 * Resolve the card background color for a constituency card.
 * Same as resolvePartyColor but intended for use as a bg — OTH and IND
 * cards should be clearly distinguishable (not grey) when they have a color.
 * party_color is the pre-fetched color_code from the API (from DB) for the leader.
 */
export function resolveCardBg(
  code: string,
  alliance: string,
  partyColorFromApi: string,   // leader.party_color from the API
  parties: Party[],
): string {
  if (isRawIND(code)) return PURE_IND_COLOR;

  if (isSupportedIND(code)) {
    const parent = parentPartyCode(code);
    const parentParty = parties.find(p => p.code === parent);
    const parentColor = parentParty?.color_code ?? ALLIANCE_COLORS[alliance] ?? PURE_IND_COLOR;
    return lightenHex(parentColor, 0.45);
  }

  if (alliance === 'OTH') {
    // Prefer the fresh API color_code; fall back to parties lookup
    if (partyColorFromApi && partyColorFromApi !== '#808080') return partyColorFromApi;
    const party = parties.find(p => p.code === code);
    return party?.color_code ?? PURE_IND_COLOR;
  }

  return ALLIANCE_COLORS[alliance] ?? PURE_IND_COLOR;
}
