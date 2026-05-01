import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useStateSummary, clearElectionDataCache } from '../hooks/useElectionData';

const ALLIANCE_COLORS: Record<string, string> = {
  LDF: '#D42B2B', UDF: '#1A8FE3', NDA: '#F7921C', OTH: '#9CA3AF',
};

const STALE_MS = 30_000; // 30 seconds

export default function GlobalHeader() {
  const navigate = useNavigate();
  const location = useLocation();
  const { data: summary } = useStateSummary();

  const [time, setTime] = useState(new Date());
  const [isStale, setIsStale] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const lastRefreshedRef = useRef(Date.now());

  // Single interval: updates clock + staleness check every second
  useEffect(() => {
    const t = setInterval(() => {
      setTime(new Date());
      setIsStale(Date.now() - lastRefreshedRef.current > STALE_MS);
    }, 1000);
    return () => clearInterval(t);
  }, []);

  const handleRefresh = useCallback(() => {
    setIsRefreshing(true);
    clearElectionDataCache();
    lastRefreshedRef.current = Date.now();
    setIsStale(false);
    setTimeout(() => setIsRefreshing(false), 800);
  }, []);

  const ldfSeats = summary ? summary.alliance_summary.LDF.won + summary.alliance_summary.LDF.leading : 0;
  const udfSeats = summary ? summary.alliance_summary.UDF.won + summary.alliance_summary.UDF.leading : 0;
  const ndaSeats = summary ? summary.alliance_summary.NDA.won + summary.alliance_summary.NDA.leading : 0;

  return (
    <header className="bg-ink text-white px-8 h-14 flex items-center justify-between shrink-0 sticky top-0 z-50">
      <div className="flex items-center gap-3 w-1/4">
        <div className="font-serif text-xl tracking-tight">Kerala <span className="text-gold">Elections</span> 2026</div>

        {/* Live / Stale / Refreshing pill */}
        <button
          onClick={handleRefresh}
          title={isStale ? 'Data may be stale — click to refresh' : 'Data is live'}
          className={`flex items-center gap-1.5 text-[11px] font-semibold tracking-wider px-2.5 py-0.5 rounded-full uppercase border transition-all duration-500 cursor-pointer select-none ${
            isRefreshing
              ? 'bg-blue-500/15 border-blue-500/30 text-blue-400'
              : isStale
              ? 'bg-amber-500/20 border-amber-500/40 text-amber-400 hover:bg-amber-500/30 hover:border-amber-400/60'
              : 'bg-green-500/15 border-green-500/30 text-green-400 hover:bg-green-500/25'
          }`}
        >
          {isRefreshing ? (
            <span className="inline-block animate-spin text-[13px] leading-none">↻</span>
          ) : isStale ? (
            <>
              <span className="text-[13px] leading-none">↻</span>
              <span>Refresh</span>
            </>
          ) : (
            <>
              <div className="pulse" />
              <span>Live</span>
            </>
          )}
        </button>
      </div>

      {/* Key Results Tally */}
      <div className="flex items-center justify-center gap-6 flex-1">
        {[['LDF', ldfSeats], ['UDF', udfSeats], ['NDA', ndaSeats]].map(([name, seats]) => (
          <div key={name as string} className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: ALLIANCE_COLORS[name as string] }} />
            <span className="font-serif text-[17px]" style={{ color: ALLIANCE_COLORS[name as string] }}>{seats}</span>
            <span className="text-[11px] tracking-wide text-white/45">{name}</span>
          </div>
        ))}
        <span className="text-[11px] text-white/20 mx-2">|</span>
        <span className="text-[11px] text-white/30">{ldfSeats + udfSeats + ndaSeats} / 140 declared</span>
      </div>

      {/* Navigation & Time */}
      <div className="flex items-center justify-end gap-6 w-1/4">
        <div className="flex gap-4">
          <span
            className={`text-[12px] font-medium cursor-pointer hover:text-white/80 transition-colors ${location.pathname === '/' ? 'text-white' : 'text-white/50'}`}
            onClick={() => navigate('/')}
          >
            State Results
          </span>
          <span
            className={`text-[12px] font-medium cursor-pointer hover:text-white/80 transition-colors ${location.pathname.startsWith('/constituency') ? 'text-white' : 'text-white/50'}`}
            onClick={() => {
              if (!location.pathname.startsWith('/constituency')) navigate('/constituency/1');
            }}
          >
            Constituency
          </span>
        </div>
        <div className="font-mono text-xs text-white/40">
          {time.toLocaleString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' })} IST
        </div>
      </div>
    </header>
  );
}
