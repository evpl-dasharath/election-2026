// Election data types - updated 10k threshold

export type Alliance = 'UDF' | 'LDF' | 'NDA' | 'OTH';

export type CountingStatus = 
  | 'NOT_STARTED' 
  | 'IN_PROGRESS' 
  | 'COMPLETED' 
  | 'RESULT_DECLARED';

export type ReservedCategory = 'GEN' | 'SC' | 'ST';

export interface Party {
  code: string;
  name: string;
  full_name?: string;
  alliance: Alliance;
  color_code?: string;   // field name returned by the API serializer
  color?: string;        // legacy alias kept for compatibility
}

export interface Candidate {
  name: string;
  party: string;
  alliance: Alliance;
  votes: number;
  percentage: number;
  is_winner: boolean;
  is_leading: boolean;
  party_color: string;
}

export interface LiveResult {
  status: CountingStatus;
  total_electors: number;
  votes_polled: number;
  votes_counted: number;
  valid_votes: number;
  rejected_votes: number;
  rounds_completed: number;
  total_rounds: number;
  last_updated: string | null;
}

export type Region = 'north' | 'central_north' | 'south_central' | 'south';

export interface ConstituencyListItem {
  id: number;
  number: number;
  name: string;
  district: string;
  region: Region;
  reserved: string;
  status: CountingStatus;
  votes_counted?: number;
  rounds_completed?: number;
  total_rounds?: number;
  sitting_party: string | null;
  sitting_alliance: Alliance | null;
  // Polling-day static fields (from electoral rolls / ECI polling data)
  total_electors: number;   // never changes
  votes_polled: number;     // finalised after polling day, before counting
  total_valid: number;      // total valid votes counted in 2026
  leader: {
    name: string;
    party: string;
    alliance: Alliance;
    votes: number;
    percentage: number;
    party_color: string;  // hex from DB Party.color_code
  } | null;
  runner_up: {
    name: string;
    party: string;
    alliance: Alliance;
    votes: number;
    percentage: number;
    party_color: string;
  } | null;
  // Extra fields injected by Alliance/Party detail endpoints
  alliance_pos?: number | null;
  margin_to_second?: number | null;
  alliance_votes?: number;
  party_pos?: number | null;
  party_votes?: number;
  party_candidate_name?: string | null;
  alliance_candidate_name?: string | null;
  alliance_party_code?: string | null;
  margin?: number | null;
  voteShare?: number;
}

export interface ConstituencyDetail {
  constituency: {
    id: number;
    number: number;
    name: string;
    district: string;
  };
  live_result: LiveResult | null;
  candidates_2026: Candidate[];
  results_2021: Historical2021Candidate[];
}

export interface Historical2021Candidate {
  candidate: string;
  party: string;
  votes: number;
  percentage: number;
  is_winner: boolean;
  alliance: Alliance;
  color_code: string;
}

export interface Historical2011Candidate {
  candidate: string;
  party: string;
  votes: number;
  percentage: number;
  is_winner: boolean;
  alliance: Alliance;
  color_code: string;
}

export interface Historical2016Candidate {
  candidate: string;
  party: string;
  votes: number;
  percentage: number;
  is_winner: boolean;
  alliance: Alliance;
  color_code: string;
}

export interface Historical2011 {
  margin: number;
  alliance_shares: Record<Alliance, number>;
  candidates: Historical2011Candidate[];
}

export interface Historical2016 {
  winner_candidate: string;
  winner_party: string;
  winner_alliance: string;
  winner_votes: number;
  winner_percentage: number;
  runnerup_candidate: string;
  runnerup_party: string;
  runnerup_alliance: string;
  runnerup_votes: number;
  runnerup_percentage: number;
  margin: number;
  /** Full alliance vote-share aggregates from all candidates */
  alliance_shares: Record<Alliance, number>;
  /** All candidates from the 2016 election (excl. NOTA) */
  candidates: Historical2016Candidate[];
}

export interface ParliamentResult {
  year: number;
  constituency_name: string;
  parliament_constituency: string;
  udf_votes: number;
  ldf_votes: number;
  nda_votes: number;
  lead_alliance: Alliance;
  runnerup_alliance: Alliance;
  margin: number;
}

export interface HistoricalComparison {
  constituency: {
    number: number;
    name: string;
    district: string;
  };
  la_2021: {
    winner: string | null;
    party: string | null;
    margin: number | null;
    /** Alliance vote-share aggregates from all candidates in 2021 */
    alliance_shares: Record<Alliance, number>;
    candidates: Historical2021Candidate[];
  };
  la_2016: Historical2016 | null;
  la_2011: Historical2011 | null;
  ls_2019: ParliamentResult | null;
  ls_2024: ParliamentResult | null;
}

export interface StateSummary {
  timestamp?: string;
  total_constituencies: number;
  results_declared: number;
  counting_in_progress: number;
  not_started?: number;
  alliance_summary: {
    [K in Alliance]: {
      won: number;
      leading: number;
      trailing: number;
      vote_share?: number;
    };
  };
  /** Pure IND (party code exactly 'IND') — separate from OTH alliance_summary */
  ind_summary: {
    won: number;
    leading: number;
  };
  total_votes_counted: number;
  total_votes_polled?: number;

}

export interface District {
  id: number;
  name: string;
  order: number;
}

// Admin panel types
export interface AdminUpdatePayload {
  constituency_id: number;
  candidates: {
    id?: number;
    name: string;
    party: string;
    votes: number;
  }[];
  live_result: {
    status: CountingStatus;
    votes_counted: number;
    valid_votes: number;
    rounds_completed: number;
    total_rounds: number;
  };
}

// ─── Alliance & Party page types ──────────────────────────────────────────────

export interface PartyInAlliance {
  code: string;
  name: string;
  color: string;
  contested: number;
  won: number;
  leading: number;
  seats_2nd: number;
  seats_close_3rd: number;
  seats_distant_3rd: number;
  vote_share: number;
  vote_share_2021_pct: number;
}

export interface AllianceSummary {
  alliance: string;
  seats_won: number;
  seats_leading: number;
  seats_2nd: number;
  seats_close_3rd: number;
  seats_distant_3rd: number;
  seats_trailing: number;
  seats_contested: number;
  total_votes: number;
  vote_share: number;
  vote_share_2021_pct: number;
  best_margin: { constituency: string; margin: number } | null;
  worst_margin: { constituency: string; margin: number } | null;
  seat_movement: { gained: number; held: number; lost: number; pushed_to_3rd: number; pulled_up_to_2nd: number };
  swing_analysis: {
    gained_from: { LDF: number; UDF: number; NDA: number; OTH: number };
    lost_to: { LDF: number; UDF: number; NDA: number; OTH: number };
  };
  parties: PartyInAlliance[];
  constituencies: (ConstituencyListItem & { competing: boolean })[];
}

export interface PartyDetailFull {
  code: string;
  full_name: string;
  alliance: string;
  color_code: string;
  seats_contested: number;
  seats_won: number;
  seats_leading: number;
  seats_2nd: number;
  seats_close_3rd: number;
  seats_distant_3rd: number;
  seats_trailing: number;
  total_votes: number;
  vote_share: number;
  vote_share_2021_pct: number;
  constituencies: ConstituencyListItem[];
}

