import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useStateSummary, clearElectionDataCache, useLastRtdbUpdate, useDataSource } from '../hooks/useElectionData';
import { ALLIANCE_COLORS, PURE_IND_COLOR } from '../utils/colorUtils';

// ─── Election Day Config ──────────────────────────────────────────────────────
// Election day: May 4, 2026 at 8:00 AM IST
const ELECTION_DAY = new Date('2026-05-04T02:30:00Z'); // 8:00 AM IST = 2:30 AM UTC
const STALE_WARN_MS = 10 * 60 * 1000; // 10 minutes
const STALE_ERROR_MS = 20 * 60 * 1000; // 20 minutes

function isElectionDay(): boolean {
  return Date.now() >= ELECTION_DAY.getTime();
}

export default function GlobalHeader() {
  const navigate = useNavigate();
  const location = useLocation();
  const { data: summary } = useStateSummary();
  const lastRtdbUpdate = useLastRtdbUpdate();
  const { source: dataSource, cachedAt } = useDataSource();

  const [time, setTime] = useState(new Date());
  const [staleness, setStaleness] = useState<'ok' | 'warn' | 'error'>('ok');
  const [isRefreshing, setIsRefresh] = useState(false);
  const [cacheAge, setCacheAge] = useState<string | null>(null);

  function formatAge(ms: number): string {
    const sec = Math.floor(ms / 1000);
    if (sec < 60) return `${sec}s ago`;
    const min = Math.floor(sec / 60);
    if (min < 60) return `${min} min ago`;
    const hrs = Math.floor(min / 60);
    return `${hrs}h ${min % 60}m ago`;
  }

  useEffect(() => {
    const t = setInterval(() => {
      setTime(new Date());
      if (isElectionDay() && lastRtdbUpdate !== null) {
        const age = Date.now() - lastRtdbUpdate;
        if (age > STALE_ERROR_MS) setStaleness('error');
        else if (age > STALE_WARN_MS) setStaleness('warn');
        else setStaleness('ok');
      } else {
        setStaleness('ok');
      }
      if (cachedAt !== null && dataSource === 'cached-json') {
        setCacheAge(formatAge(Date.now() - cachedAt));
      } else {
        setCacheAge(null);
      }
    }, 1000);
    if (cachedAt !== null && dataSource === 'cached-json') {
      setCacheAge(formatAge(Date.now() - cachedAt));
    } else {
      setCacheAge(null);
    }
    return () => clearInterval(t);
  }, [lastRtdbUpdate, dataSource, cachedAt]);

  const handleRefresh = useCallback(() => {
    setIsRefresh(true);
    clearElectionDataCache();
    setTimeout(() => setIsRefresh(false), 800);
  }, []);

  const ldfWon = summary?.alliance_summary.LDF.won || 0;
  const ldfLeading = summary?.alliance_summary.LDF.leading || 0;
  const ldfShare = summary?.alliance_summary.LDF.vote_share || 0;
  const udfWon = summary?.alliance_summary.UDF.won || 0;
  const udfLeading = summary?.alliance_summary.UDF.leading || 0;
  const udfShare = summary?.alliance_summary.UDF.vote_share || 0;
  const ndaWon = summary?.alliance_summary.NDA.won || 0;
  const ndaLeading = summary?.alliance_summary.NDA.leading || 0;
  const ndaShare = summary?.alliance_summary.NDA.vote_share || 0;
  const othWon = summary?.alliance_summary.OTH?.won || 0;
  const othLeading = summary?.alliance_summary.OTH?.leading || 0;
  const othShare = summary?.alliance_summary.OTH?.vote_share || 0;
  const indWon = summary?.ind_summary?.won || 0;
  const indLeading = summary?.ind_summary?.leading || 0;
  const othOnlyWon = Math.max(0, othWon - indWon);
  const othOnlyLeading = Math.max(0, othLeading - indLeading);

  const declared = summary?.results_declared || 0;
  const pending = 140 - declared - (summary?.counting_in_progress || 0);
  const totalCounted = summary?.total_votes_counted || 0;
  const totalPolled = summary?.total_votes_polled || 0;
  const votePct = totalPolled > 0 ? Math.round((totalCounted / totalPolled) * 100) : 0;
  const declaredPct = Math.round((declared / 140) * 100);
  const counting = summary?.counting_in_progress || 0;

  const mainPills = [
    { id: 'LDF', won: ldfWon, lead: ldfLeading, share: ldfShare, color: ALLIANCE_COLORS.LDF },
    { id: 'UDF', won: udfWon, lead: udfLeading, share: udfShare, color: ALLIANCE_COLORS.UDF },
    { id: 'NDA', won: ndaWon, lead: ndaLeading, share: ndaShare, color: ALLIANCE_COLORS.NDA },
  ];

  const conditionalPills = [
    ...(othOnlyWon + othOnlyLeading > 0
      ? [{ id: 'OTH', won: othOnlyWon, lead: othOnlyLeading, share: othShare, color: ALLIANCE_COLORS.OTH }]
      : []),
    ...(indWon + indLeading > 0
      ? [{ id: 'IND', won: indWon, lead: indLeading, share: 0, color: PURE_IND_COLOR }]
      : []),
  ];

  const allPills = [...mainPills, ...conditionalPills];

  const staleBanner = staleness !== 'ok' && isElectionDay() ? (
    <div
      className="text-center text-[11px] font-semibold py-1 px-4"
      style={{
        background: staleness === 'error' ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.15)',
        color: staleness === 'error' ? '#FCA5A5' : '#FCD34D',
        borderBottom: `1px solid ${staleness === 'error' ? 'rgba(239,68,68,0.2)' : 'rgba(245,158,11,0.2)'}`,
      }}
    >
      {staleness === 'error'
        ? '⚠ No data received for 20+ minutes — check network or backend'
        : '⚠ No data updates for 10 minutes — feed may be delayed'}
    </div>
  ) : null;

  const cachedBanner = dataSource === 'cached-json' ? (
    <div
      className="text-center text-[11px] font-semibold py-1 px-4 flex items-center justify-center gap-2"
      style={{
        background: 'rgba(251,146,60,0.12)',
        color: '#FD9A5B',
        borderBottom: '1px solid rgba(251,146,60,0.22)',
      }}
    >
      <span
        style={{
          display: 'inline-block',
          width: 7, height: 7,
          borderRadius: '50%',
          background: '#FB923C',
          animation: 'cachedPulse 2s ease-in-out infinite',
          flexShrink: 0,
        }}
      />
      <span>
        📦 Showing cached data
        {cacheAge ? ` · snapshot loaded ${cacheAge}` : ''}
        {' · '}
        <span
          onClick={handleRefresh}
          style={{ textDecoration: 'underline', cursor: 'pointer', opacity: 0.85 }}
          title="Retry Firebase connection"
        >
          Retry live
        </span>
      </span>
    </div>
  ) : null;

  const StatusBadge = () => {
    if (!isElectionDay()) {
      return (
        <div
          className="flex items-center gap-1 text-[9px] font-bold tracking-wider px-2 py-0.5 rounded-full uppercase border select-none"
          style={{ background: 'rgba(139,92,246,0.15)', border: '1px solid rgba(139,92,246,0.35)', color: '#A78BFA' }}
          title="Pre-election: running in development mode. Goes live on May 4, 2026 at 8:00 AM IST."
        >
          <span className="text-[9px]">🛠</span> IN DEV
        </div>
      );
    }
    if (isRefreshing) {
      return (
        <button
          onClick={handleRefresh}
          className="flex items-center gap-1 text-[9px] font-bold tracking-wider px-2 py-0.5 rounded-full uppercase border transition-all duration-500 cursor-pointer select-none bg-blue-500/15 border-blue-500/30 text-blue-400"
        >
          <span className="inline-block animate-spin text-[11px] leading-none">↻</span>
        </button>
      );
    }
    if (staleness === 'error') {
      return (
        <button
          onClick={handleRefresh}
          title="Data stale 20+ min — click to refresh"
          className="flex items-center gap-1 text-[9px] font-bold tracking-wider px-2 py-0.5 rounded-full uppercase border transition-all duration-500 cursor-pointer select-none bg-red-500/15 border-red-500/30 text-red-400"
        >
          <span className="text-[11px] leading-none">⚠</span><span>Stale</span>
        </button>
      );
    }
    if (staleness === 'warn') {
      return (
        <button
          onClick={handleRefresh}
          title="No update for 10 min — click to refresh"
          className="flex items-center gap-1 text-[9px] font-bold tracking-wider px-2 py-0.5 rounded-full uppercase border transition-all duration-500 cursor-pointer select-none bg-amber-500/20 border-amber-500/40 text-amber-400"
        >
          <span className="text-[11px] leading-none">↻</span><span>Delayed</span>
        </button>
      );
    }
    return (
      <button
        onClick={handleRefresh}
        title="Live — data streaming from Firebase"
        className="flex items-center gap-1 text-[9px] font-bold tracking-wider px-2 py-0.5 rounded-full uppercase border transition-all duration-500 cursor-pointer select-none bg-green-500/15 border-green-500/30 text-green-400"
      >
        <div className="pulse" /><span>Live</span>
      </button>
    );
  };

  // ─── Nav entries ─────────────────────────────────────────────────────────────
  const navItems = [
    {
      label: 'State',
      active: location.pathname === '/',
      onClick: () => navigate('/'),
    },
    {
      label: 'Constituency',
      active: location.pathname.startsWith('/constituency'),
      onClick: () => { if (!location.pathname.startsWith('/constituency')) navigate('/constituency/1'); },
    },
    {
      label: 'Alliances',
      active: location.pathname.startsWith('/alliance'),
      onClick: () => navigate('/alliance/ldf'),
    },
    {
      label: 'Parties',
      active: location.pathname.startsWith('/party'),
      onClick: () => navigate('/party'),
    },
    {
      label: 'History',
      active: location.pathname === '/history',
      onClick: () => navigate('/history'),
    },
  ];

  return (
    <header className="bg-ink text-white shrink-0 sticky top-0 z-50 border-b border-white/10">
      <style>{`
        @keyframes cachedPulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(0.8); }
        }
      `}</style>

      {staleBanner}
      {cachedBanner}

      {/* ── Row 1: Logo | Pills | Nav + Time ──────────────── */}
      <div className="px-3 md:px-6 py-2 md:py-0 min-h-[3rem] md:h-12 flex flex-wrap md:flex-nowrap items-center justify-between gap-y-2 gap-x-4">

        {/* Left: logo + status badge */}
        <div className="flex items-center gap-2 md:gap-2.5 shrink-0 md:w-[200px]">
          <div className="font-serif text-[15px] md:text-[17px] tracking-tight whitespace-nowrap">
            Kerala <span className="text-gold">Elections</span> 2026
          </div>
          <StatusBadge />
        </div>

        {/* Center: alliance pills */}
        <div className="flex items-center gap-2 w-full md:w-auto md:flex-1 justify-start md:justify-center overflow-x-auto custom-scrollbar order-3 md:order-2 pb-1 md:pb-0">
          {allPills.map(({ id, won, lead, share, color }) => {
            const total = won + lead;
            return (
              <div
                key={id}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 8,
                  background: `${color}18`,
                  border: `1px solid ${color}50`,
                  borderRadius: 10, padding: '6px 14px',
                }}
              >
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: color, flexShrink: 0 }} />
                <span style={{ fontSize: 13, fontWeight: 700, color, letterSpacing: 0.5 }}>{id}</span>
                <span style={{ fontSize: 22, fontWeight: 800, color: 'white', lineHeight: 1 }}>{total}</span>
                {won > 0 && (
                  <span style={{ fontSize: 22, fontWeight: 800, color: 'rgba(255,255,255,0.45)', lineHeight: 1, whiteSpace: 'nowrap' }}>
                    W {won}
                  </span>
                )}
                {share !== undefined && share > 0 && (
                  <span style={{ fontSize: 22, fontWeight: 800, color: 'rgba(255,255,255,0.6)', lineHeight: 1, whiteSpace: 'nowrap', borderLeft: `1px solid ${color}40`, paddingLeft: 8, marginLeft: 2 }}>
                    {share.toFixed(1)}%
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Right: nav + time */}
        <div className="flex items-center justify-end gap-3 md:gap-5 shrink-0 md:w-[200px] order-2 md:order-3">
          {/* Nav — scrollable on mobile so all 5 entries fit */}
          <div className="flex gap-3 md:gap-4 overflow-x-auto custom-scrollbar">
            {navItems.map(({ label, active, onClick }) => (
              <span
                key={label}
                onClick={onClick}
                className={`text-[11px] font-medium cursor-pointer hover:text-white/80 transition-colors whitespace-nowrap ${active ? 'text-white' : 'text-white/45'}`}
              >
                {label}
              </span>
            ))}
          </div>
          <div className="font-mono text-[10px] text-white/35 shrink-0">
            {time.toLocaleString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' })} IST
          </div>
        </div>
      </div>

      {/* ── Row 2: Seat totals + progress ─────────────────── */}
      <div className="px-3 md:px-6 py-1 md:py-0 min-h-[1.75rem] md:h-7 flex flex-wrap md:flex-nowrap items-center justify-center gap-x-4 md:gap-x-6 gap-y-1 border-t border-white/8 bg-white/3">
        {[
          { label: 'Declared', value: declared, color: 'text-white/70' },
          { label: 'Counting', value: counting, color: 'text-amber-400/80' },
          { label: 'Pending', value: pending, color: 'text-white/30' },
        ].map(({ label, value, color }) => (
          <span key={label} className="flex items-baseline gap-1.5">
            <span className={`font-mono font-bold text-[13px] ${color}`}>{value}</span>
            <span className="text-[9px] text-white/30 uppercase tracking-wider">{label}</span>
          </span>
        ))}
        {totalPolled > 0 && (
          <>
            <span className="text-white/15 text-[10px]">|</span>
            <div className="flex items-center gap-2">
              <div className="w-28 h-1 bg-white/8 rounded-full overflow-hidden">
                <div
                  className="h-full bg-green-400/60 rounded-full transition-all duration-700"
                  style={{ width: `${votePct}%` }}
                  title={`${totalCounted.toLocaleString('en-IN')} / ${totalPolled.toLocaleString('en-IN')} votes`}
                />
              </div>
              <span className="font-mono text-[10px] text-white/40">{votePct}% votes</span>
            </div>
          </>
        )}
        {totalPolled === 0 && declared > 0 && (
          <>
            <span className="text-white/15 text-[10px]">|</span>
            <div className="flex items-center gap-2">
              <div className="w-28 h-1 bg-white/8 rounded-full overflow-hidden">
                <div
                  className="h-full bg-white/40 rounded-full transition-all duration-700"
                  style={{ width: `${declaredPct}%` }}
                />
              </div>
              <span className="font-mono text-[10px] text-white/40">{declaredPct}% declared</span>
            </div>
          </>
        )}
      </div>
    </header>
  );
}
