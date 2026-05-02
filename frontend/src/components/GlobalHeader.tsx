import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useStateSummary, clearElectionDataCache } from '../hooks/useElectionData';
import { ALLIANCE_COLORS, PURE_IND_COLOR } from '../utils/colorUtils';

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
  const indWon     = summary?.ind_summary?.won     || 0;
  const indLeading = summary?.ind_summary?.leading || 0;

  // OTH = total OTH alliance minus pure IND (IND is a subset of OTH alliance)
  const othOnlyWon     = Math.max(0, othWon     - indWon);
  const othOnlyLeading = Math.max(0, othLeading - indLeading);

  // Totals
  const declared = summary?.results_declared     || 0;
  const counting = summary?.counting_in_progress || 0;
  const pending  = 140 - declared - counting;
  const pct      = Math.round(((declared + counting) / 140) * 100);

  // Main alliance pills — always shown
  const mainPills = [
    { id: 'LDF', won: ldfWon, lead: ldfLeading, color: ALLIANCE_COLORS.LDF },
    { id: 'UDF', won: udfWon, lead: udfLeading, color: ALLIANCE_COLORS.UDF },
    { id: 'NDA', won: ndaWon, lead: ndaLeading, color: ALLIANCE_COLORS.NDA },
  ];

  // Conditional pills — only shown when they have at least one lead or win
  const conditionalPills = [
    ...(othOnlyWon + othOnlyLeading > 0
      ? [{ id: 'OTH', won: othOnlyWon, lead: othOnlyLeading, color: ALLIANCE_COLORS.OTH }]
      : []),
    ...(indWon + indLeading > 0
      ? [{ id: 'IND', won: indWon, lead: indLeading, color: PURE_IND_COLOR }]
      : []),
  ];

  const allPills = [...mainPills, ...conditionalPills];

  return (
    <header className="bg-ink text-white shrink-0 sticky top-0 z-50 border-b border-white/10">
      {/* ── Row 1: Logo | Pills | Nav + Time ──────────────── */}
      <div className="px-3 md:px-6 py-2 md:py-0 min-h-[3rem] md:h-12 flex flex-wrap md:flex-nowrap items-center justify-between gap-y-2 gap-x-4">

        {/* Left: logo + live pill */}
        <div className="flex items-center gap-2 md:gap-2.5 shrink-0 md:w-[200px]">
          <div className="font-serif text-[15px] md:text-[17px] tracking-tight whitespace-nowrap">
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

        {/* Center: alliance pills */}
        <div className="flex items-center gap-2 w-full md:w-auto md:flex-1 justify-start md:justify-center overflow-x-auto custom-scrollbar order-3 md:order-2 pb-1 md:pb-0">
          {allPills.map(({ id, won, lead, color }) => {
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
        <div className="flex items-center justify-end gap-3 md:gap-5 shrink-0 md:w-[200px] order-2 md:order-3">
          <div className="flex gap-3 md:gap-4">
            <span
              className={`text-[11px] font-medium cursor-pointer hover:text-white/80 transition-colors ${location.pathname === '/' ? 'text-white' : 'text-white/45'}`}
              onClick={() => navigate('/')}
            >State</span>
            <span
              className={`text-[11px] font-medium cursor-pointer hover:text-white/80 transition-colors ${location.pathname.startsWith('/constituency') ? 'text-white' : 'text-white/45'}`}
              onClick={() => { if (!location.pathname.startsWith('/constituency')) navigate('/constituency/1'); }}
            >Constituency</span>
            <span
              className={`text-[11px] font-medium cursor-pointer hover:text-white/80 transition-colors ${location.pathname === '/history' ? 'text-white' : 'text-white/45'}`}
              onClick={() => navigate('/history')}
            >History</span>
          </div>
          <div className="font-mono text-[10px] text-white/35">
            {time.toLocaleString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' })} IST
          </div>
        </div>
      </div>

      {/* ── Row 2: Seat totals + progress ─────────────────── */}
      <div className="px-3 md:px-6 py-1 md:py-0 min-h-[1.75rem] md:h-7 flex flex-wrap md:flex-nowrap items-center justify-center gap-x-4 md:gap-x-6 gap-y-1 border-t border-white/8 bg-white/3">
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
