import { useState, useEffect } from 'react';
import type {
  StateSummary,
  ConstituencyListItem,
  ConstituencyDetail,
  HistoricalComparison,
  Party,
  AllianceSummary,
  PartyDetailFull,
} from '../types';
import { db } from '../firebase';
import { ref, onValue } from 'firebase/database';

// ─── Data source tracking ─────────────────────────────────────────────────────
export type DataSource = 'live' | 'cached-json' | 'unknown';
let _dataSource: DataSource = 'unknown';
let _cachedJsonLoadedAt: number | null = null; // ms timestamp when fallback was loaded
const _dataSourceCallbacks = new Set<(src: DataSource, ts: number | null) => void>();

/** Seed the cache timestamp from the deployed meta.json's generated_at field if present. */
function _seedCacheTimestampFromMeta(meta: any) {
  if (meta?.generated_at && _cachedJsonLoadedAt === null) {
    const parsed = Date.parse(meta.generated_at);
    if (!isNaN(parsed)) _cachedJsonLoadedAt = parsed;
  }
}

function _setDataSource(src: DataSource) {
  if (src === 'cached-json' && _dataSource !== 'cached-json') {
    // Only set to now if not already seeded from meta.json generated_at
    if (_cachedJsonLoadedAt === null) _cachedJsonLoadedAt = Date.now();
  } else if (src === 'live') {
    _cachedJsonLoadedAt = null;
  }
  _dataSource = src;
  _dataSourceCallbacks.forEach(cb => cb(_dataSource, _cachedJsonLoadedAt));
}

export function useDataSource(): { source: DataSource; cachedAt: number | null } {
  const [source, setSource] = useState<DataSource>(_dataSource);
  const [cachedAt, setCachedAt] = useState<number | null>(_cachedJsonLoadedAt);
  useEffect(() => {
    const cb = (src: DataSource, ts: number | null) => {
      setSource(src);
      setCachedAt(ts);
    };
    _dataSourceCallbacks.add(cb);
    return () => { _dataSourceCallbacks.delete(cb); };
  }, []);
  return { source, cachedAt };
}

// ─── RTDB connection state ────────────────────────────────────────────────────
let _rtdbConnected: boolean = true; // optimistically assume connected
const _connCallbacks = new Set<(connected: boolean) => void>();

function _notifyConnected(connected: boolean) {
  const wasConnected = _rtdbConnected;
  _rtdbConnected = connected;
  _connCallbacks.forEach(cb => cb(connected));
  // When connection is restored after being down → flush cache & re-fetch
  if (!wasConnected && connected) {
    _setDataSource('unknown'); // will resolve to 'live' once Firebase delivers data
    clearElectionDataCache();
  }
  if (!connected) {
    // Mark as cached-json source when disconnected (hooks will fall back)
    _setDataSource('cached-json');
  }
}

// Start .info/connected listener once at module level
let _infoConnectedStarted = false;
function _ensureInfoConnectedListener() {
  if (_infoConnectedStarted) return;
  _infoConnectedStarted = true;
  _setDataSource('cached-json');
  _notifyConnected(false);
}

/**
 * Returns whether the Firebase RTDB connection is currently active.
 * Automatically re-fetches all data when connection is restored.
 */
export function useRtdbConnected(): boolean {
  const [connected, setConnected] = useState(_rtdbConnected);
  useEffect(() => {
    _ensureInfoConnectedListener();
    const cb = (c: boolean) => setConnected(c);
    _connCallbacks.add(cb);
    return () => { _connCallbacks.delete(cb); };
  }, []);
  return connected;
}

// Environment-based data source
const USE_API = false;
const API_BASE_URL = 'http://localhost:8001/api';
const JSON_BASE_PATH = '/data';

// ─── Module-level cache ───────────────────────────────────────────────────────
let _summaryCache: StateSummary | null = null;
let _constituenciesCache: ConstituencyListItem[] | null = null;
let _partiesCache: Party[] | null = null;
import { ConstituencyHistory } from '../utils/seatClassification';
let _allHistoricalCache: ConstituencyHistory[] | null = null;
const _constituencyDetailCache: Record<number, ConstituencyDetail> = {};
const _historicalCache: Record<number, HistoricalComparison> = {};
const _allianceCache: Record<string, AllianceSummary> = {};
const _partyDetailCache: Record<string, PartyDetailFull> = {};
let _allResultDetailsCache: ConstituencyDetail[] | null = null;
let _historicalIndexCache: Record<string, HistoricalComparison> | null = null;

// ─── RTDB last-update timestamp (for staleness detection) ──────────────────
let _lastRtdbUpdate: number | null = null;
const _staleCallbacks = new Set<(ts: number | null) => void>();

export function getLastRtdbUpdate(): number | null {
  return _lastRtdbUpdate;
}
function _notifyStale(ts: number | null) {
  _lastRtdbUpdate = ts;
  _staleCallbacks.forEach(cb => cb(ts));
}

export function useLastRtdbUpdate() {
  const [ts, setTs] = useState<number | null>(_lastRtdbUpdate);
  useEffect(() => {
    const cb = (t: number | null) => setTs(t);
    _staleCallbacks.add(cb);
    return () => { _staleCallbacks.delete(cb); };
  }, []);
  return ts;
}

