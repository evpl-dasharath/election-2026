import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useStateSummary, clearElectionDataCache } from '../hooks/useElectionData';

const AC: Record<string, string> = {
  LDF: '#D42B2B', UDF: '#1A8FE3', NDA: '#F7921C', OTH: '#9CA3AF',
};

const STALE_MS = 30_000;

export default function GlobalHeader() {
  const navigate  = useNavigate();
  const location  = useLocation();
  const { data: summary } = useStateSummary();

  const [time, setTime]             = useState(new Date());
  const [isStale, setIsStale]       = useState(false);
  const [isRefreshing, setIsRefresh] = useState(false);
  const lastRef = useRef(Date.now());

  useEffect(() => {
    const t = setInterval(() => {
      setTime(new Date());
      setIsStale(Date.now() - lastRef.current > STALE_MS);
    }, 1000);
    return () => clearInterval(t);
  }, []);

  const handleRefresh = useCallback(() => {
    setIsRefresh(true);
    clearElectionDataCache();
    lastRef.current = Date.now();
    setIsStale(false);
    setTimeout(() => setIsRefresh(false), 800);
  }, []);

  // Alliance tallies
  const ldfWon     = summary?.alliance_summary.LDF.won     || 0;
  const ldfLeading = summary?.alliance_summary.LDF.leading || 0;
  const udfWon     = summary?.alliance_summary.UDF.won     || 0;
  const udfLeading = summary?.alliance_summary.UDF.leading || 0;
  const ndaWon     = summary?.alliance_summary.NDA.won     || 0;
  const ndaLeading = summary?.alliance_summary.NDA.leading || 0;
  const othWon     = summary?.alliance_summary.OTH?.won     || 0;
  const othLeading = summary?.alliance_summary.OTH?.leading || 0;

  // Totals
  const declared = summary?.results_declared     || 0;
  const counting = summary?.counting_in_progress || 0;
  const pending  = 140 - declared - counting;
  const pct      = Math.round(((declared + counting) / 140) * 100);

  const pills = [
    { id: 'LDF', won: ldfWon, lead: ldfLeading },
    { id: 'UDF', won: udfWon, lead: udfLeading },
    { id: 'NDA', won: ndaWon, lead: ndaLeading },
    { id: 'OTH', won: othWon, lead: othLeading },
  ] as const;

  return (
    <header className="bg-ink text-white shrink-0 sticky top-0 z-50 border-b border-white/10">
      {/* ── Row 1: Logo | Pills | Nav + Time ──────────────── */}
      <div className="px-6 h-12 flex items-center justify-between gap-4">

        {/* Left: logo + live pill */}
        <div className="flex items-center gap-2.5 w-[200px] shrink-0">
          <div className="font-serif text-[17px] tracking-tight whitespace-nowrap">
            Kerala <span className="text-gold">Elections</span> 2026
          </div>
          <button
            onClick={handleRefresh}
            title={isStale ? 'Stale — click to refresh' : 'Live'}
            className={`flex items-center gap-1 text-[9px] font-bold tracking-wider px-2 py-0.5 rounded-full uppercase border transition-all duration-500 cursor-pointer select-none ${
              isRefreshing ? 'bg-blue-500/15 border-blue-500/30 text-blue-400'
              : isStale    ? 'bg-amber-500/20 border-amber-500/40 text-amber-400'
                           : 'bg-green-500/15 border-green-500/30 text-green-400'
            }`}
          >
            {isRefreshing
              ? <span className="inline-block animate-spin text-[11px] leading-none">↻</span>
              : isStale
                ? <><span className="text-[11px] leading-none">↻</span><span>Refresh</span></>
                : <><div className="pulse" /><span>Live</span></>
            }
          </button>
        </div>

        {/* Center: 4 alliance pills */}
        <div className="flex items-center gap-2 flex-1 justify-center">
          {pills.map(({ id, won, lead }) => {
            const color = AC[id];
            const total = won + lead;
            return (
              <div
                key={id}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  background: `${color}18`,
                  border: `1px solid ${color}50`,
                  borderRadius: 8, padding: '4px 10px',
                }}
              >
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: color, flexShrink: 0 }} />
                <span style={{ fontSize: 11, fontWeight: 700, color, letterSpacing: 0.5 }}>{id}</span>
                <span style={{ fontSize: 17, fontWeight: 800, color: 'white', lineHeight: 1, fontFamily: "'DM Serif Display',serif" }}>{total}</span>
                {won > 0 && (
                  <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.45)', whiteSpace: 'nowrap' }}>
                    ({won} Won)
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Right: nav + time */}
        <div className="flex items-center justify-end gap-5 w-[200px] shrink-0">
          <div className="flex gap-4">
            <span
              className={`text-[11px] font-medium cursor-pointer hover:text-white/80 transition-colors ${location.pathname === '/' ? 'text-white' : 'text-white/45'}`}
              onClick={() => navigate('/')}
            >State</span>
            <span
              className={`text-[11px] font-medium cursor-pointer hover:text-white/80 transition-colors ${location.pathname.startsWith('/constituency') ? 'text-white' : 'text-white/45'}`}
              onClick={() => { if (!location.pathname.startsWith('/constituency')) navigate('/constituency/1'); }}
            >Constituency</span>
          </div>
          <div className="font-mono text-[10px] text-white/35">
            {time.toLocaleString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' })} IST
          </div>
        </div>
      </div>

      {/* ── Row 2: Seat totals + progress ─────────────────── */}
      <div className="px-6 h-7 flex items-center justify-center gap-6 border-t border-white/8 bg-white/3">
        {[
          { label: 'Declared', value: declared, color: 'text-white/70' },
          { label: 'Counting', value: counting, color: 'text-amber-400/80' },
          { label: 'Pending',  value: pending,  color: 'text-white/30' },
        ].map(({ label, value, color }) => (
          <span key={label} className="flex items-baseline gap-1.5">
            <span className={`font-mono font-bold text-[13px] ${color}`}>{value}</span>
            <span className="text-[9px] text-white/30 uppercase tracking-wider">{label}</span>
          </span>
        ))}
        {pct > 0 && (
          <>
            <span className="text-white/15 text-[10px]">|</span>
            <div className="flex items-center gap-2">
              <div className="w-24 h-1 bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-white/40 rounded-full transition-all duration-700"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="font-mono text-[10px] text-white/40">{pct}%</span>
            </div>
          </>
        )}
      </div>
    </header>
  );
}
