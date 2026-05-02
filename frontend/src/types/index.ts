// Election data types

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
  sitting_party: string | null;
  sitting_alliance: Alliance | null;
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
    };
  };
  /** Pure IND (party code exactly 'IND') — separate from OTH alliance_summary */
  ind_summary: {
    won: number;
    leading: number;
  };
  total_votes_counted: number;
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