// ─── Refresh callbacks ────────────────────────────────────────────────────────
const _refreshCallbacks = new Set<() => void>();

export function clearElectionDataCache() {
  _summaryCache = null;
  _constituenciesCache = null;
  _partiesCache = null;
  _allHistoricalCache = null;
  Object.keys(_constituencyDetailCache).forEach(k => delete _constituencyDetailCache[+k]);
  Object.keys(_historicalCache).forEach(k => delete _historicalCache[+k]);
  Object.keys(_allianceCache).forEach(k => delete _allianceCache[k]);
  Object.keys(_partyDetailCache).forEach(k => delete _partyDetailCache[k]);
  _allResultDetailsCache = null;
  _historicalIndexCache = null;
  _refreshCallbacks.forEach(cb => cb());
}

async function _ensureStaticConstituencies(): Promise<ConstituencyListItem[]> {
  if (_constituenciesCache) return _constituenciesCache;
  const res = await fetch(`${JSON_BASE_PATH}/constituencies.json`);
  const json: ConstituencyListItem[] = await res.json();
  _constituenciesCache = json;
  return json;
}

async function _ensureStaticParties(): Promise<Party[]> {
  if (_partiesCache) return _partiesCache;
  const res = await fetch(`${JSON_BASE_PATH}/parties.json`);
  const json: Party[] = await res.json();
  _partiesCache = json;
  return json;
}

async function _ensureStaticHistoricalIndex(): Promise<Record<string, HistoricalComparison>> {
  if (_historicalIndexCache) return _historicalIndexCache;
  const res = await fetch(`${JSON_BASE_PATH}/historical.json`);
  const json: Record<string, HistoricalComparison> = await res.json();
  _historicalIndexCache = json;
  return json;
}

async function _ensureAllStaticResultDetails(): Promise<ConstituencyDetail[]> {
  if (_allResultDetailsCache) return _allResultDetailsCache;
  const constituencies = await _ensureStaticConstituencies();
  const results = await Promise.all(
    constituencies.map(async (c) => {
      const res = await fetch(`${JSON_BASE_PATH}/results/${c.number.toString().padStart(3, '0')}.json`);
      if (!res.ok) {
        throw new Error(`Missing static result for constituency ${c.number}`);
      }
      return res.json() as Promise<ConstituencyDetail>;
    })
  );
  _allResultDetailsCache = results;
  return results;
}

function _getAllianceFromPartyCode(partyCode: string, parties: Party[]): string {
  return parties.find((party) => party.code === partyCode)?.alliance || 'OTH';
}

