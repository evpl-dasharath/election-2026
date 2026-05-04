import { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStateSummary, useConstituencies, useParties, useRtdbConnected } from '../hooks/useElectionData';
import { usePinnedSeats } from '../hooks/usePinnedSeats';
import type { Alliance, Region, ConstituencyListItem } from '../types';
import GlobalHeader from '../components/GlobalHeader';
import { partyAbbr, partyDisplay } from '../utils/partyAbbr';
import {
  ALLIANCE_COLORS, PURE_IND_COLOR,
  resolvePartyColor, resolveCardBg,
  isRawIND, isSupportedIND,
} from '../utils/colorUtils';

const REGION_META: { key: Region; label: string; subtitle: string }[] = [
  { key: 'north', label: 'North', subtitle: 'Malabar' },
  { key: 'central_north', label: 'Central North', subtitle: '' },
  { key: 'south_central', label: 'South Central', subtitle: '' },
  { key: 'south', label: 'South', subtitle: 'Travancore' },
];

const DISTRICT_ORDER = [
  'Kasaragod','Kannur','Wayanad','Kozhikode',
  'Malappuram','Palakkad','Thrissur',
  'Ernakulam','Idukki','Kottayam','Alappuzha',
  'Pathanamthitta','Kollam','Thiruvananthapuram',
];

const DISTRICT_REGION: Record<string, Region> = {
  Kasaragod:'north', Kannur:'north', Wayanad:'north', Kozhikode:'north',
  Malappuram:'central_north', Palakkad:'central_north', Thrissur:'central_north',
  Ernakulam:'south_central', Idukki:'south_central', Kottayam:'south_central', Alappuzha:'south_central',
  Pathanamthitta:'south', Kollam:'south', Thiruvananthapuram:'south',
};

const MAJORITY = 71;


// ── Region tally helper ────────────────────────────────────
function regionTally(list: ConstituencyListItem[], region: Region) {
  const inRegion = list.filter(c => c.region === region);
  const tally = { LDF: 0, UDF: 0, NDA: 0, OTH: 0, total: inRegion.length };
  inRegion.forEach(c => {
    const live = c.status === 'IN_PROGRESS' || c.status === 'RESULT_DECLARED';
    if (live && c.leader) {
      const a = c.leader.alliance as Alliance;
      tally[a] = (tally[a] || 0) + 1;
    }
  });
  return tally;
}

