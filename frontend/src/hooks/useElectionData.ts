import { useState, useEffect } from 'react';
import type {
  StateSummary,
  ConstituencyListItem,
  ConstituencyDetail,
  HistoricalComparison,
  Party,
} from '../types';

// Environment-based data source
const USE_API = import.meta.env.DEV;
const API_BASE_URL = 'http://localhost:8001/api';
const JSON_BASE_PATH = '/data';

// ─── Module-level cache ───────────────────────────────────────────────────────
let _summaryCache: StateSummary | null = null;
let _constituenciesCache: ConstituencyListItem[] | null = null;
let _partiesCache: Party[] | null = null;
let _allHistoricalCache: unknown[] | null = null;
const _constituencyDetailCache: Record<number, ConstituencyDetail> = {};
const _historicalCache: Record<number, HistoricalComparison> = {};

// ─── Refresh callbacks ────────────────────────────────────────────────────────
// When clearElectionDataCache() is called, all mounted hooks are notified
// and automatically re-fetch fresh data.
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
 * Safe to call speculatively (no-ops if already cached).
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
    if (_summaryCache !== null) { setData(_summaryCache); setLoading(false); return; }
    const fetchData = async () => {
      try {
        setLoading(true);
        let json: StateSummary;
        if (USE_API) {
          const res = await fetch(`${API_BASE_URL}/summary/`);
          json = await res.json();
        } else {
          const res = await fetch(`${JSON_BASE_PATH}/meta.json`);
          json = await res.json();
        }
        _summaryCache = json;
        setData(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch summary');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
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
    if (_constituenciesCache !== null) { setData(_constituenciesCache); setLoading(false); return; }
    const fetchData = async () => {
      try {
        setLoading(true);
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
        setData(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch constituencies');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
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
    if (_constituencyDetailCache[constituencyId]) {
      setData(_constituencyDetailCache[constituencyId]);
      setLoading(false);
      return;
    }
    const fetchData = async () => {
      try {
        setLoading(true);
        let json: ConstituencyDetail;
        if (USE_API) {
          const res = await fetch(`${API_BASE_URL}/constituencies/${constituencyId}/`);
          json = await res.json();
        } else {
          const listRes = await fetch(`${JSON_BASE_PATH}/constituencies.json`);
          const list: ConstituencyListItem[] = await listRes.json();
          const constituency = list.find(c => c.id === constituencyId);
          if (!constituency) throw new Error('Constituency not found');
          const res = await fetch(
            `${JSON_BASE_PATH}/results/${constituency.number.toString().padStart(3, '0')}.json`
          );
          json = await res.json();
        }
        _constituencyDetailCache[constituencyId] = json;
        setData(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch constituency');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
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
// Returns all 140 constituencies with la_2011 / la_2016 / la_2021 winner summaries.
// Backed by GET /api/history/all/ (Option A — single bulk request, cached).
export function useAllHistorical() {
  const [data, setData] = useState<unknown[]>(_allHistoricalCache ?? []);
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
        let json: unknown[];
        if (USE_API) {
          const res = await fetch(`${API_BASE_URL}/history/all/`);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          json = await res.json();
        } else {
          // Static fallback: expects /data/history_all.json
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