async function _buildAllianceSummaryFromStatic(code: string): Promise<AllianceSummary> {
  const allianceCode = code.toUpperCase();
  const parties = await _ensureStaticParties();
  const constituencies = await _ensureStaticConstituencies();
  const results = await _ensureAllStaticResultDetails();
  const historical = await _ensureStaticHistoricalIndex();
  const partiesInAlliance = parties.filter((party) => party.alliance === allianceCode);
  const partyCodes = new Set(partiesInAlliance.map((party) => party.code));
  const partyStats: Record<string, {
    code: string;
    name: string;
    color: string;
    contested: number;
    won: number;
    leading: number;
    seats_2nd: number;
    seats_close_3rd: number;
    seats_distant_3rd: number;
    votes: number;
    votes2021: number;
  }> = {};

  partiesInAlliance.forEach((party) => {
    partyStats[party.code] = {
      code: party.code,
      name: party.full_name || party.name,
      color: party.color_code || party.color || '#808080',
      contested: 0,
      won: 0,
      leading: 0,
      seats_2nd: 0,
      seats_close_3rd: 0,
      seats_distant_3rd: 0,
      votes: 0,
      votes2021: 0,
    };
  });

  let totalValidVotes2026 = 0;
  let allianceVotes2026 = 0;
  let totalVotes2021 = 0;
  let allianceVotes2021 = 0;
  let seatsWon = 0;
  let seatsLeading = 0;
  let gained = 0;
  let held = 0;
  let lost = 0;
  let bestMargin: { constituency: string; margin: number } | null = null;
  let worstMargin: { constituency: string; margin: number } | null = null;
  let seats2nd = 0;
  let seatsClose3rd = 0;
  let seatsDistant3rd = 0;
  let seatsTrailing = 0;
  const gainedFrom = { LDF: 0, UDF: 0, NDA: 0, OTH: 0 };
  const lostTo = { LDF: 0, UDF: 0, NDA: 0, OTH: 0 };

  const constituencyByNumber = new Map(constituencies.map((c) => [c.number, c]));

  results.forEach((result) => {
    const constituency = constituencyByNumber.get(result.constituency.number);
    if (!constituency) return;

    const candidates2026 = result.candidates_2026.filter((candidate) => candidate.party !== 'NOTA');
    const topTwo2026 = [...candidates2026].sort((a, b) => b.votes - a.votes).slice(0, 2);
    const contestingParties = new Set<string>();

    candidates2026.forEach((candidate) => {
      totalValidVotes2026 += candidate.votes;
      contestingParties.add(candidate.party);
      if (partyCodes.has(candidate.party)) {
        allianceVotes2026 += candidate.votes;
        if (!partyStats[candidate.party]) {
          partyStats[candidate.party] = {
            code: candidate.party,
            name: candidate.party,
            color: parties.find((party) => party.code === candidate.party)?.color_code || '#808080',
            contested: 0,
            won: 0,
            leading: 0,
            seats_2nd: 0,
            seats_close_3rd: 0,
            seats_distant_3rd: 0,
            votes: 0,
            votes2021: 0,
          };
        }
        partyStats[candidate.party].votes += candidate.votes;
      }
    });

    contestingParties.forEach((partyCode) => {
      if (partyCodes.has(partyCode) && partyStats[partyCode]) {
        partyStats[partyCode].contested += 1;
      }
    });

    const history = historical[String(result.constituency.number)];
    history?.la_2021?.candidates?.forEach((candidate) => {
      totalVotes2021 += candidate.votes;
      if (candidate.alliance === allianceCode) allianceVotes2021 += candidate.votes;
      if (partyCodes.has(candidate.party) && partyStats[candidate.party]) {
        partyStats[candidate.party].votes2021 += candidate.votes;
      }
    });

    const status = result.live_result?.status || constituency.status;
    const leader = topTwo2026[0];
    const runnerUp = topTwo2026[1];
    const hasStarted = status === 'IN_PROGRESS' || status === 'RESULT_DECLARED' || status === 'COMPLETED';
    const currentAlliance = leader?.alliance || null;
    const historicalWinnerAlliance =
      history?.la_2021?.candidates?.find((candidate) => candidate.is_winner)?.alliance || null;
    const sittingAlliance = historicalWinnerAlliance || constituency.sitting_alliance || null;

    if (leader && leader.party && partyStats[leader.party]) {
      if (status === 'RESULT_DECLARED' || status === 'COMPLETED') {
        partyStats[leader.party].won += 1;
      } else if (status === 'IN_PROGRESS') {
        partyStats[leader.party].leading += 1;
      }
    }

    if (hasStarted && leader) {
      if (currentAlliance === allianceCode) {
        if (status === 'RESULT_DECLARED' || status === 'COMPLETED') seatsWon += 1;
        else if (status === 'IN_PROGRESS') seatsLeading += 1;

        if (sittingAlliance === allianceCode) held += 1;
        else {
          gained += 1;
          const bucket = (sittingAlliance && sittingAlliance in gainedFrom ? sittingAlliance : 'OTH') as keyof typeof gainedFrom;
          gainedFrom[bucket] += 1;
        }
      } else if (sittingAlliance === allianceCode && currentAlliance) {
        lost += 1;
        const bucket = (currentAlliance in lostTo ? currentAlliance : 'OTH') as keyof typeof lostTo;
        lostTo[bucket] += 1;
      }
    }

    // Determine alliance placement for this constituency
    if (topTwo2026.length > 0) {
      const p1 = _getAllianceFromPartyCode(candidates2026[0]?.party, parties);
      const p2Code = candidates2026[1]?.party;
      const p2 = p2Code ? _getAllianceFromPartyCode(p2Code, parties) : null;
      const p3Code = candidates2026[2]?.party;
      const p3 = p3Code ? _getAllianceFromPartyCode(p3Code, parties) : null;
      
      if (p2 === allianceCode) {
        seats2nd += 1;
        if (p2Code && partyStats[p2Code]) partyStats[p2Code].seats_2nd += 1;
      } else if (p3 === allianceCode) {
        const marginToSecond = candidates2026[1].votes - candidates2026[2].votes;
        if (marginToSecond < 10000) {
          seatsClose3rd += 1;
          if (p3Code && partyStats[p3Code]) partyStats[p3Code].seats_close_3rd += 1;
        } else {
          seatsDistant3rd += 1;
          if (p3Code && partyStats[p3Code]) partyStats[p3Code].seats_distant_3rd += 1;
        }
      } else if (p1 !== allianceCode) {
        // If not 1st, not 2nd, not 3rd, it's trailing further
        if (candidates2026.some(c => _getAllianceFromPartyCode(c.party, parties) === allianceCode)) {
          seatsTrailing += 1;
        }
      }
    }

    if (leader && runnerUp && currentAlliance === allianceCode) {
      const margin = leader.votes - runnerUp.votes;
      if (!bestMargin || margin > bestMargin.margin) {
        bestMargin = { constituency: result.constituency.name, margin };
      }
      if (!worstMargin || margin < worstMargin.margin) {
        worstMargin = { constituency: result.constituency.name, margin };
      }
    }
  });

  const partiesData = Object.values(partyStats)
    .filter((party) => party.contested > 0 || party.votes > 0 || party.votes2021 > 0)
    .map((party) => ({
      code: party.code,
      name: party.name,
      color: party.color,
      contested: party.contested,
      won: party.won,
      leading: party.leading,
      seats_2nd: party.seats_2nd,
      seats_close_3rd: party.seats_close_3rd,
      seats_distant_3rd: party.seats_distant_3rd,
      vote_share: totalValidVotes2026 > 0 ? (party.votes / totalValidVotes2026) * 100 : 0,
      vote_share_2021_pct: totalVotes2021 > 0 ? (party.votes2021 / totalVotes2021) * 100 : 0,
    }))
    .sort((a, b) => (b.won + b.leading) - (a.won + a.leading) || b.vote_share - a.vote_share);

  return {
    alliance: allianceCode,
    seats_won: seatsWon,
    seats_leading: seatsLeading,
    seats_2nd: seats2nd,
    seats_close_3rd: seatsClose3rd,
    seats_distant_3rd: seatsDistant3rd,
    seats_trailing: seatsTrailing,
    seats_contested: partiesData.reduce((sum, party) => sum + party.contested, 0),
    total_votes: allianceVotes2026,
    vote_share: totalValidVotes2026 > 0 ? (allianceVotes2026 / totalValidVotes2026) * 100 : 0,
    vote_share_2021_pct: totalVotes2021 > 0 ? (allianceVotes2021 / totalVotes2021) * 100 : 0,
    best_margin: bestMargin,
    worst_margin: worstMargin,
    seat_movement: { gained, held, lost, pushed_to_3rd: 0, pulled_up_to_2nd: 0 },
    swing_analysis: { gained_from: gainedFrom, lost_to: lostTo },
    parties: partiesData,
    constituencies: constituencies.map((constituency) => ({
      ...constituency,
      competing: results
        .find((result) => result.constituency.number === constituency.number)
        ?.candidates_2026.some((candidate) => candidate.party !== 'NOTA' && _getAllianceFromPartyCode(candidate.party, parties) === allianceCode) || false,
    })),
  };
}

