import { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStateSummary, useConstituencies, useParties } from '../hooks/useElectionData';
import type { Alliance, Region, ConstituencyListItem } from '../types';
import GlobalHeader from '../components/GlobalHeader';
import { partyAbbr } from '../utils/partyAbbr';

// ── Constants ──────────────────────────────────────────────
const ALLIANCE_COLORS: Record<string, string> = {
  LDF: '#D42B2B', UDF: '#1A8FE3', NDA: '#F7921C', OTH: '#9CA3AF',
};

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

// ── Helper: party colour ───────────────────────────────────
const PARTY_COLORS: Record<string, string> = {
  'CPI(M)': '#DF2525', CPIM: '#DF2525', CPI: '#EF4444',
  INC: '#19AAED', IUML: '#16A34A', 'KEC(M)': '#EAB308',
  RSP: '#B91C1C', BJP: '#F97316', BDJS: '#FDBA74',
};

function getPartyColor(code: string, alliance: string, parties: { code: string; color_code?: string }[]): string {
  const p = parties.find(x => x.code === code);
  if (p?.color_code) return p.color_code;
  if (PARTY_COLORS[code]) return PARTY_COLORS[code];
  return ALLIANCE_COLORS[alliance] || '#6B7280';
}

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

  const [activeRegion, setActiveRegion] = useState<Region | null>(null);
  const [activeDistrict, setActiveDistrict] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeResultFilter, setActiveResultFilter] = useState<string | null>(null);

  const SMALL_MARGIN = 8_000; // votes — "lead by small margin"
  const CLOSE_MARGIN = 4_000; // votes — "close contest"

  // ── Derived data ────
  const totalSeats = summary?.total_constituencies || 140;

  const indSeats = useMemo(() =>
    constituencies.filter(c => {
      const live = c.status === 'IN_PROGRESS' || c.status === 'RESULT_DECLARED';
      return live && c.leader?.party === 'IND';
    }).length
  , [constituencies]);

  const ldfSeats = summary ? summary.alliance_summary.LDF.won + summary.alliance_summary.LDF.leading : 0;
  const udfSeats = summary ? summary.alliance_summary.UDF.won + summary.alliance_summary.UDF.leading : 0;
  const ndaSeats = summary ? summary.alliance_summary.NDA.won + summary.alliance_summary.NDA.leading : 0;
  const othSeatsRaw = summary ? (summary.alliance_summary.OTH?.won || 0) + (summary.alliance_summary.OTH?.leading || 0) : 0;
  const othSeats = Math.max(0, othSeatsRaw - indSeats);

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

  const statusLabel = useMemo(() => {
    if (countingPct === 0) return { text: 'Awaiting results', color: '' };
    if (hasMajority) {
      const verb = countingPct >= 90 ? 'wins majority' : countingPct >= 60 ? 'heading for majority' : countingPct >= 25 ? 'on course for majority' : 'early majority trend';
      return { text: `${leading.name} ${verb}`, color: leading.name === 'LDF' ? 'text-ldf' : leading.name === 'UDF' ? 'text-udf' : 'text-nda' };
    }
    const phase = countingPct < 25 ? 'early trends' : countingPct < 60 ? 'mid-count trends' : countingPct < 90 ? 'near-final trends' : 'final results';
    return { text: `Hung Assembly — ${phase}`, color: '' };
  }, [countingPct, hasMajority, leading]);

  // Party breakdown for bar
  const partyBreakdown = useMemo(() => {
    const bd: Record<string, { alliance: string; count: number }> = {};
    constituencies.forEach(c => {
      const live = c.status === 'IN_PROGRESS' || c.status === 'RESULT_DECLARED';
      if (live && c.leader) {
        const a = c.leader.party === 'IND' ? 'IND' : c.leader.alliance;
        if (!bd[c.leader.party]) bd[c.leader.party] = { alliance: a, count: 0 };
        bd[c.leader.party].count++;
      }
    });
    const order: Record<string, number> = { LDF: 1, NDA: 2, OTH: 3, IND: 4, UDF: 5 };
    return Object.entries(bd)
      .map(([party, d]) => ({ party, ...d }))
      .sort((a, b) => (order[a.alliance] ?? 3) - (order[b.alliance] ?? 3) || b.count - a.count);
  }, [constituencies]);

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
        if (!c.name.toLowerCase().includes(s) && !c.district.toLowerCase().includes(s)) return false;
      }
      if (activeResultFilter) {
        const margin = (c.leader && c.runner_up) ? c.leader.votes - c.runner_up.votes : null;
        const al = c.leader?.alliance;
        const isDone = c.status === 'RESULT_DECLARED';
        const isLive = c.status === 'IN_PROGRESS';
        switch (activeResultFilter) {
          case 'ldf_won':   return isDone && al === 'LDF';
          case 'ldf_lead':  return isLive && al === 'LDF';
          case 'ldf_close': return isLive && al === 'LDF' && margin !== null && margin < SMALL_MARGIN;
          case 'udf_won':   return isDone && al === 'UDF';
          case 'udf_lead':  return isLive && al === 'UDF';
          case 'udf_close': return isLive && al === 'UDF' && margin !== null && margin < SMALL_MARGIN;
          case 'nda_won':   return isDone && al === 'NDA';
          case 'nda_lead':  return isLive && al === 'NDA';
          case 'nda_close': return isLive && al === 'NDA' && margin !== null && margin < SMALL_MARGIN;
          case 'close':     return (isLive || isDone) && margin !== null && margin < CLOSE_MARGIN;
          default: break;
        }
      }
      return true;
    });
  }, [constituencies, activeRegion, activeDistrict, searchTerm, activeResultFilter, SMALL_MARGIN, CLOSE_MARGIN]);

  // ── Render ──────────────────────────────────────────────
  return (
    <div className="flex flex-col min-h-screen bg-pagebg text-ink">
      <GlobalHeader />

      {/* ── HERO SUMMARY ── */}
      <div className="bg-surface px-8 pt-6 pb-5 border-b border-pageborder shrink-0">
        <div className="mb-5">
          <div className="font-sans text-[26px] font-bold tracking-tight mb-1">2026 Assembly Results</div>
          <div className="text-[16px] text-ink2">
            <span className={`font-bold ${statusLabel.color}`}>{statusLabel.text}</span>
            <span className="text-pageborder mx-3">|</span>
            <span className="font-medium text-ink2">{summary?.results_declared || 0} of {totalSeats} seats declared</span>
          </div>
        </div>

        {/* Alliance numbers row */}
        <div className="flex items-end mb-4 gap-0 overflow-x-auto custom-scrollbar pb-2 -mb-2">
          <div className="flex items-start shrink-0">
            {[
              { label: 'LDF', seats: ldfSeats, color: ALLIANCE_COLORS.LDF },
              { label: 'UDF', seats: udfSeats, color: ALLIANCE_COLORS.UDF },
              { label: 'NDA', seats: ndaSeats, color: ALLIANCE_COLORS.NDA },
              { label: 'IND', seats: indSeats, color: '#6B7280' },
              { label: 'OTH', seats: othSeats, color: '#9CA3AF' },
            ].map((a, i) => (
              <div key={a.label} className={`px-8 ${i < 4 ? 'border-r border-pageborder' : ''} ${i === 4 ? 'border-r-2 border-dashed border-pageborder' : ''}`}>
                <div className="w-2.5 h-2.5 mb-2" style={{ backgroundColor: a.color }} />
                <div className="text-[13px] font-semibold mb-0.5" style={{ color: a.color }}>{a.label}</div>
                <div className="flex items-baseline gap-1.5">
                  <span className="font-sans font-bold text-[22px] text-ink leading-none">{a.seats} <span className="text-[14px]">seats</span></span>
                  <span className="text-[12px] text-ink2 font-mono font-medium">({((a.seats / totalSeats) * 100).toFixed(1)}%)</span>
                </div>
              </div>
            ))}

            {/* Top parties */}
            {[...partyBreakdown].sort((a, b) => b.count - a.count).slice(0, 6).map((p, idx, arr) => {
              const pc = getPartyColor(p.party, p.alliance, parties);
              return (
                <div key={p.party} className={`px-8 ${idx < arr.length - 1 ? 'border-r border-pageborder' : ''}`}>
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
          <div className="h-[28px] flex w-full font-sans text-[15px] font-bold text-white relative shadow-sm rounded-sm overflow-hidden border border-pageborder/50">
            {ldfSeats > 0 && <div className="h-full bg-ldf transition-all duration-500 flex items-center px-3" style={{ width: `${(ldfSeats/totalSeats)*100}%` }}>{ldfSeats > 5 && ldfSeats}</div>}
            {ndaSeats > 0 && <div className="h-full bg-nda transition-all duration-500 flex items-center px-3" style={{ width: `${(ndaSeats/totalSeats)*100}%` }}>{ndaSeats > 5 && ndaSeats}</div>}
            {othSeats > 0 && <div className="h-full bg-oth transition-all duration-500 flex items-center px-3" style={{ width: `${(othSeats/totalSeats)*100}%` }}>{othSeats > 5 && othSeats}</div>}
            {indSeats > 0 && <div className="h-full bg-gray-500 transition-all duration-500 flex items-center px-3" style={{ width: `${(indSeats/totalSeats)*100}%` }}>{indSeats > 5 && indSeats}</div>}
            {udfSeats > 0 && <div className="h-full bg-udf transition-all duration-500 flex items-center px-3" style={{ width: `${(udfSeats/totalSeats)*100}%` }}>{udfSeats > 5 && udfSeats}</div>}
            {(() => { const cnt = ldfSeats+ndaSeats+othSeats+indSeats+udfSeats; const unc = Math.max(0,totalSeats-cnt); return unc > 0 ? <div className="h-full bg-pageborder/50 transition-all duration-500" style={{ width: `${(unc/totalSeats)*100}%` }} title={`${unc} seats awaited`} /> : null; })()}
          </div>
          <div className="h-[8px] flex w-full shadow-sm rounded-sm overflow-hidden border border-pageborder/50">
            {partyBreakdown.map((p, i) => {
              if (p.count === 0) return null;
              return <div key={p.party+i} className="h-full border-r border-white/60 last:border-0 transition-all duration-500" style={{ width: `${(p.count/totalSeats)*100}%`, backgroundColor: getPartyColor(p.party, p.alliance, parties) }} title={`${p.party}: ${p.count}`} />;
            })}
          </div>
        </div>
      </div>

      {/* ── REGIONAL SUMMARY PANEL ── */}
      <div className="bg-surface px-8 py-2 border-b border-pageborder">
        <div className="grid grid-cols-4 gap-2">
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
      <div className="bg-surface px-8 py-3 border-b border-pageborder flex items-center gap-3">
        <div className="flex gap-2 overflow-x-auto custom-scrollbar flex-1 pb-1">
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
        <div className="flex items-center gap-2 bg-pagebg border border-pageborder rounded-md px-3 py-1.5 shrink-0 w-[220px]">
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

      {/* ── RESULT TYPE FILTER ── */}
      <div className="bg-surface px-8 py-2 border-b border-pageborder flex items-center gap-3 overflow-x-auto custom-scrollbar">
        <span className="text-[10px] font-bold tracking-widest uppercase text-ink2 shrink-0">Filter</span>

        {(['LDF', 'UDF', 'NDA'] as const).map((al, gi) => {
          const color = ALLIANCE_COLORS[al];
          const chips = [
            { key: `${al.toLowerCase()}_won`,   label: `${al} Won`,       icon: '✓' },
            { key: `${al.toLowerCase()}_lead`,  label: `${al} Lead`,      icon: '▲' },
            { key: `${al.toLowerCase()}_close`, label: `${al} Close`,     icon: '~' },
          ];
          return (
            <div key={al} className={`flex items-center gap-1.5 ${gi > 0 ? 'border-l border-pageborder pl-3' : ''}`}>
              {chips.map(ch => {
                const isActive = activeResultFilter === ch.key;
                return (
                  <button
                    key={ch.key}
                    onClick={() => setActiveResultFilter(isActive ? null : ch.key)}
                    className="text-[11px] font-semibold px-2.5 py-1 rounded-full border transition-all duration-150 whitespace-nowrap shrink-0"
                    style={{
                      borderColor: isActive ? color : `${color}55`,
                      background: isActive ? color : 'transparent',
                      color: isActive ? '#fff' : color,
                    }}
                  >
                    {ch.icon} {ch.label}
                  </button>
                );
              })}
            </div>
          );
        })}

        <div className="border-l border-pageborder pl-3 shrink-0">
          <button
            onClick={() => setActiveResultFilter(activeResultFilter === 'close' ? null : 'close')}
            className="text-[11px] font-semibold px-2.5 py-1 rounded-full border transition-all duration-150 whitespace-nowrap"
            style={{
              borderColor: activeResultFilter === 'close' ? '#F59E0B' : '#F59E0B88',
              background: activeResultFilter === 'close' ? '#F59E0B' : 'transparent',
              color: activeResultFilter === 'close' ? '#fff' : '#B45309',
            }}
          >
            ⚡ Close Contests
          </button>
        </div>

        {activeResultFilter && (
          <button
            onClick={() => setActiveResultFilter(null)}
            className="ml-auto shrink-0 text-[11px] text-ink2 hover:text-ink underline"
          >
            Clear
          </button>
        )}
      </div>

      {/* ── CONSTITUENCY CARD GRID ── */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-6 py-4">
        {loadingConst ? (
          <div className="text-center text-ink2 py-16">Loading constituencies...</div>
        ) : filteredConstituencies.length === 0 ? (
          <div className="text-center text-ink2 py-16 text-[14px]">No constituencies match your filters</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '12px' }}>
            {filteredConstituencies.map(c => (
              <ConstituencyCard key={c.id} c={c} onClick={() => navigate(`/constituency/${c.id}`)} />
            ))}
          </div>
        )}
      </div>

      {/* ── BOTTOM TICKER ── */}
      <div className="bg-ink text-white/60 text-[12px] py-2 px-8 flex items-center gap-4 border-t border-white/5 overflow-hidden shrink-0">
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
function ConstituencyCard({ c, onClick }: { c: ConstituencyListItem; onClick: () => void }) {
  const isLive = c.status === 'IN_PROGRESS';
  const isDone = c.status === 'RESULT_DECLARED';
  const countingStarted = isLive || isDone;
  const alliance = c.leader?.alliance || '';
  const color = ALLIANCE_COLORS[alliance] || '#9CA3AF';
  const margin = countingStarted && c.leader && c.runner_up
    ? c.leader.votes - c.runner_up.votes : null;
  const isClose = isLive && margin !== null && margin < 500;

  // All active cards = solid alliance color; awaited = neutral
  const bg = countingStarted ? color : '#E8E4DF';

  // Progress bar: leader vote % * 2 as proxy for counting progress
  const progressPct = isDone ? 100
    : isLive && c.leader ? Math.min(95, Math.max(6, Number(c.leader.percentage) * 2))
    : 0;

  const statusLabel = isDone ? 'WON' : isLive ? 'LEADING' : 'AWAITED';

  return (
    <div
      onClick={onClick}
      className="rounded-md cursor-pointer transition-all duration-150 hover:brightness-110 hover:shadow-lg overflow-hidden"
      style={{
        backgroundColor: bg,
        outline: isClose ? '2px solid #F59E0B' : 'none',
      }}
    >
      <div className="px-3 pt-2.5 pb-2">
        {/* Header: number + status label */}
        <div className="flex items-center justify-between mb-1.5">
          <span
            className="font-mono text-[9px]"
            style={{ color: countingStarted ? 'rgba(255,255,255,0.5)' : '#9CA3AF' }}
          >#{String(c.number).padStart(3, '0')}</span>
          <span
            className="text-[8px] font-bold tracking-wider px-1.5 py-0.5 rounded"
            style={{
              backgroundColor: countingStarted ? 'rgba(0,0,0,0.2)' : '#D1CBC4',
              color: countingStarted ? 'rgba(255,255,255,0.9)' : '#6B7280',
            }}
          >{isClose ? 'CLOSE' : statusLabel}</span>
        </div>

        {/* Constituency name */}
        <div
          className="text-[12px] font-bold leading-tight mb-2 truncate"
          style={{ color: countingStarted ? 'white' : '#333' }}
          title={c.name}
        >{c.name}</div>

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
                style={{ backgroundColor: 'rgba(255,255,255,0.95)', color }}
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
              className="text-[9px] font-medium truncate mb-2"
              style={{ color: 'rgba(255,255,255,0.65)' }}
            >{c.leader.party} · {alliance}</div>

            {/* Runner-up */}
            {c.runner_up && (() => {
              const ruColor = ALLIANCE_COLORS[c.runner_up.alliance] || '#6B7280';
              return (
                <div
                  className="mt-1.5 rounded px-2 py-1 flex items-center gap-1.5 min-w-0"
                  style={{ backgroundColor: 'rgba(255,255,255,0.95)' }}
                >
                  <span className="text-[9px] font-semibold shrink-0" style={{ color: ruColor, opacity: 0.6 }}>2nd</span>
                  <span className="text-[10px] font-semibold truncate" style={{ color: ruColor }} title={c.runner_up.name}>{c.runner_up.name}</span>
                  <span className="text-[10px] font-semibold shrink-0" style={{ color: ruColor, opacity: 0.8 }}>{c.runner_up.party} · {c.runner_up.alliance}</span>
                </div>
              );
            })()}
          </>
        ) : (
          <div className="text-[10px] italic" style={{ color: '#9CA3AF' }}>Counting begins soon</div>
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

