export type SeatClass = 'Stronghold' | 'Fragile' | 'Leaning' | 'Swing' | "Opponent's";
export type Alliance = 'LDF' | 'UDF' | 'NDA';

// Window: 2011, 2016, 2021 (3 elections post-delimitation)
// Margin thresholds
const LARGE_MARGIN = 5000;
const TIGHT_MARGIN = 2000;

export interface ElectionResult {
  winner: string;
  winner_party: string;
  winner_alliance: string;
  margin: number | null;
}

export interface ConstituencyHistory {
  constituency_number: number;
  constituency_name: string;
  district: string;
  la_2011: ElectionResult | null;
  la_2016: ElectionResult | null;
  la_2021: ElectionResult | null;
  la_2026?: ElectionResult | null; // live/final
  ls_2019?: ElectionResult | null;
  ls_2024?: ElectionResult | null;
}

export function classifyForAlliance(
  alliance: Alliance,
  results: (ElectionResult | null)[],  // [2011, 2016, 2021]
): SeatClass {
  const [r11, r16, r21] = results;

  const w11 = r11?.winner_alliance === alliance;
  const w16 = r16?.winner_alliance === alliance;
  const w21 = r21?.winner_alliance === alliance;

  const m11 = r11?.margin ?? 0;
  const m16 = r16?.margin ?? 0;
  const m21 = r21?.margin ?? 0;

  // Stronghold / Fragile / Leaning: won all 3
  if (w11 && w16 && w21) {
    const tightCount = (m11 < TIGHT_MARGIN ? 1 : 0) + (m16 < TIGHT_MARGIN ? 1 : 0) + (m21 < TIGHT_MARGIN ? 1 : 0);
    if (tightCount >= 2) return 'Fragile';

    const hugeCount = (m11 >= 15000 ? 1 : 0) + (m16 >= 15000 ? 1 : 0) + (m21 >= 15000 ? 1 : 0);
    const noSmall = m11 >= 5000 && m16 >= 5000 && m21 >= 5000;
    
    if (hugeCount >= 2 && noSmall) return 'Stronghold';
    
    return 'Leaning';
  }

  // Leaning: won last 2 (✗✓✓)
  if (!w11 && w16 && w21) {
    if (m16 < TIGHT_MARGIN && m21 < TIGHT_MARGIN) return 'Swing';
    
    // Explicit rule: If it was UDF in 2011, and swung to LDF for '16 and '21, consider it a Swing seat overall.
    if (alliance === 'LDF' && r11?.winner_alliance === 'UDF') return 'Swing';
    
    return 'Leaning';
  }

  // Swing: alternating ✓✗✓
  if (w11 && !w16 && w21) {
    // Large wins bookending a tight loss → Leaning
    if (m11 >= LARGE_MARGIN && m21 >= LARGE_MARGIN && m16 < TIGHT_MARGIN) return 'Leaning';
    return 'Swing';
  }

  return "Opponent's";
}

// Compute classification for all three alliances and pick the one that
// "owns" this seat. If multiple alliances qualify (impossible by logic but
// guard anyway), LDF > UDF > NDA priority.
export function classifySeat(history: ConstituencyHistory): {
  seatClass: SeatClass;
  ownerAlliance: Alliance | null;
} {
  const results = [history.la_2011, history.la_2016, history.la_2021];
  const alliances: Alliance[] = ['LDF', 'UDF', 'NDA'];

  for (const al of alliances) {
    const cls = classifyForAlliance(al, results);
    if (cls === 'Stronghold' || cls === 'Fragile' || cls === 'Leaning') {
      return { seatClass: cls, ownerAlliance: al };
    }
  }
  return { seatClass: 'Swing', ownerAlliance: null };
}