async function _buildPartyDetailFromStatic(code: string): Promise<PartyDetailFull> {
  const partyCode = code.toUpperCase();
  const parties = await _ensureStaticParties();
  const constituencies = await _ensureStaticConstituencies();
  const results = await _ensureAllStaticResultDetails();
  const historical = await _ensureStaticHistoricalIndex();
  const party = parties.find((item) => item.code.toUpperCase() === partyCode);

  if (!party) {
    throw new Error(`Party not found: ${code}`);
  }

  let totalValidVotes2026 = 0;
  let partyVotes2026 = 0;
  let totalVotes2021 = 0;
  let partyVotes2021 = 0;
  let seatsWon = 0;
  let seatsLeading = 0;
  let seats2nd = 0;
  let seatsClose3rd = 0;
  let seatsDistant3rd = 0;
  let seatsTrailing = 0;
  const contestedNumbers = new Set<number>();

  results.forEach((result) => {
    const candidates2026 = result.candidates_2026.filter((candidate) => candidate.party !== 'NOTA');
    const leader = [...candidates2026].sort((a, b) => b.votes - a.votes)[0];
    const status = result.live_result?.status;

    candidates2026.forEach((candidate) => {
      totalValidVotes2026 += candidate.votes;
      if (candidate.party.toUpperCase() === partyCode) {
        contestedNumbers.add(result.constituency.number);
        partyVotes2026 += candidate.votes;
      }
    });

    historical[String(result.constituency.number)]?.la_2021?.candidates?.forEach((candidate) => {
      totalVotes2021 += candidate.votes;
      if (candidate.party.toUpperCase() === partyCode) {
        partyVotes2021 += candidate.votes;
      }
    });

    if (leader?.party.toUpperCase() === partyCode) {
      if (status === 'RESULT_DECLARED' || status === 'COMPLETED') seatsWon += 1;
      else if (status === 'IN_PROGRESS') seatsLeading += 1;
    } else {
      const p2 = candidates2026[1]?.party.toUpperCase();
      const p3 = candidates2026[2]?.party.toUpperCase();
      if (p2 === partyCode) {
        seats2nd += 1;
      } else if (p3 === partyCode) {
        const marginToSecond = candidates2026[1].votes - candidates2026[2].votes;
        if (marginToSecond < 10000) {
          seatsClose3rd += 1;
        } else {
          seatsDistant3rd += 1;
        }
      } else {
        if (candidates2026.some(c => c.party.toUpperCase() === partyCode)) {
          seatsTrailing += 1;
        }
      }
    }
  });

  return {
    code: party.code,
    full_name: party.full_name || party.name,
    alliance: party.alliance,
    color_code: party.color_code || party.color || '#808080',
    seats_contested: contestedNumbers.size,
    seats_won: seatsWon,
    seats_leading: seatsLeading,
    seats_2nd: seats2nd,
    seats_close_3rd: seatsClose3rd,
    seats_distant_3rd: seatsDistant3rd,
    seats_trailing: seatsTrailing,
    total_votes: partyVotes2026,
    vote_share: totalValidVotes2026 > 0 ? (partyVotes2026 / totalValidVotes2026) * 100 : 0,
    vote_share_2021_pct: totalVotes2021 > 0 ? (partyVotes2021 / totalVotes2021) * 100 : 0,
    constituencies: constituencies.filter((constituency) => contestedNumbers.has(constituency.number)),
  };
}

/**
 * Fire-and-forget prefetch — populates the cache silently, no React re-renders.
 */
export async function prefetchConstituencyDetail(constituencyId: number): Promise<void> {
  if (_constituencyDetailCache[constituencyId]) return;
  try {
    if (USE_API) {
      const res = await fetch(`${API_BASE_URL}/constituencies/${constituencyId}/`);
      if (!res.ok) return;
      _constituencyDetailCache[constituencyId] = await res.json();
    } else {
      if (!_constituenciesCache) return;
      const c = _constituenciesCache.find(x => x.id === constituencyId);
      if (!c) return;
      const res = await fetch(
        `${JSON_BASE_PATH}/results/${c.number.toString().padStart(3, '0')}.json`
      );
      if (!res.ok) return;
      _constituencyDetailCache[constituencyId] = await res.json();
    }
  } catch {
    // Silently ignore prefetch errors
  }
}