// ── Main Component ─────────────────────────────────────────
export default function HomePage() {
  const navigate = useNavigate();
  const { data: summary } = useStateSummary();
  const { data: constituencies, loading: loadingConst } = useConstituencies();
  const { data: parties } = useParties();
  const rtdbConnected = useRtdbConnected();
  const [offlineDismissed, setOfflineDismissed] = useState<boolean>(false);

  // Auto-clear dismiss flag when we reconnect
  useEffect(() => { if (rtdbConnected) setOfflineDismissed(false); }, [rtdbConnected]);

  const showOfflineBanner = !rtdbConnected && !offlineDismissed;

  const [activeRegion, setActiveRegion] = useState<Region | null>(null);
  const [activeDistrict, setActiveDistrict] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeResultFilter, setActiveResultFilter] = useState<string | null>(null);
  // 'inplay' is the default mode during counting; 'results' after all are declared
  const [filterMode, setFilterMode] = useState<'inplay' | 'results'>('inplay');

  const { pinned, toggle, isPinned } = usePinnedSeats();
  const pinnedConstituencies = useMemo(
    () => pinned.map(id => constituencies.find(c => c.id === Number(id))).filter(Boolean) as ConstituencyListItem[],
    [pinned, constituencies]
  );

  const STRONG_MARGIN = 10_000; // votes — "strong lead"
  const LEAN_MARGIN   = 3_000;  // votes — "lean lead" (below this = bare)

  // ── Derived data ────
  const totalSeats = summary?.total_constituencies || 140;
  const declared = summary?.results_declared || 0;

  const indWon     = summary?.ind_summary?.won     || 0;
  const indLeading = summary?.ind_summary?.leading || 0;
  const indSeats   = indWon + indLeading;

  const ldfSeats = summary ? summary.alliance_summary.LDF.won + summary.alliance_summary.LDF.leading : 0;
  const udfSeats = summary ? summary.alliance_summary.UDF.won + summary.alliance_summary.UDF.leading : 0;
  const ndaSeats = summary ? summary.alliance_summary.NDA.won + summary.alliance_summary.NDA.leading : 0;
  const othTotal = summary ? (summary.alliance_summary.OTH?.won || 0) + (summary.alliance_summary.OTH?.leading || 0) : 0;
  // OTH excluding pure IND (IND is tracked separately)
  const othSeats = Math.max(0, othTotal - indSeats);

  const allianceList = [
    { name: 'LDF', seats: ldfSeats },
    { name: 'UDF', seats: udfSeats },
    { name: 'NDA', seats: ndaSeats },
  ];
  const leading = allianceList.reduce((a, b) => a.seats > b.seats ? a : b);
  const hasMajority = leading.seats >= MAJORITY;

  const seatsActive = useMemo(() =>
    constituencies.filter(c => c.status === 'IN_PROGRESS' || c.status === 'RESULT_DECLARED').length
  , [constituencies]);
  const countingPct = totalSeats > 0 ? (seatsActive / totalSeats) * 100 : 0;
  // Auto-switch to Results tab once every seat is declared
  const allDeclared = declared >= totalSeats && totalSeats > 0;
  useEffect(() => {
    if (allDeclared) setFilterMode('results');
  }, [allDeclared]);
  // Clear the active chip whenever the mode changes
  useEffect(() => { setActiveResultFilter(null); }, [filterMode]);

  const statusLabel = useMemo(() => {
    if (seatsActive === 0) return { text: 'Awaiting results', color: '' };
    const color = leading.name === 'LDF' ? 'text-ldf' : leading.name === 'UDF' ? 'text-udf' : 'text-nda';
    if (hasMajority) {
      if (declared >= totalSeats) return { text: `${leading.name} wins with ${leading.seats} seats`, color };
      if (declared >= 106)        return { text: `${leading.name} wins majority`, color };
      if (declared >= 85)         return { text: `${leading.name} heading for majority`, color };
      if (declared >= 36)         return { text: `${leading.name} on course for majority`, color };
      return                             { text: `${leading.name} — early majority trend`, color };
    }
    // No majority
    if (declared >= totalSeats) return { text: 'Hung Assembly', color: '' };
    if (declared >= 106)        return { text: 'Hung assembly near-certain', color: '' };
    if (declared >= 85)         return { text: 'Hung assembly likely', color: '' };
    if (declared >= 36)         return { text: 'Trends indicate hung assembly', color: '' };
    return                             { text: 'Early trends', color: '' };
  }, [declared, seatsActive, totalSeats, hasMajority, leading]);

  // Party breakdown for bar — each party is its own segment
  const partyBreakdown = useMemo(() => {
    const bd: Record<string, { alliance: string; count: number; partyColor: string }> = {};
    constituencies.forEach(c => {
      const live = c.status === 'IN_PROGRESS' || c.status === 'RESULT_DECLARED';
      if (live && c.leader) {
        const code     = c.leader.party;
        const alliance = c.leader.alliance;
        const pColor   = resolvePartyColor(code, alliance, parties);
        if (!bd[code]) bd[code] = { alliance, count: 0, partyColor: pColor };
        bd[code].count++;
      }
    });
    // Sort: LDF → NDA → OTH (non-IND) → IND/supported → UDF
    // IND parties have alliance=OTH — give pure IND and supported-IND a sub-order within OTH
    const allianceOrder = (p: { alliance: string; party: string }): number => {
      if (p.alliance === 'LDF') return 1;
      if (p.alliance === 'NDA') return 2;
      if (p.alliance === 'OTH' && !isRawIND(p.party) && !isSupportedIND(p.party)) return 3;
      if (isSupportedIND(p.party)) return 4;
      if (isRawIND(p.party)) return 5;
      if (p.alliance === 'UDF') return 6;
      return 7;
    };
    return Object.entries(bd)
      .map(([party, d]) => ({ party, ...d }))
      .sort((a, b) => allianceOrder(a) - allianceOrder(b) || b.count - a.count);
  }, [constituencies, parties]);

  // ── Filtering ────
  const handleRegionClick = (r: Region) => {
    if (activeRegion === r) { setActiveRegion(null); setActiveDistrict(null); }
    else { setActiveRegion(r); setActiveDistrict(null); }
  };
  const handleDistrictClick = (d: string) => {
    if (activeDistrict === d) { setActiveDistrict(null); setActiveRegion(null); }
    else { setActiveDistrict(d); setActiveRegion(DISTRICT_REGION[d] || null); }
  };

  const filteredConstituencies = useMemo(() => {
    return constituencies.filter(c => {
      if (activeDistrict && c.district !== activeDistrict) return false;
      if (!activeDistrict && activeRegion && c.region !== activeRegion) return false;
      if (searchTerm) {
        const s = searchTerm.toLowerCase();
        if (!c.name.toLowerCase().includes(s)) return false;
      }
      if (activeResultFilter) {
        const winAl  = c.leader?.alliance;
        const sittAl = c.sitting_alliance;
        const margin = c.leader && c.runner_up ? c.leader.votes - c.runner_up.votes : null;
        const hasResult = c.status === 'RESULT_DECLARED' || (c.status === 'IN_PROGRESS' && winAl);

        if (filterMode === 'inplay') {
          // ── In Play: cross-alliance quick filters ──────────────────────────
          if (activeResultFilter === 'all_bare') {
            return c.status === 'IN_PROGRESS' && margin !== null && margin < LEAN_MARGIN && !!winAl;
          }
          if (activeResultFilter === 'all_leading') {
            return c.status === 'IN_PROGRESS' && !!winAl;
          }
          if (activeResultFilter === 'all_won') {
            return c.status === 'RESULT_DECLARED';
          }
          // ── Per-alliance margin filters (only IN_PROGRESS) ────────────────
          if (c.status !== 'IN_PROGRESS') return false;
          if (!winAl) return false;
          // Parse filter key: e.g. 'ldf_strong', 'udf_lean', 'nda_bare'
          const [fAl, fBucket] = activeResultFilter.split('_');
          const alUpper = fAl.toUpperCase();
          if (winAl !== alUpper) return false;
          if (margin === null) return false;
          if (fBucket === 'strong') return margin >= STRONG_MARGIN;
          if (fBucket === 'lean')   return margin >= LEAN_MARGIN && margin < STRONG_MARGIN;
          if (fBucket === 'bare')   return margin < LEAN_MARGIN;
          return true;
        } else {
          // ── Results: Held / Gained / Lost ───────────────────────────────
          switch (activeResultFilter) {
            case 'ldf_held':    return hasResult && winAl === 'LDF' && sittAl === 'LDF';
            case 'ldf_gained':  return hasResult && winAl === 'LDF' && sittAl !== 'LDF';
            case 'ldf_lost':    return hasResult && winAl !== 'LDF' && sittAl === 'LDF';
            case 'udf_held':    return hasResult && winAl === 'UDF' && sittAl === 'UDF';
            case 'udf_gained':  return hasResult && winAl === 'UDF' && sittAl !== 'UDF';
            case 'udf_lost':    return hasResult && winAl !== 'UDF' && sittAl === 'UDF';
            case 'nda_held':    return hasResult && winAl === 'NDA' && sittAl === 'NDA';
            case 'nda_gained':  return hasResult && winAl === 'NDA' && sittAl !== 'NDA';
            case 'nda_lost':    return hasResult && winAl !== 'NDA' && sittAl === 'NDA';
            default: break;
          }
        }
      }
      return true;
    });
  }, [constituencies, activeRegion, activeDistrict, searchTerm, activeResultFilter, filterMode, STRONG_MARGIN, LEAN_MARGIN]);

  // ── Render ──────────────────────────────────────────────
  return (
    <div className="flex flex-col min-h-screen bg-pagebg text-ink">
      <GlobalHeader />
      {/* ── OFFLINE BANNER ── */}
      {showOfflineBanner && (
        <div style={{
          background: '#1C1917',
          borderBottom: '2px solid #78350F',
          padding: '8px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          flexShrink: 0,
        }}>
          <span style={{ fontSize: 14, flexShrink: 0 }}>⚠️</span>
          <span style={{ fontSize: 12, color: '#FDE68A', flex: 1 }}>
            <strong style={{ color: '#FCD34D' }}>Live connection lost.</strong>{' '}
            Showing last known results — will refresh automatically when reconnected.
          </span>
          <button
            onClick={() => setOfflineDismissed(true)}
            style={{ fontSize: 11, color: '#A16207', background: 'transparent', border: 'none', cursor: 'pointer', padding: '2px 6px' }}
          >Dismiss</button>
        </div>
      )}

      {/* ── HERO SUMMARY ── */}
      <div className="bg-surface px-4 md:px-8 pt-4 md:pt-6 pb-4 md:pb-5 border-b border-pageborder shrink-0">
        <div className="mb-4 md:mb-5">
          <div className="font-sans text-[22px] md:text-[26px] font-bold tracking-tight mb-1">2026 Assembly Results</div>
          <div className="text-[16px] text-ink2">
            <span className={`font-bold ${statusLabel.color}`}>{statusLabel.text}</span>
            <span className="text-pageborder mx-3">|</span>
            <span className="font-medium text-ink2">
              {seatsActive > 0
                ? <>{summary?.results_declared || 0} declared · {seatsActive} of {totalSeats} counting</>
                : <>0 of {totalSeats} seats counting</>}
            </span>
          </div>
        </div>

        {/* Alliance numbers row */}
        <div className="flex items-end mb-4 gap-0 overflow-x-auto custom-scrollbar pb-2 -mb-2">
          <div className="flex items-start shrink-0">
            {/* Fixed alliance blocks — always shown */}
            {[
              { label: 'LDF', seats: ldfSeats, color: ALLIANCE_COLORS.LDF },
              { label: 'UDF', seats: udfSeats, color: ALLIANCE_COLORS.UDF },
              { label: 'NDA', seats: ndaSeats, color: ALLIANCE_COLORS.NDA },
            ].map((a, i) => (
              <div key={a.label} className={`px-5 md:px-8 ${i < 2 ? 'border-r border-pageborder' : ''}`}>
                <div className="w-2.5 h-2.5 mb-2" style={{ backgroundColor: a.color }} />
                <div className="text-[13px] font-semibold mb-0.5" style={{ color: a.color }}>{a.label}</div>
                <div className="flex items-baseline gap-1.5">
                  <span className="font-sans font-bold text-[22px] text-ink leading-none">{a.seats} <span className="text-[14px]">seats</span></span>
                  <span className="text-[12px] text-ink2 font-mono font-medium">({((a.seats / totalSeats) * 100).toFixed(1)}%)</span>
                </div>
              </div>
            ))}

            {/* OTH block — only shown when > 0 */}
            {othSeats > 0 && (
              <div className="px-5 md:px-8 border-r border-pageborder">
                <div className="w-2.5 h-2.5 mb-2" style={{ backgroundColor: ALLIANCE_COLORS.OTH }} />
                <div className="text-[13px] font-semibold mb-0.5" style={{ color: ALLIANCE_COLORS.OTH }}>OTH</div>
                <div className="flex items-baseline gap-1.5">
                  <span className="font-sans font-bold text-[22px] text-ink leading-none">{othSeats} <span className="text-[14px]">seats</span></span>
                  <span className="text-[12px] text-ink2 font-mono font-medium">({((othSeats / totalSeats) * 100).toFixed(1)}%)</span>
                </div>
              </div>
            )}

            {/* IND block — only shown when > 0 */}
            {indSeats > 0 && (
              <div className="px-5 md:px-8 border-r border-pageborder">
                <div className="w-2.5 h-2.5 mb-2" style={{ backgroundColor: PURE_IND_COLOR }} />
                <div className="text-[13px] font-semibold mb-0.5" style={{ color: PURE_IND_COLOR }}>IND</div>
                <div className="flex items-baseline gap-1.5">
                  <span className="font-sans font-bold text-[22px] text-ink leading-none">{indSeats} <span className="text-[14px]">seats</span></span>
                  <span className="text-[12px] text-ink2 font-mono font-medium">({((indSeats / totalSeats) * 100).toFixed(1)}%)</span>
                </div>
              </div>
            )}

            {/* Top parties */}
            {[...partyBreakdown].sort((a, b) => b.count - a.count).slice(0, 6).map((p, idx, arr) => {
              const pc = p.partyColor;
              return (
                <div key={p.party} className={`px-5 md:px-8 ${idx < arr.length - 1 ? 'border-r border-pageborder' : ''}`}>
                  <div className="w-2.5 h-2.5 mb-2" style={{ backgroundColor: pc }} />
                  <div className="text-[13px] font-semibold text-ink mb-0.5" style={{ color: pc }}>{p.party}</div>
                  <div className="flex items-baseline gap-1.5">
                    <span className="font-sans font-bold text-[22px] text-ink leading-none">{p.count} <span className="text-[14px]">seats</span></span>
                    <span className="text-[12px] text-ink2 font-mono font-medium">({((p.count / totalSeats) * 100).toFixed(1)}%)</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Seat bars */}
        <div className="relative pt-1 pb-1 flex flex-col gap-1 mb-1">
          <div className="absolute left-[50.71%] top-1 bottom-0 w-[3px] bg-white z-20 shadow-[0_0_8px_rgba(0,0,0,0.5)] border-x border-black/30" title="71 seats for majority">
            <div className="absolute top-[100%] mt-1 text-[10px] font-bold text-ink2 bg-white px-1.5 py-0.5 rounded shadow-sm border border-pageborder whitespace-nowrap">Majority 71</div>
          </div>
          {/* Alliance-level bar — OTH is now split per-party */}
          <div className="h-[28px] flex w-full font-sans text-[15px] font-bold text-white relative shadow-sm rounded-sm overflow-hidden border border-pageborder/50">
            {ldfSeats > 0 && <div className="h-full bg-ldf transition-all duration-500 flex items-center px-3" style={{ width: `${(ldfSeats/totalSeats)*100}%` }}>{ldfSeats > 5 && ldfSeats}</div>}
            {ndaSeats > 0 && <div className="h-full bg-nda transition-all duration-500 flex items-center px-3" style={{ width: `${(ndaSeats/totalSeats)*100}%` }}>{ndaSeats > 5 && ndaSeats}</div>}
            {/* OTH parties — individual segments */}
            {partyBreakdown
              .filter(p => p.alliance === 'OTH' && !isRawIND(p.party) && !isSupportedIND(p.party))
              .map(p => (
                <div
                  key={p.party}
                  className="h-full transition-all duration-500 flex items-center px-1"
                  style={{ width: `${(p.count/totalSeats)*100}%`, backgroundColor: p.partyColor }}
                  title={`${p.party}: ${p.count}`}
                >
                  {p.count > 5 && <span className="text-[11px] font-bold">{p.count}</span>}
                </div>
              ))
            }
            {/* Supported IND — individual tinted segments */}
            {partyBreakdown
              .filter(p => isSupportedIND(p.party))
              .map(p => (
                <div
                  key={p.party}
                  className="h-full transition-all duration-500"
                  style={{ width: `${(p.count/totalSeats)*100}%`, backgroundColor: p.partyColor }}
                  title={`${p.party}: ${p.count}`}
                />
              ))
            }
            {/* Pure IND */}
            {indSeats > 0 && <div className="h-full transition-all duration-500 flex items-center px-3" style={{ width: `${(indSeats/totalSeats)*100}%`, backgroundColor: PURE_IND_COLOR }}>{indSeats > 5 && indSeats}</div>}
            {udfSeats > 0 && <div className="h-full bg-udf transition-all duration-500 flex items-center px-3" style={{ width: `${(udfSeats/totalSeats)*100}%` }}>{udfSeats > 5 && udfSeats}</div>}
            {(() => { const cnt = ldfSeats+ndaSeats+othSeats+indSeats+udfSeats; const unc = Math.max(0,totalSeats-cnt); return unc > 0 ? <div className="h-full bg-pageborder/50 transition-all duration-500" style={{ width: `${(unc/totalSeats)*100}%` }} title={`${unc} seats awaited`} /> : null; })()}
          </div>
          {/* Fine-grained party bar */}
          <div className="h-[8px] flex w-full shadow-sm rounded-sm overflow-hidden border border-pageborder/50">
            {partyBreakdown.map((p, i) => {
              if (p.count === 0) return null;
              return <div key={p.party+i} className="h-full border-r border-white/60 last:border-0 transition-all duration-500" style={{ width: `${(p.count/totalSeats)*100}%`, backgroundColor: p.partyColor }} title={`${p.party}: ${p.count}`} />;
            })}
          </div>
        </div>
      </div>

      {/* ── REGIONAL SUMMARY PANEL ── */}
      <div className="bg-surface px-4 md:px-8 py-2 border-b border-pageborder">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
          {REGION_META.map(rm => {
            const t = regionTally(constituencies, rm.key);
            const alliances = [
              { a: 'LDF' as const, s: t.LDF },
              { a: 'UDF' as const, s: t.UDF },
              { a: 'NDA' as const, s: t.NDA },
            ].sort((a, b) => b.s - a.s);
            const isActive = activeRegion === rm.key;

            return (
              <div
                key={rm.key}
                className="flex items-center gap-3 px-3 py-2 rounded cursor-pointer transition-all"
                style={{
                  backgroundColor: isActive ? '#F0EDE8' : 'transparent',
                  border: `1px solid ${isActive ? '#C9C4BC' : '#E8E4DF'}`,
                }}
                onClick={() => handleRegionClick(rm.key)}
              >
                <div className="shrink-0">
                  <div className="text-[12px] font-bold text-ink leading-none">{rm.label}</div>
                  <div className="text-[11px] text-ink2 mt-0.5 font-medium">{t.total} seats</div>
                </div>
                <div className="flex items-center gap-2 ml-auto">
                  {alliances.map(al => (
                    <div key={al.a} className="text-center">
                      <div className="text-[11px] font-bold font-mono leading-none" style={{ color: ALLIANCE_COLORS[al.a] }}>{al.s}</div>
                      <div className="text-[8px] font-semibold mt-0.5" style={{ color: ALLIANCE_COLORS[al.a], opacity: 0.7 }}>{al.a}</div>
                    </div>
                  ))}
                </div>
                {isActive && <div className="w-1.5 h-1.5 rounded-full bg-ink shrink-0" />}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── DISTRICT FILTER TABS + SEARCH ── */}
      <div className="bg-surface px-4 md:px-8 py-3 border-b border-pageborder flex flex-col md:flex-row md:items-center gap-3">
        <div className="flex gap-2 overflow-x-auto custom-scrollbar w-full md:flex-1 pb-1">
          <button
            className={`district-tab ${!activeDistrict && !activeRegion ? 'active' : ''}`}
            onClick={() => { setActiveDistrict(null); setActiveRegion(null); }}
          >All {totalSeats}</button>
          {DISTRICT_ORDER.map(d => {
            const isActive = activeDistrict === d;
            const inRegion = !activeDistrict && activeRegion && DISTRICT_REGION[d] === activeRegion;
            return (
              <button
                key={d}
                className={`district-tab ${isActive ? 'active' : inRegion ? 'bg-ink/10 border-ink/30 text-ink' : ''}`}
                onClick={() => handleDistrictClick(d)}
              >{d}</button>
            );
          })}
        </div>
        <div className="flex items-center gap-2 bg-pagebg border border-pageborder rounded-md px-3 py-1.5 shrink-0 w-full md:w-[220px]">
          <span className="text-ink2 text-sm">⌕</span>
          <input
            type="text"
            placeholder="Search..."
            className="bg-transparent border-none outline-none w-full text-[13px] font-sans text-ink placeholder-ink2"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {/* ── FILTER MODE TABS + CHIPS ── */}
      <div className="bg-surface border-b border-pageborder">

        {/* Mode tabs */}
        <div className="flex items-center px-4 md:px-8 pt-2 gap-0 border-b border-pageborder">
          <button
            onClick={() => { setFilterMode('inplay'); setActiveResultFilter(null); }}
            className="text-[11px] font-bold tracking-widest uppercase px-4 py-2 border-b-2 transition-all duration-150"
            style={{
              borderBottomColor: filterMode === 'inplay' ? '#1A1611' : 'transparent',
              color: filterMode === 'inplay' ? '#1A1611' : '#9CA3AF',
            }}
          >
            In Play
          </button>
          <button
            onClick={() => { setFilterMode('results'); setActiveResultFilter(null); }}
            className="text-[11px] font-bold tracking-widest uppercase px-4 py-2 border-b-2 transition-all duration-150"
            style={{
              borderBottomColor: filterMode === 'results' ? '#1A1611' : 'transparent',
              color: filterMode === 'results' ? '#1A1611' : '#9CA3AF',
            }}
          >
            Results
            {allDeclared && <span className="ml-1.5 text-[8px] bg-green-600 text-white px-1.5 py-0.5 rounded-full">ALL IN</span>}
          </button>
          {activeResultFilter && (
            <button
              onClick={() => setActiveResultFilter(null)}
              className="ml-auto text-[11px] text-ink2 hover:text-ink underline shrink-0"
            >Clear</button>
          )}
        </div>

        {/* In Play chips */}
        {filterMode === 'inplay' && (
          <div className="flex flex-col gap-1 px-4 md:px-8 py-2 overflow-x-auto custom-scrollbar">

            {/* ── Row 1: Cross-alliance summary chips ── */}
            <div className="flex items-center gap-2">
              <span className="text-[9px] font-bold tracking-widest uppercase text-ink2 shrink-0 w-14">All</span>
              {([
                {
                  key: 'all_leading',
                  label: 'Leading',
                  icon: '▶',
                  title: 'All seats still being counted (any lead)',
                  count: constituencies.filter(c => c.status === 'IN_PROGRESS' && !!c.leader).length,
                  color: '#1A1611',
                },
                {
                  key: 'all_bare',
                  label: 'Bare leads',
                  icon: '≈',
                  title: `Any alliance leading by < ${(LEAN_MARGIN/1000).toFixed(0)}k votes`,
                  count: constituencies.filter(c => {
                    const m = c.leader && c.runner_up ? c.leader.votes - c.runner_up.votes : null;
                    return c.status === 'IN_PROGRESS' && m !== null && m < LEAN_MARGIN && !!c.leader;
                  }).length,
                  color: '#DC2626',
                },
                {
                  key: 'all_won',
                  label: 'Won',
                  icon: '✓',
                  title: 'Seats already declared (counting complete)',
                  count: constituencies.filter(c => c.status === 'RESULT_DECLARED').length,
                  color: '#15803D',
                },
              ].map(chip => {
                const isActive = activeResultFilter === chip.key;
                return (
                  <button
                    key={chip.key}
                    title={chip.title}
                    onClick={() => setActiveResultFilter(isActive ? null : chip.key)}
                    className="text-[11px] font-semibold px-2.5 py-1 rounded-full border transition-all duration-150 whitespace-nowrap shrink-0 flex items-center gap-1"
                    style={{
                      borderColor: isActive ? chip.color : `${chip.color}55`,
                      background: isActive ? chip.color : 'transparent',
                      color: isActive ? '#fff' : chip.color,
                    }}
                  >
                    <span style={{ fontSize: '9px', opacity: 0.85 }}>{chip.icon}</span>
                    {chip.label}
                    {chip.count > 0 && <span style={{ fontSize: '9px', fontWeight: 800, opacity: isActive ? 0.9 : 0.7 }}>{chip.count}</span>}
                  </button>
                );
              }))}
            </div>


            {/* ── Row 2: Per-alliance margin chips ── */}
            <div className="flex items-center gap-2">
            {(['LDF', 'UDF', 'NDA'] as const).map((al, gi) => {
              const color = ALLIANCE_COLORS[al];
              const chips = [
                { key: `${al.toLowerCase()}_strong`, label: 'Strong', icon: '⬆', title: `${al} leading by >${(STRONG_MARGIN/1000).toFixed(0)}k votes` },
                { key: `${al.toLowerCase()}_lean`,   label: 'Lean',   icon: '↑',  title: `${al} leading by ${(LEAN_MARGIN/1000).toFixed(0)}k–${(STRONG_MARGIN/1000).toFixed(0)}k votes` },
                { key: `${al.toLowerCase()}_bare`,   label: 'Bare',   icon: '≈',  title: `${al} barely ahead (< ${(LEAN_MARGIN/1000).toFixed(0)}k votes)` },
              ];
              // Counts — IN_PROGRESS only (seats still being counted, not yet declared)
              const strongN = constituencies.filter(c => {
                const m = c.leader && c.runner_up ? c.leader.votes - c.runner_up.votes : null;
                return c.status === 'IN_PROGRESS' && c.leader?.alliance === al && m !== null && m >= STRONG_MARGIN;
              }).length;
              const leanN = constituencies.filter(c => {
                const m = c.leader && c.runner_up ? c.leader.votes - c.runner_up.votes : null;
                return c.status === 'IN_PROGRESS' && c.leader?.alliance === al && m !== null && m >= LEAN_MARGIN && m < STRONG_MARGIN;
              }).length;
              const bareN = constituencies.filter(c => {
                const m = c.leader && c.runner_up ? c.leader.votes - c.runner_up.votes : null;
                return c.status === 'IN_PROGRESS' && c.leader?.alliance === al && m !== null && m < LEAN_MARGIN;
              }).length;
              const counts = [strongN, leanN, bareN];
              return (
                <div key={al} className={`flex items-center gap-1.5 ${gi > 0 ? 'border-l border-pageborder pl-3' : ''}`}>
                  <span className="text-[10px] font-bold shrink-0" style={{ color }}>{al}</span>
                  {chips.map((ch, ci) => {
                    const isActive = activeResultFilter === ch.key;
                    const n = counts[ci];
                    return (
                      <button
                        key={ch.key}
                        title={ch.title}
                        onClick={() => setActiveResultFilter(isActive ? null : ch.key)}
                        className="text-[11px] font-semibold px-2.5 py-1 rounded-full border transition-all duration-150 whitespace-nowrap shrink-0 flex items-center gap-1"
                        style={{
                          borderColor: isActive ? color : `${color}55`,
                          background: isActive ? color : 'transparent',
                          color: isActive ? '#fff' : color,
                        }}
                      >
                        <span style={{ fontSize: '9px', opacity: 0.85 }}>{ch.icon}</span>
                        {ch.label}
                        {n > 0 && <span style={{ fontSize: '9px', fontWeight: 800, opacity: isActive ? 0.9 : 0.7 }}>{n}</span>}
                      </button>
                    );
                  })}
                </div>
              );
            })}
            </div>
          </div>
        )}




        {/* Results chips */}
        {filterMode === 'results' && (
          <div className="flex items-center gap-2 px-4 md:px-8 py-2 overflow-x-auto custom-scrollbar">
            {(['LDF', 'UDF', 'NDA'] as const).map((al, gi) => {
              const color = ALLIANCE_COLORS[al];
              const chips = [
                { key: `${al.toLowerCase()}_held`,   label: 'Held',   icon: '=',  title: `${al} retained seat from 2021` },
                { key: `${al.toLowerCase()}_gained`, label: 'Gained', icon: '↑',  title: `${al} flipped from another alliance` },
                { key: `${al.toLowerCase()}_lost`,   label: 'Lost',   icon: '↓',  title: `${al} lost seat it held in 2021` },
              ];
              return (
                <div key={al} className={`flex items-center gap-1.5 ${gi > 0 ? 'border-l border-pageborder pl-3' : ''}`}>
                  {chips.map(ch => {
                    const isActive = activeResultFilter === ch.key;
                    return (
                      <button
                        key={ch.key}
                        title={ch.title}
                        onClick={() => setActiveResultFilter(isActive ? null : ch.key)}
                        className="text-[11px] font-semibold px-2.5 py-1 rounded-full border transition-all duration-150 whitespace-nowrap shrink-0"
                        style={{
                          borderColor: isActive ? color : `${color}55`,
                          background: isActive ? color : 'transparent',
                          color: isActive ? '#fff' : color,
                        }}
                      >
                        <span style={{ fontSize: '9px', opacity: 0.85 }}>{ch.icon}</span> {ch.label}
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </div>
        )}

      </div>

      {/* ── CONSTITUENCY CARD GRID ── */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-4 md:px-6 py-4">
        {/* ── PINNED SEATS SECTION ── */}
        {pinnedConstituencies.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-[11px] font-bold tracking-widest uppercase text-ink2">📌 Pinned</span>
              <span className="text-[10px] text-ink2 opacity-60">{pinnedConstituencies.length}/10</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 300px), 1fr))', gap: '12px' }}>
              {pinnedConstituencies.map(c => (
                <ConstituencyCard
                  key={c.id}
                  c={c}
                  onClick={() => navigate(`/constituency/${c.id}`)}
                  isPinned={true}
                  onPinToggle={e => { e.stopPropagation(); toggle(String(c.id)); }}
                />
              ))}
            </div>
            <div className="mt-4 border-b border-pageborder" />
          </div>
        )}

        {loadingConst ? (
          <div className="text-center text-ink2 py-16">Loading constituencies...</div>
        ) : filteredConstituencies.length === 0 ? (
          <div className="text-center text-ink2 py-16 text-[14px]">No constituencies match your filters</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 300px), 1fr))', gap: '12px' }}>
            {filteredConstituencies.filter(c => !isPinned(String(c.id))).map(c => (
              <ConstituencyCard
                key={c.id}
                c={c}
                onClick={() => navigate(`/constituency/${c.id}`)}
                isPinned={isPinned(String(c.id))}
                onPinToggle={e => { e.stopPropagation(); toggle(String(c.id)); }}
              />
            ))}
          </div>
        )}
      </div>

      {/* ── BOTTOM TICKER ── */}
      <div className="bg-ink text-white/60 text-[12px] py-2 px-4 md:px-8 flex items-center gap-4 border-t border-white/5 overflow-hidden shrink-0">
        <div className="text-[10px] font-bold tracking-widest uppercase text-gold shrink-0">Updates</div>
        <div className="overflow-hidden flex-1">
          <div className="ticker-scroll">
            {constituencies
              .filter(c => c.status === 'IN_PROGRESS' && c.leader)
              .slice(0, 10)
              .concat(constituencies.filter(c => c.status === 'IN_PROGRESS' && c.leader).slice(0, 10))
              .map((c, i) => (
                <span key={i} className="text-white/50">
                  <strong className="text-white font-semibold">{c.name}</strong>{' '}
                  {c.leader!.party} {c.leader!.alliance === 'LDF' ? '🔴' : c.leader!.alliance === 'UDF' ? '🔵' : '🟠'} leading
                  {c.runner_up ? ` by ${(c.leader!.votes - c.runner_up.votes).toLocaleString('en-IN')}` : ''} ·
                </span>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Constituency Card Component ────────────────────────────
function ConstituencyCard({
  c, onClick, isPinned = false, onPinToggle,
}: {
  c: ConstituencyListItem;
  onClick: () => void;
  isPinned?: boolean;
  onPinToggle?: (e: React.MouseEvent) => void;
}) {
  const isLive = c.status === 'IN_PROGRESS';
  const isDone = c.status === 'RESULT_DECLARED';
  const countingStarted = isLive || isDone;
  const alliance = c.leader?.alliance || '';

  // Resolve card background
  const bg = countingStarted && c.leader
    ? resolveCardBg(c.leader.party, alliance, c.leader.party_color ?? '', [])
    : '#E8E4DF';
  
  // Badge text color = card bg color (badge is white circle, text should be party color)
  const badgeTextColor = bg;

  const margin = countingStarted && c.leader && c.runner_up
    ? c.leader.votes - c.runner_up.votes : null;
  const BARE_THRESHOLD = 3_000;
  const isClose = isLive && margin !== null && margin < BARE_THRESHOLD;

  // Progress: prefer counted/polled, fallback to rounds, then proxy
  const progressPct = isDone ? 100
    : isLive && c.votes_counted && c.votes_polled && c.votes_polled > 0
      ? Math.min(100, Math.round((c.votes_counted / c.votes_polled) * 100))
    : isLive && c.rounds_completed && c.total_rounds && c.total_rounds > 0
      ? Math.round((c.rounds_completed / c.total_rounds) * 100)
    : isLive && c.leader
      ? Math.min(95, Math.max(6, Number(c.leader.percentage) * 2))
    : 0;

  const statusLabel = isDone ? 'WON' : isLive ? 'LEADING' : 'AWAITED';

  // Stripe color = runner-up's color — for OTH/IND use actual party color, not generic grey
  const ruStripeColor = isClose && c.runner_up
    ? (() => {
        const al  = c.runner_up!.alliance;
        const ru  = c.runner_up!;
        let base: string;
        if (al === 'OTH' || ru.party === 'IND') {
          // Use party_color from DB; fall back to alliance grey
          base = ru.party_color || ALLIANCE_COLORS.OTH;
        } else {
          base = ALLIANCE_COLORS[al] || '#000000';
        }
        // IND-vs-IND: both card bg and stripe would be the same grey → use dark slate instead
        if (base === PURE_IND_COLOR || base === '#6B7280') {
          base = '#1E293B'; // dark slate — contrasts clearly against grey
        }
        return base + '66'; // hex alpha ~40%
      })()
    : 'rgba(0,0,0,0.13)';

  return (
    <div
      onClick={onClick}
      className="rounded-md cursor-pointer transition-all duration-150 hover:brightness-110 overflow-hidden relative"
      style={{
        backgroundColor: bg,
        // Bare: diagonal stripes in runner-up alliance color — encodes the contest dynamic
        backgroundImage: isClose
          ? `repeating-linear-gradient(45deg, transparent, transparent 7px, ${ruStripeColor} 7px, ${ruStripeColor} 9px)`
          : 'none',
        boxShadow: isClose
          ? '0 4px 18px rgba(0,0,0,0.35)'
          : '0 1px 4px rgba(0,0,0,0.15)',
      }}
    >
      <div className="px-3 pt-2.5 pb-2">
        {/* Header: pin + number + status label */}
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1">
            {onPinToggle && (
              <button
                onClick={onPinToggle}
                title={isPinned ? 'Unpin' : 'Pin this seat'}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 3,
                  fontSize: 10,
                  fontWeight: 700,
                  padding: '2px 6px',
                  borderRadius: 99,
                  border: 'none',
                  cursor: 'pointer',
                  lineHeight: 1,
                  transition: 'all 0.15s',
                  background: isPinned ? '#1E293B' : 'rgba(255,255,255,0.82)',
                  color: isPinned ? '#fff' : '#6B7280',
                  boxShadow: isPinned ? '0 1px 6px rgba(0,0,0,0.4)' : '0 1px 3px rgba(0,0,0,0.2)',
                  backdropFilter: 'blur(4px)',
                }}
              >
                <span style={{ fontSize: 11 }}>📌</span>
                {isPinned && <span style={{ fontSize: 9 }}>Pinned</span>}
              </button>
            )}
            <span
              className="font-mono text-[9px]"
              style={{ color: countingStarted ? 'rgba(255,255,255,0.5)' : '#9CA3AF' }}
            >#{String(c.number).padStart(3, '0')}</span>
          </div>
          {isClose ? (
            // BARE badge — dark semi-transparent, readable on all alliance colors
            <span
              className="text-[8px] font-black tracking-wider px-1.5 py-0.5 rounded"
              style={{ backgroundColor: 'rgba(0,0,0,0.45)', color: 'rgba(255,255,255,0.95)' }}
            >⚡ BARE</span>
          ) : (
            <span
              className="text-[8px] font-bold tracking-wider px-1.5 py-0.5 rounded"
              style={{
                backgroundColor: countingStarted ? 'rgba(0,0,0,0.2)' : '#D1CBC4',
                color: countingStarted ? 'rgba(255,255,255,0.9)' : '#6B7280',
              }}
            >{statusLabel}</span>
          )}
        </div>

        {/* Constituency name and 2021 seat info */}
        <div className="mb-2">
          <div
            className="text-[12px] font-bold leading-tight truncate"
            style={{ color: countingStarted ? 'white' : '#333' }}
            title={c.name}
          >{c.name}</div>
          {c.sitting_alliance && (
            <div className="mt-1 flex items-center gap-1.5" style={{ opacity: countingStarted ? 0.8 : 1 }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 3, border: `1px solid ${countingStarted ? 'rgba(255,255,255,0.3)' : (ALLIANCE_COLORS[c.sitting_alliance] || '#9CA3AF') + '40'}`, borderRadius: 12, padding: '1px 5px', background: countingStarted ? 'rgba(0,0,0,0.1)' : 'transparent' }}>
                <div style={{ width: 4, height: 4, borderRadius: '50%', background: countingStarted ? 'white' : (ALLIANCE_COLORS[c.sitting_alliance] || '#9CA3AF'), flexShrink: 0 }} />
                <span style={{ fontSize: 8, fontWeight: 700, color: countingStarted ? 'white' : (ALLIANCE_COLORS[c.sitting_alliance] || '#9CA3AF') }}>{c.sitting_alliance}</span>
                <span style={{ fontSize: 8, color: countingStarted ? 'rgba(255,255,255,0.7)' : '#9CA3AF' }}>seat (2021)</span>
              </div>
            </div>
          )}
        </div>

        {countingStarted && c.leader ? (
          <>
            {/* Margin row + party badge */}
            <div className="flex items-center justify-between mb-2 gap-2">
              {/* MARGIN — hero number */}
              <div
                className="font-black leading-none"
                style={{ fontSize: '22px', color: 'white' }}
              >
                {margin !== null ? `+${margin.toLocaleString('en-IN')}` : '—'}
              </div>

              {/* Party round badge */}
              <div
                className="shrink-0 w-9 h-9 rounded-full flex items-center justify-center font-bold text-[10px] tracking-wide"
                style={{ backgroundColor: 'rgba(255,255,255,0.95)', color: badgeTextColor }}
                title={c.leader.party}
              >
              {partyAbbr(c.leader.party)}
              </div>
            </div>

            {/* Leader */}
            <div
              className="text-[11px] font-semibold truncate mb-1"
              style={{ color: 'white' }}
              title={c.leader.name}
            >{c.leader.name}</div>
            <div
              className="text-[9px] font-medium truncate mb-2 flex items-center gap-1.5"
              style={{ color: 'rgba(255,255,255,0.65)' }}
            >
              {partyDisplay(c.leader.party)}
              <span
                className="px-1 py-0 rounded text-[8px] font-bold shrink-0"
                style={{ background: 'rgba(255,255,255,0.18)', color: 'rgba(255,255,255,0.9)' }}
              >{alliance}</span>
            </div>

            {/* Runner-up */}
            {c.runner_up && (() => {
              // Runner-up color: use party_color from API for OTH, else alliance color
              const ruAlliance = c.runner_up.alliance;
              const ruColor = ruAlliance === 'OTH' || isRawIND(c.runner_up.party) || isSupportedIND(c.runner_up.party)
                ? (c.runner_up.party_color || ALLIANCE_COLORS[ruAlliance] || '#6B7280')
                : (ALLIANCE_COLORS[ruAlliance] || '#6B7280');
              return (
                <div
                  className="mt-1.5 rounded px-2 py-1 flex items-center gap-1.5 min-w-0"
                  style={{ backgroundColor: 'rgba(255,255,255,0.95)' }}
                >
                  <span className="text-[9px] font-semibold shrink-0" style={{ color: ruColor, opacity: 0.6 }}>2nd</span>
                  <span className="text-[10px] font-semibold truncate" style={{ color: ruColor }} title={c.runner_up.name}>{c.runner_up.name}</span>
                  <span className="text-[10px] font-semibold shrink-0" style={{ color: ruColor, opacity: 0.8 }}>{partyDisplay(c.runner_up.party)} · {c.runner_up.alliance}</span>
                </div>
              );
            })()}
          </>
        ) : (
          <div className="text-[10px] italic flex items-center gap-1.5" style={{ color: '#9CA3AF' }}>
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-neutral-400/60" />
            Not yet started
          </div>
        )}
      </div>

      {/* Progress bar + % — always at bottom */}
      <div className="px-3 pb-2 pt-1">
        <div className="flex items-center justify-between mb-1">
          <div
            className="text-[8px] font-semibold"
            style={{ color: countingStarted ? 'rgba(255,255,255,0.55)' : 'transparent' }}
          >Counting</div>
          <div
            className="text-[8px] font-bold"
            style={{ color: countingStarted ? 'rgba(255,255,255,0.8)' : 'transparent' }}
          >{progressPct === 100 ? '100%' : progressPct > 0 ? `~${Math.round(progressPct)}%` : ''}</div>
        </div>
        <div className="h-[3px] rounded-full" style={{ backgroundColor: 'rgba(0,0,0,0.2)' }}>
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${progressPct}%`,
              backgroundColor: 'rgba(255,255,255,0.6)',
              opacity: progressPct === 0 ? 0 : 1,
            }}
          />
        </div>
      </div>
    </div>
  );
}

