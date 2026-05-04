import { useState, useEffect } from 'react';
import type {
  StateSummary,
  ConstituencyListItem,
  ConstituencyDetail,
  HistoricalComparison,
  Party,
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
  const connRef = ref(db, '.info/connected');
  onValue(connRef, (snap) => {
    _notifyConnected(snap.val() === true);
  });
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
const USE_API = import.meta.env.DEV;
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
  _refreshCallbacks.forEach(cb => cb());
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
    let unsubscribe = () => {};

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
    let unsubscribe = () => {};

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
                   // votes_polled & total_electors are STATIC (polling-day data).
                   // c already has them from constituencies.json — do NOT override from RTDB.
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
                   // Use votes_polled (polling-day total) as denominator for vote share.
                   // Fall back to currently counted votes only if votes_polled is unavailable.
                   const voteShareDenominator = (newC.votes_polled && newC.votes_polled > 0)
                     ? newC.votes_polled
                     : 0;

                   // Only show a leader/runner-up once at least 1 vote has been counted
                   if (totalVotesCounted > 0 && sorted.length > 0) {
                     const pInfo = getPartyInfo(sorted[0].party);
                     newC.leader = {
                       name: sorted[0].name,
                       party: sorted[0].party,
                       votes: sorted[0].votes,
                       percentage: (sorted[0].votes / voteShareDenominator) * 100,
                       alliance: pInfo.alliance,
                       party_color: pInfo.color
                     };
                   } else {
                     newC.leader = null;
                   }
                   if (totalVotesCounted > 0 && sorted.length > 1 && sorted[1].votes > 0) {
                     const pInfo = getPartyInfo(sorted[1].party);
                     newC.runner_up = {
                       name: sorted[1].name,
                       party: sorted[1].party,
                       votes: sorted[1].votes,
                       percentage: (sorted[1].votes / voteShareDenominator) * 100,
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
    
    let unsubscribe = () => {};

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
             // Use votes_polled (polling-day total) as denominator for vote share.
             // Priority: staticListItem.votes_polled > baseJson.live_result.votes_polled > RTDB > counted votes
             const voteShareDenominator = (
               (staticListItem?.votes_polled && staticListItem.votes_polled > 0) ? staticListItem.votes_polled
               : (baseJson.live_result?.votes_polled && baseJson.live_result.votes_polled > 0) ? baseJson.live_result.votes_polled
               : (liveAc.votes_polled && liveAc.votes_polled > 0) ? liveAc.votes_polled
               : 0
             );

             const mergedCands = sortedLiveCands.map((c: any, index: number) => {
                const pInfo = getPartyInfo(c.party);
                return {
                  name: c.name,
                  party: c.party,
                  alliance: pInfo.alliance,
                  votes: c.votes,
                  percentage: voteShareDenominator > 0 ? (c.votes / voteShareDenominator) * 100 : 0,
                  is_winner: liveAc.status === 'RESULT_DECLARED' && index === 0 && c.votes > 0,
                  is_leading: liveAc.status === 'IN_PROGRESS' && index === 0 && c.votes > 0,
                  party_color: pInfo.color
                };
             });

               const mergedLiveResult = {
                 status: liveAc.status,
                 // total_electors & votes_polled are STATIC (polling-day data).
                 // Priority: staticListItem (from constituencies.json) > baseJson.live_result > RTDB
                 // staticListItem is always populated in prod JSON path (from the list fetch above).
                 total_electors: staticListItem?.total_electors
                   || baseJson.live_result?.total_electors
                   || liveAc.total_electors
                   || 0,
                 votes_polled: staticListItem?.votes_polled
                   || baseJson.live_result?.votes_polled
                   || liveAc.votes_polled
                   || 0,
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