// ─── Hooks ───────────────────────────────────────────────────────────────────

export function useStateSummary() {
  const [data, setData] = useState<StateSummary | null>(_summaryCache);
  const [loading, setLoading] = useState(_summaryCache === null);
  const [error, setError] = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0);

  useEffect(() => {
    const cb = () => setTrigger(t => t + 1);
    _refreshCallbacks.add(cb);
    return () => { _refreshCallbacks.delete(cb); };
  }, []);

  useEffect(() => {
    let unsubscribe = () => { };

    const fetchStaticData = async (markAsCached = true) => {
      try {
        setLoading(true);
        let json: StateSummary;
        if (USE_API) {
          const res = await fetch(`${API_BASE_URL}/summary/`);
          json = await res.json();
        } else {
          const res = await fetch(`${JSON_BASE_PATH}/meta.json`);
          json = await res.json();
          // Seed cache timestamp from the deploy-time generated_at field
          _seedCacheTimestampFromMeta(json);
        }
        // Always update — don't guard with cache check so refresh works
        _summaryCache = json;
        setData(json);
        if (markAsCached) _setDataSource('cached-json');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch summary');
      } finally {
        setLoading(false);
      }
    };

    const setupLive = () => {
      const metaRef = ref(db, 'meta');
      unsubscribe = onValue(metaRef, (snapshot) => {
        if (snapshot.exists()) {
          const liveData = snapshot.val();
          if (liveData && liveData.alliance_summary) {
            _summaryCache = liveData;
            setData({ ...liveData }); // always spread to force re-render
            setLoading(false);
            _notifyStale(Date.now());
            _setDataSource('live');
          } else {
            fetchStaticData();
          }
        } else {
          fetchStaticData();
        }
      }, (err) => {
        console.error('RTDB error for summary:', err);
        fetchStaticData();
      });
    };

    setupLive();

    return () => unsubscribe();
  }, [trigger]);

  return { data, loading, error };
}

export function useConstituencies() {
  const [data, setData] = useState<ConstituencyListItem[]>(_constituenciesCache ?? []);
  const [loading, setLoading] = useState(_constituenciesCache === null);
  const [error, setError] = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0);

  useEffect(() => {
    const cb = () => setTrigger(t => t + 1);
    _refreshCallbacks.add(cb);
    return () => { _refreshCallbacks.delete(cb); };
  }, []);

  useEffect(() => {
    let unsubscribe = () => { };

    const fetchAndListen = async () => {
      try {
        setLoading(true);
        if (!_constituenciesCache) {
          let json: ConstituencyListItem[];
          if (USE_API) {
            const res = await fetch(`${API_BASE_URL}/constituencies/`);
            const raw = await res.json();
            json = raw.results || raw;
          } else {
            const res = await fetch(`${JSON_BASE_PATH}/constituencies.json`);
            json = await res.json();
          }
          _constituenciesCache = json;
        }

        // Ensure parties cache for live candidate alliance/color lookup
        if (!_partiesCache) {
          const pres = await fetch(USE_API ? `${API_BASE_URL}/parties/` : `${JSON_BASE_PATH}/parties.json`);
          const praw = await pres.json();
          _partiesCache = praw.results || praw;
        }

        // The JSON snapshot now contains real vote data exported at deploy time.
        // Keep it as-is — RTDB will override it once connected.
        // (No longer zeroing status/leader/runner_up here.)

        setData([..._constituenciesCache!]);
        setLoading(false);
        // Mark as cached-json until RTDB delivers live data
        _setDataSource('cached-json');

        _ensureInfoConnectedListener();

        const liveRef = ref(db, 'live');
        unsubscribe = onValue(liveRef, (snapshot) => {
          if (snapshot.exists()) {
            const liveData = snapshot.val();
            _notifyStale(Date.now());
            _setDataSource('live');

            const merged = _constituenciesCache!.map(c => {
              const liveAc = liveData[c.number];
              if (liveAc) {
                // Clone, preserving all original fields (region, district, sitting_alliance, etc.)
                const totalVotesForItem = (liveAc.candidates || [])
                  .reduce((s: number, cc: any) => s + (cc.votes || 0), 0);
                const newC: ConstituencyListItem = {
                  ...c,
                  status: liveAc.status,
                  votes_counted: totalVotesForItem,
                  // votes_polled: use the higher of stored polling-day figure or actual counted
                  // (ECI/DB mismatch means counted can exceed stored polled)
                  votes_polled: Math.max(c.votes_polled || 0, totalVotesForItem),
                  rounds_completed: liveAc.rounds_completed ?? 0,
                  total_rounds: liveAc.total_rounds ?? 0,
                };

                if (liveAc.status === 'NOT_STARTED') {
                  newC.leader = null;
                  newC.runner_up = null;
                } else if (liveAc.candidates && liveAc.candidates.length > 0) {
                  const sorted = [...liveAc.candidates].sort((a: any, b: any) => b.votes - a.votes);

                  const getPartyInfo = (pCode: string) => {
                    const p = _partiesCache?.find(x => x.code === pCode);
                    return { alliance: p?.alliance || 'OTH', color: p?.color_code || p?.color || '#999999' };
                  };

                  const totalVotesCounted = sorted.reduce((s: number, c: any) => s + c.votes, 0);
                  // Use votes_polled as denominator if available AND >= total counted.
                  // If votes_polled < total counted (DB/ECI mismatch) fall back to
                  // totalVotesCounted so percentages never exceed 100%.
                  // NOTA is included in totalVotesCounted for an accurate denominator.
                  const voteShareDenominator = (
                    newC.votes_polled && newC.votes_polled > 0 && newC.votes_polled >= totalVotesCounted
                      ? newC.votes_polled
                      : totalVotesCounted > 0 ? totalVotesCounted : 0
                  );

                  // Exclude NOTA from leader/runner-up consideration
                  const nonNota = sorted.filter(
                    (c: any) => c.party !== 'NOTA' && c.name?.toUpperCase() !== 'NOTA'
                  );

                  // Only show a leader/runner-up once at least 1 vote has been counted
                  if (totalVotesCounted > 0 && nonNota.length > 0) {
                    const pInfo = getPartyInfo(nonNota[0].party);
                    newC.leader = {
                      name: nonNota[0].name,
                      party: nonNota[0].party,
                      votes: nonNota[0].votes,
                      percentage: voteShareDenominator > 0 ? (nonNota[0].votes / voteShareDenominator) * 100 : 0,
                      alliance: pInfo.alliance,
                      party_color: pInfo.color
                    };
                  } else {
                    newC.leader = null;
                  }
                  if (totalVotesCounted > 0 && nonNota.length > 1 && nonNota[1].votes > 0) {
                    const pInfo = getPartyInfo(nonNota[1].party);
                    newC.runner_up = {
                      name: nonNota[1].name,
                      party: nonNota[1].party,
                      votes: nonNota[1].votes,
                      percentage: voteShareDenominator > 0 ? (nonNota[1].votes / voteShareDenominator) * 100 : 0,
                      alliance: pInfo.alliance,
                      party_color: pInfo.color
                    };
                  } else {
                    newC.runner_up = null;
                  }
                } else {
                  // candidates array is empty — awaited
                  newC.leader = null;
                  newC.runner_up = null;
                }
                return newC;
              }
              return c;
            });
            setData(merged);
          } else {
            // No live data in RTDB yet — mark source as cached-json (showing static data)
            _setDataSource('cached-json');
          }
        }, (err) => {
          console.error('RTDB error for constituencies:', err);
          // Firebase failed — we already have static data from constituencies.json, just mark it
          _setDataSource('cached-json');
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch constituencies');
        setLoading(false);
      }
    };

    fetchAndListen();
    return () => unsubscribe();
  }, [trigger]);

  return { data, loading, error };
}

export function useConstituencyDetail(constituencyId: number | null) {
  const [data, setData] = useState<ConstituencyDetail | null>(
    constituencyId ? (_constituencyDetailCache[constituencyId] ?? null) : null
  );
  const [loading, setLoading] = useState<boolean>(
    constituencyId !== null && !_constituencyDetailCache[constituencyId ?? 0]
  );
  const [error, setError] = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0);

  useEffect(() => {
    const cb = () => setTrigger(t => t + 1);
    _refreshCallbacks.add(cb);
    return () => { _refreshCallbacks.delete(cb); };
  }, []);

  useEffect(() => {
    if (!constituencyId) { setData(null); return; }

    let unsubscribe = () => { };

    const fetchAndListen = async () => {
      try {
        setLoading(true);
        let baseJson: ConstituencyDetail;
        let staticListItem: ConstituencyListItem | undefined;

        if (_constituencyDetailCache[constituencyId]) {
          baseJson = _constituencyDetailCache[constituencyId];
          // Also try to get static values from list cache
          staticListItem = _constituenciesCache?.find(c => c.id === constituencyId);
        } else {
          if (USE_API) {
            const res = await fetch(`${API_BASE_URL}/constituencies/${constituencyId}/`);
            baseJson = await res.json();
          } else {
            const listRes = await fetch(`${JSON_BASE_PATH}/constituencies.json`);
            const list: ConstituencyListItem[] = await listRes.json();
            const constituency = list.find(c => c.id === constituencyId);
            if (!constituency) throw new Error('Constituency not found');
            staticListItem = constituency; // capture for static fields below
            const res = await fetch(
              `${JSON_BASE_PATH}/results/${constituency.number.toString().padStart(3, '0')}.json`
            );
            baseJson = await res.json();
          }
          _constituencyDetailCache[constituencyId] = baseJson;
        }

        if (!_partiesCache) {
          const pres = await fetch(USE_API ? `${API_BASE_URL}/parties/` : `${JSON_BASE_PATH}/parties.json`);
          const praw = await pres.json();
          _partiesCache = praw.results || praw;
        }

        setData(baseJson);
        setLoading(false);

        const acNumber = baseJson.constituency.number;
        const liveRef = ref(db, `live/${acNumber}`);
        unsubscribe = onValue(liveRef, (snapshot) => {
          if (snapshot.exists()) {
            const liveAc = snapshot.val();
            _notifyStale(Date.now());

            const getPartyInfo = (pCode: string) => {
              const p = _partiesCache?.find(x => x.code === pCode);
              return { alliance: p?.alliance || 'OTH', color: p?.color_code || p?.color || '#999999' };
            };

            const sortedLiveCands = [...(liveAc.candidates || [])].sort((a: any, b: any) => b.votes - a.votes);
            const totalVotesCounted = sortedLiveCands.reduce((sum: number, c: any) => sum + c.votes, 0);
            // Resolve votes_polled from the most-trusted source
            const resolvedVotesPolled =
              (staticListItem?.votes_polled && staticListItem.votes_polled > 0) ? staticListItem.votes_polled
              : (baseJson.live_result?.votes_polled && baseJson.live_result.votes_polled > 0) ? baseJson.live_result.votes_polled
              : (liveAc.votes_polled && liveAc.votes_polled > 0) ? liveAc.votes_polled
              : 0;
            // If votes_polled < total counted (DB/ECI mismatch), use totalVotesCounted
            // so individual percentages never exceed 100%.
            // NOTA is included in totalVotesCounted for an accurate denominator.
            const voteShareDenominator =
              resolvedVotesPolled > 0 && resolvedVotesPolled >= totalVotesCounted
                ? resolvedVotesPolled
                : totalVotesCounted > 0 ? totalVotesCounted : 0;

            // Identify the top non-NOTA candidate for winner/leading flags
            const topNonNota = sortedLiveCands.find(
              (c: any) => c.party !== 'NOTA' && c.name?.toUpperCase() !== 'NOTA'
            );

            const mergedCands = sortedLiveCands.map((c: any) => {
              const pInfo = getPartyInfo(c.party);
              const isNota = c.party === 'NOTA' || c.name?.toUpperCase() === 'NOTA';
              return {
                name: c.name,
                party: c.party,
                alliance: pInfo.alliance,
                votes: c.votes,
                percentage: voteShareDenominator > 0 ? (c.votes / voteShareDenominator) * 100 : 0,
                is_winner: !isNota && liveAc.status === 'RESULT_DECLARED' && c === topNonNota && c.votes > 0,
                is_leading: !isNota && liveAc.status === 'IN_PROGRESS' && c === topNonNota && c.votes > 0,
                party_color: pInfo.color
              };
            });

            const mergedLiveResult = {
              status: liveAc.status,
              total_electors: staticListItem?.total_electors
                || baseJson.live_result?.total_electors
                || liveAc.total_electors
                || 0,
              // votes_polled: use max(stored, counted) to handle ECI/DB mismatch
              // so bar never exceeds 100% and percentage denominator is always valid
              votes_polled: Math.max(
                staticListItem?.votes_polled || 0,
                baseJson.live_result?.votes_polled || 0,
                liveAc.votes_polled || 0,
                totalVotesCounted
              ),
              // votes_counted & valid_votes come from ECI counting feed
              votes_counted: totalVotesCounted,
              valid_votes: totalVotesCounted,
              rejected_votes: liveAc.rejected_votes || baseJson.live_result?.rejected_votes || 0,
              rounds_completed: liveAc.rounds_completed || 0,
              total_rounds: liveAc.total_rounds || 0,
              last_updated: liveAc.last_updated || null
            };

            const merged: ConstituencyDetail = {
              ...baseJson,
              live_result: mergedLiveResult,
              candidates_2026: mergedCands
            };
            // Update cache so navigating back doesn't show stale data
            _constituencyDetailCache[constituencyId] = merged;
            setData(merged);
          }
        });

      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch constituency');
        setLoading(false);
      }
    };

    fetchAndListen();
    return () => unsubscribe();
  }, [constituencyId, trigger]);

  return { data, loading, error };
}

export function useHistoricalComparison(constituencyNumber: number | null) {
  const [data, setData] = useState<HistoricalComparison | null>(
    constituencyNumber ? (_historicalCache[constituencyNumber] ?? null) : null
  );
  const [loading, setLoading] = useState<boolean>(
    constituencyNumber !== null && !_historicalCache[constituencyNumber ?? 0]
  );
  const [error, setError] = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0);

  useEffect(() => {
    const cb = () => setTrigger(t => t + 1);
    _refreshCallbacks.add(cb);
    return () => { _refreshCallbacks.delete(cb); };
  }, []);

  useEffect(() => {
    if (!constituencyNumber) { setData(null); return; }
    if (_historicalCache[constituencyNumber]) {
      setData(_historicalCache[constituencyNumber]);
      setLoading(false);
      return;
    }
    const fetchData = async () => {
      try {
        setLoading(true);
        let json: HistoricalComparison;
        if (USE_API) {
          const res = await fetch(`${API_BASE_URL}/historical/${constituencyNumber}/`);
          json = await res.json();
        } else {
          const res = await fetch(`${JSON_BASE_PATH}/historical.json`);
          const all = await res.json();
          json = all[constituencyNumber.toString()];
        }
        _historicalCache[constituencyNumber] = json;
        setData(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch historical data');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [constituencyNumber, trigger]);

  return { data, loading, error };
}

export function useParties() {
  const [data, setData] = useState<Party[]>(_partiesCache ?? []);
  const [loading, setLoading] = useState(_partiesCache === null);
  const [error, setError] = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0);

  useEffect(() => {
    const cb = () => setTrigger(t => t + 1);
    _refreshCallbacks.add(cb);
    return () => { _refreshCallbacks.delete(cb); };
  }, []);

  useEffect(() => {
    if (_partiesCache !== null) { setData(_partiesCache); setLoading(false); return; }
    const fetchData = async () => {
      try {
        setLoading(true);
        let json: Party[];
        if (USE_API) {
          const res = await fetch(`${API_BASE_URL}/parties/`);
          const raw = await res.json();
          json = raw.results || raw;
        } else {
          const res = await fetch(`${JSON_BASE_PATH}/parties.json`);
          json = await res.json();
        }
        _partiesCache = json;
        setData(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch parties');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [trigger]);

  return { data, loading, error };
}

export function useRefreshData() {
  const [refreshKey, setRefreshKey] = useState(0);
  const refresh = () => setRefreshKey(prev => prev + 1);
  return { refreshKey, refresh };
}

// ─── useAllHistorical ─────────────────────────────────────────────────────────
export function useAllHistorical() {
  const [data, setData] = useState<ConstituencyHistory[]>(_allHistoricalCache as ConstituencyHistory[] ?? []);
  const [loading, setLoading] = useState(_allHistoricalCache === null);
  const [error, setError] = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0);

  useEffect(() => {
    const cb = () => setTrigger(t => t + 1);
    _refreshCallbacks.add(cb);
    return () => { _refreshCallbacks.delete(cb); };
  }, []);

  useEffect(() => {
    if (_allHistoricalCache !== null) {
      setData(_allHistoricalCache);
      setLoading(false);
      return;
    }
    const fetchData = async () => {
      try {
        setLoading(true);
        let json: ConstituencyHistory[];
        if (USE_API) {
          const res = await fetch(`${API_BASE_URL}/history/all/`);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          json = await res.json();
        } else {
          const res = await fetch(`${JSON_BASE_PATH}/history_all.json`);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          json = await res.json();
        }
        _allHistoricalCache = json;
        setData(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch historical data');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [trigger]);

  return { data, loading, error };
}


// ─────────────────────────────────────────────────────────────────────────────
// APPEND TO BOTTOM OF useElectionData.ts
// ─────────────────────────────────────────────────────────────────────────────
// Also add to the top-level import in useElectionData.ts:
//   import type { AllianceSummary, PartyDetailFull } from '../types';
// And add two module-level caches after _historicalCache:
//   const _allianceCache: Record<string, AllianceSummary> = {};
//   const _partyDetailCache: Record<string, PartyDetailFull> = {};
// And in clearElectionDataCache(), add:
//   Object.keys(_allianceCache).forEach(k => delete _allianceCache[k]);
//   Object.keys(_partyDetailCache).forEach(k => delete _partyDetailCache[k]);
// ─────────────────────────────────────────────────────────────────────────────

export function useAllianceSummary(code: string | null) {
  const [data, setData] = useState<AllianceSummary | null>(
    code ? (_allianceCache[code] ?? null) : null
  );
  const [loading, setLoading] = useState<boolean>(
    code !== null && !_allianceCache[code ?? '']
  );
  const [error, setError] = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0);

  useEffect(() => {
    const cb = () => setTrigger(t => t + 1);
    _refreshCallbacks.add(cb);
    return () => { _refreshCallbacks.delete(cb); };
  }, []);

  useEffect(() => {
    if (!code) { setData(null); setLoading(false); return; }

    if (_allianceCache[code]) {
      setData(_allianceCache[code]);
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      try {
        setLoading(true);
        let json: AllianceSummary;
        if (USE_API) {
          const res = await fetch(`${API_BASE_URL}/alliance/${code}/`);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          json = await res.json();
        } else {
          const res = await fetch(`${JSON_BASE_PATH}/alliance_${code.toLowerCase()}.json?v=${Date.now()}`);
          if (res.ok) {
            json = await res.json();
          } else {
            json = await _buildAllianceSummaryFromStatic(code);
          }
        }
        _allianceCache[code] = json;
        setData(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch alliance data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [code, trigger]);

  return { data, loading, error };
}

export function usePartyDetail(code: string | null) {
  const [data, setData] = useState<PartyDetailFull | null>(
    code ? (_partyDetailCache[code] ?? null) : null
  );
  const [loading, setLoading] = useState<boolean>(
    code !== null && !_partyDetailCache[code ?? '']
  );
  const [error, setError] = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0);

  useEffect(() => {
    const cb = () => setTrigger(t => t + 1);
    _refreshCallbacks.add(cb);
    return () => { _refreshCallbacks.delete(cb); };
  }, []);

  useEffect(() => {
    if (!code) { setData(null); setLoading(false); return; }

    if (_partyDetailCache[code]) {
      setData(_partyDetailCache[code]);
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      try {
        setLoading(true);
        let json: PartyDetailFull;
        if (USE_API) {
          const res = await fetch(`${API_BASE_URL}/party/${code}/`);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          json = await res.json();
        } else {
          const res = await fetch(`${JSON_BASE_PATH}/party_${code.toLowerCase()}.json?v=${Date.now()}`);
          if (res.ok) {
            json = await res.json();
          } else {
            json = await _buildPartyDetailFromStatic(code);
          }
        }
        _partyDetailCache[code] = json;
        setData(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch party data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [code, trigger]);

  return { data, loading, error };
}


