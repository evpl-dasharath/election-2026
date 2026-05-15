import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useConstituencies, useAllHistorical } from '../hooks/useElectionData';
import GlobalHeader from '../components/GlobalHeader';

// ── Design tokens (matching existing codebase) ────────────────
const AC: Record<string, string> = {
  LDF: '#D42B2B', UDF: '#1A8FE3', NDA: '#F7921C', OTH: '#6B7280',
};
const ATAG_BG: Record<string, string> = {
  LDF: '#FEE2E2', UDF: '#DBEAFE', NDA: '#FED7AA', OTH: '#F3F4F6',
};
const ATAG_FG: Record<string, string> = {
  LDF: '#D42B2B', UDF: '#1A8FE3', NDA: '#C2620A', OTH: '#6B7280',
};
function ac(a: string) { return AC[a] || '#6B7280'; }

import { SeatClass, Alliance, classifySeat, ConstituencyHistory, ElectionResult } from '../utils/seatClassification';

// ── Badge component ───────────────────────────────────────────
function ClassBadge({ cls, alliance }: { cls: SeatClass; alliance: Alliance | null }) {
  const color = alliance ? ac(alliance) : '#6B7280';

  // Fragile: hatched background in alliance colour to signal instability
  if (cls === 'Fragile') {
    return (
      <>
        <style>{`
          @keyframes fragile-shimmer {
            0%   { background-position: 0 0; }
            100% { background-position: 20px 20px; }
          }
        `}</style>
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: 5,
          fontSize: 10, fontWeight: 700, letterSpacing: 0.5,
          padding: '2px 8px', borderRadius: 20,
          border: `1.5px solid ${color}`,
          color,
          background: `repeating-linear-gradient(
            45deg,
            ${color}18,
            ${color}18 3px,
            transparent 3px,
            transparent 9px
          )`,
          whiteSpace: 'nowrap',
          animation: 'fragile-shimmer 2.5s linear infinite',
          backgroundSize: '20px 20px',
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, display: 'inline-block', flexShrink: 0, opacity: 0.7 }} />
          Fragile
        </span>
      </>
    );
  }

  let bg: string;
  if (cls === 'Stronghold') bg = color;
  else if (cls === 'Leaning') bg = color + '22';
  else bg = '#F5F2EE';

  const fg = cls === 'Stronghold' ? '#fff' : color;
  const label = cls;

  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      fontSize: 10, fontWeight: 700, letterSpacing: 0.4,
      padding: '2px 8px', borderRadius: 20,
      background: bg, color: fg,
      border: `1px solid ${color}40`,
      whiteSpace: 'nowrap',
    }}>
      {alliance && (
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, display: 'inline-block', flexShrink: 0 }} />
      )}
      {label}
    </span>
  );
}

// ── Result cell ───────────────────────────────────────────────
function ResultCell({ result, is2026 = false, isLiveStatus = false }: { result: ElectionResult | null; is2026?: boolean, isLiveStatus?: boolean }) {
  if (!result) return (
    <td style={{ padding: '12px 14px', color: '#D1D5DB', textAlign: 'center', fontSize: 14 }}>—</td>
  );

  const al = result.winner_alliance || 'OTH';
  const color = ac(al);
  const margin = result.margin;
  const isFragile = margin != null && margin < 2000;
  const LARGE_MARGIN = 20000;

  return (
    <td style={{ padding: '10px 14px', verticalAlign: 'middle' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-start' }}>

        {/* Alliance pill */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 4,
            fontSize: 11, fontWeight: 800, letterSpacing: 0.6,
            padding: '2px 8px', borderRadius: 4,
            background: ATAG_BG[al] || '#F3F4F6',
            color: ATAG_FG[al] || '#6B7280',
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, display: 'inline-block', flexShrink: 0 }} />
            {al}
          </span>
          {/* 2026 live indicator */}
          {is2026 && isLiveStatus && (
            <span style={{ fontSize: 9, color: '#22c55e', fontWeight: 700, letterSpacing: 0.3 }}>● LIVE</span>
          )}
        </div>

        {/* Margin */}
        {margin != null && (
          <span style={{
            fontFamily: "'JetBrains Mono',monospace",
            fontSize: 13,
            fontWeight: 700,
            color: isFragile ? '#DC2626' : margin >= LARGE_MARGIN ? '#16A34A' : '#5C5245',
          }}>
            +{margin.toLocaleString('en-IN')}
          </span>
        )}
      </div>
    </td>
  );
}

// ── Filters ───────────────────────────────────────────────────
type FilterClass = 'all' | 'Stronghold' | 'Fragile' | 'Leaning' | 'Swing';
type FilterAlliance = 'all' | 'LDF' | 'UDF' | 'NDA';

const DISTRICTS = [
  'All Districts',
  'Kasaragod','Kannur','Wayanad','Kozhikode',
  'Malappuram','Palakkad','Thrissur',
  'Ernakulam','Idukki','Kottayam','Alappuzha',
  'Pathanamthitta','Kollam','Thiruvananthapuram',
];

// ── Main Component ────────────────────────────────────────────
export default function HistoryPage() {
  const navigate = useNavigate();

  // Replace with your actual hook — should return all 140 constituencies
  // with la_2011, la_2016, la_2021, la_2026 nested results
  const { data: allHistory, loading } = useAllHistorical();
  const { data: constituencies } = useConstituencies();

  const [searchTerm, setSearchTerm] = useState('');
  const [filterClass, setFilterClass] = useState<FilterClass>('all');
  const [filterAlliance, setFilterAlliance] = useState<FilterAlliance>('all');
  const [filterDistrict, setFilterDistrict] = useState('All Districts');
  const [sortBy, setSortBy] = useState<'number' | 'name' | 'district' | 'margin2021'>('number');
  const [showLS, setShowLS] = useState(false);

  // Merge live 2026 data from constituencies list into history
  const enriched = useMemo(() => {
    if (!allHistory) return [];
    return allHistory.map((h: ConstituencyHistory) => {
      // Find matching constituency for live 2026 data
      const live = constituencies.find(c => c.number === h.constituency_number);
      const la_2026: ElectionResult | null = (live?.status !== 'NOT_STARTED' && live?.leader)
        ? {
            winner: live.leader.name,
            winner_party: live.leader.party.toUpperCase(),
            winner_alliance: live.leader.alliance.toUpperCase(),
            margin: null,
          }
        : null;
      return { ...h, la_2026, _live: live };
    });
  }, [allHistory, constituencies]);

  // Classify all seats
  const classified = useMemo(() => {
    return enriched.map(h => {
      const { seatClass, ownerAlliance } = classifySeat(h);
      return { ...h, seatClass, ownerAlliance };
    });
  }, [enriched]);

  // Apply filters + search + sort
  const filtered = useMemo(() => {
    let rows = classified;

    if (searchTerm) {
      const s = searchTerm.toLowerCase();
      rows = rows.filter(r =>
        r.constituency_name.toLowerCase().includes(s)
      );
    }
    if (filterDistrict !== 'All Districts') {
      rows = rows.filter(r => r.district === filterDistrict);
    }
    if (filterClass !== 'all') {
      rows = rows.filter(r => r.seatClass === filterClass);
    }
    if (filterAlliance !== 'all') {
      rows = rows.filter(r => r.ownerAlliance === filterAlliance);
    }

    // Sort
    return [...rows].sort((a, b) => {
      if (sortBy === 'name') return a.constituency_name.localeCompare(b.constituency_name);
      if (sortBy === 'district') return a.district.localeCompare(b.district) || a.constituency_number - b.constituency_number;
      if (sortBy === 'margin2021') {
        const ma = a.la_2021?.margin ?? -1;
        const mb = b.la_2021?.margin ?? -1;
        return mb - ma;
      }
      return a.constituency_number - b.constituency_number;
    });
  }, [classified, searchTerm, filterDistrict, filterClass, filterAlliance, sortBy]);

  // Summary counts for the filter bar (dynamically updated by other filters)
  const counts = useMemo(() => {
    let rows = classified;

    if (searchTerm) {
      const s = searchTerm.toLowerCase();
      rows = rows.filter(r =>
        r.constituency_name.toLowerCase().includes(s)
      );
    }
    if (filterDistrict !== 'All Districts') {
      rows = rows.filter(r => r.district === filterDistrict);
    }
    if (filterAlliance !== 'all') {
      rows = rows.filter(r => r.ownerAlliance === filterAlliance);
    }

    const c: Record<string, number> = { Stronghold: 0, Fragile: 0, Leaning: 0, Swing: 0, all: rows.length };
    rows.forEach(r => { c[r.seatClass] = (c[r.seatClass] || 0) + 1; });
    return c;
  }, [classified, searchTerm, filterDistrict, filterAlliance]);

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: '#F5F2EE', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ width: 40, height: 40, border: '3px solid #E2DDD8', borderTopColor: '#C8A84B', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto 12px' }} />
          <p style={{ color: '#5C5245', fontFamily: "'DM Sans',sans-serif", fontSize: 13 }}>Loading historical data…</p>
        </div>
        <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      </div>
    );
  }

  return (
    <div style={{ fontFamily: "'DM Sans',sans-serif", background: '#F5F2EE', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <GlobalHeader />

      {/* ── Page header ── */}
      <div className="bg-[#FDFCFB] border-b border-[#E2DDD8] px-4 py-4 md:px-6 md:py-5">
        <div className="max-w-[1400px] mx-auto">
          <h1 className="font-serif text-[22px] md:text-[26px] text-[#1A1611] mb-1 leading-tight">
            Historical Results
          </h1>
          <p className="text-[12px] md:text-[13px] text-[#5C5245] mb-4">
            Post-delimitation window: 2011 · 2016 · 2021 · 2026 — Seat loyalty classification based on 2011–2021 pattern
          </p>

          {/* ── Classification legend ── */}
          <div className="flex flex-wrap gap-2 md:gap-4 mb-4">
            {([
              { cls: 'Stronghold', desc: 'Won all 3 (2011–21), ≥15k margin twice, never <5k', al: 'LDF' },
              { cls: 'Leaning', desc: 'Won all 3 (moderate margins), won last 2, or strong bounce-back', al: 'UDF' },
              { cls: 'Fragile', desc: 'Won all 3 but ≥2 wins were tight (<2,000)', al: 'UDF' },
              { cls: 'Swing', desc: 'Seat changed hands — no clear owner across 3 elections', al: null },
            ] as const).map(({ cls, desc, al }) => (
              <div key={cls} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <ClassBadge cls={cls} alliance={al as Alliance | null} />
                <span style={{ fontSize: 11, color: '#6B7280' }}>{desc}</span>
              </div>
            ))}
          </div>

          {/* ── Filters row ── */}
          <div className="flex flex-col md:flex-row gap-3 md:gap-2 flex-wrap items-stretch md:items-center">

            {/* Search */}
            <div className="flex items-center gap-2 bg-[#F5F2EE] border border-[#E2DDD8] rounded-md px-3 py-1.5 w-full md:w-[180px] shrink-0 focus-within:border-ink transition-colors">
              <span className="text-[#5C5245] text-sm" aria-hidden="true">⌕</span>
              <input
                type="text"
                aria-label="Search constituency"
                placeholder="Search constituency…"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="border-none bg-transparent outline-none font-sans text-[12px] text-[#1A1611] w-full"
              />
            </div>

            {/* District filter */}
            <select
              value={filterDistrict}
              onChange={e => setFilterDistrict(e.target.value)}
              className="text-[12px] px-3 py-1.5 rounded-md border border-[#E2DDD8] bg-[#F5F2EE] text-[#1A1611] font-sans cursor-pointer w-full md:w-auto shrink-0"
            >
              {DISTRICTS.map(d => <option key={d} value={d}>{d}</option>)}
            </select>

            {/* Seat class filter */}
            <div className="flex gap-1.5 overflow-x-auto custom-scrollbar pb-1 md:pb-0 w-full md:w-auto shrink-0">
              {(['all', 'Stronghold', 'Leaning', 'Fragile', 'Swing'] as FilterClass[]).map(f => {
                const active = filterClass === f;
                const count = counts[f] || 0;
                return (
                  <button
                    key={f}
                    onClick={() => setFilterClass(f)}
                    style={{
                      fontSize: 11, fontWeight: 600, padding: '4px 10px', borderRadius: 20, cursor: 'pointer',
                      fontFamily: "'DM Sans',sans-serif",
                      border: `1.5px solid ${active ? '#1A1611' : '#D1CBC4'}`,
                      background: active ? '#1A1611' : 'transparent',
                      color: active ? '#fff' : '#5C5245',
                      transition: 'all 0.15s',
                    }}
                  >
                    {f === 'all' ? `All (${count})` : `${f} (${count})`}
                  </button>
                );
              })}
            </div>

            {/* Alliance filter */}
            <div className="flex gap-1.5 overflow-x-auto custom-scrollbar pb-1 md:pb-0 w-full md:w-auto shrink-0">
              {(['all', 'LDF', 'UDF', 'NDA'] as FilterAlliance[]).map(f => {
                const active = filterAlliance === f;
                const color = f === 'all' ? '#1A1611' : ac(f);
                return (
                  <button
                    key={f}
                    onClick={() => setFilterAlliance(f)}
                    style={{
                      fontSize: 11, fontWeight: 600, padding: '4px 10px', borderRadius: 20, cursor: 'pointer',
                      fontFamily: "'DM Sans',sans-serif",
                      border: `1.5px solid ${active ? color : '#D1CBC4'}`,
                      background: active ? color : 'transparent',
                      color: active ? '#fff' : color,
                      transition: 'all 0.15s',
                    }}
                  >
                    {f === 'all' ? 'All alliances' : f}
                  </button>
                );
              })}
            </div>

            {/* View toggle */}
            <div className="mt-2 md:mt-0 md:ml-auto flex items-center w-full md:w-auto">
              <label className="flex items-center gap-1.5 cursor-pointer text-[12px] text-[#5C5245] font-sans font-semibold">
                <input
                  type="checkbox"
                  checked={showLS}
                  onChange={e => setShowLS(e.target.checked)}
                  className="cursor-pointer accent-[#1A1611]"
                />
                Show LS (2019/2024)
              </label>
            </div>
            </div>
        </div>
      </div>

      {/* ── Table ── */}
      <div className="flex-1 overflow-x-auto custom-scrollbar pb-10">
        <div className="max-w-[1400px] mx-auto min-w-[900px]">

          <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed' }}>
            <colgroup>
              <col style={{ width: 44 }} />   {/* # */}
              <col style={{ width: 150 }} />  {/* Constituency */}
              <col style={{ width: 90 }} />   {/* District */}
              <col style={{ width: 120 }} />  {/* 2011 */}
              <col style={{ width: 120 }} />  {/* 2016 */}
              {showLS && <col style={{ width: 120 }} />}  {/* LS 2019 */}
              <col style={{ width: 120 }} />  {/* 2021 */}
              {showLS && <col style={{ width: 120 }} />}  {/* LS 2024 */}
              <col style={{ width: 120 }} />  {/* 2026 */}
              <col style={{ width: 120 }} />  {/* Classification */}
              <col style={{ width: 100 }} />  {/* Shift */}
            </colgroup>

            <thead>
              <tr style={{ background: '#F5F2EE', position: 'sticky', top: 0, zIndex: 10 }}>
                {/* # */}
                <th
                  onClick={() => setSortBy('number')}
                  style={{ ...thStyle, textAlign: 'left', paddingLeft: 16, cursor: 'pointer', color: sortBy === 'number' ? '#1A1611' : '#5C5245' }}
                >
                  # {sortBy === 'number' && <span style={{ fontSize: 9 }}>▼</span>}
                </th>
                {/* Constituency */}
                <th
                  onClick={() => setSortBy('name')}
                  style={{ ...thStyle, textAlign: 'left', cursor: 'pointer', color: sortBy === 'name' ? '#1A1611' : '#5C5245' }}
                >
                  Constituency {sortBy === 'name' && <span style={{ fontSize: 9 }}>▼</span>}
                </th>
                {/* District */}
                <th
                  onClick={() => setSortBy('district')}
                  style={{ ...thStyle, textAlign: 'left', cursor: 'pointer', color: sortBy === 'district' ? '#1A1611' : '#5C5245' }}
                >
                  District {sortBy === 'district' && <span style={{ fontSize: 9 }}>▼</span>}
                </th>
                <th style={{ ...thStyle }}>
                  <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: 1.5 }}>2011</span><br />
                  <span style={{ fontSize: 9, fontWeight: 400, color: '#9CA3AF', letterSpacing: 0.3 }}>LA Election</span>
                </th>
                <th style={{ ...thStyle }}>
                  <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: 1.5 }}>2016</span><br />
                  <span style={{ fontSize: 9, fontWeight: 400, color: '#9CA3AF', letterSpacing: 0.3 }}>LA Election</span>
                </th>
                {showLS && (
                  <th style={{ ...thStyle, background: '#EFF6FF' }}>
                    <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: 1.5, color: '#1E40AF' }}>2019</span><br />
                    <span style={{ fontSize: 9, fontWeight: 400, color: '#60A5FA', letterSpacing: 0.3 }}>LS Segment</span>
                  </th>
                )}
                <th style={{ ...thStyle }}>
                  <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: 1.5 }}>2021</span><br />
                  <span style={{ fontSize: 9, fontWeight: 400, color: '#9CA3AF', letterSpacing: 0.3 }}>LA Election</span>
                </th>
                {showLS && (
                  <th style={{ ...thStyle, background: '#EFF6FF' }}>
                    <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: 1.5, color: '#1E40AF' }}>2024</span><br />
                    <span style={{ fontSize: 9, fontWeight: 400, color: '#60A5FA', letterSpacing: 0.3 }}>LS Segment</span>
                  </th>
                )}
                <th style={{ ...thStyle }}>
                  <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: 1.5, color: '#22c55e' }}>2026</span>
                  <br />
                  <span style={{ fontSize: 9, fontWeight: 400, color: '#9CA3AF', letterSpacing: 0.3 }}>Live / Final</span>
                </th>
                {/* Classification */}
                <th
                  style={{ ...thStyle, textAlign: 'center' }}
                >
                  Seat Profile
                </th>
                <th style={{ ...thStyle }}>
                  <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: 1.5 }}>Shift</span><br />
                  <span style={{ fontSize: 9, fontWeight: 400, color: '#9CA3AF', letterSpacing: 0.3 }}>2021 vs 26</span>
                </th>
              </tr>
            </thead>

            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={10} style={{ padding: 48, textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>
                    No constituencies match the current filters
                  </td>
                </tr>
              ) : filtered.map((row, i) => {
                const isEven = i % 2 === 0;
                const rowBg = isEven ? '#FDFCFB' : '#F9F7F4';
                // Color the row left border by the owning alliance
                const borderColor = row.ownerAlliance ? ac(row.ownerAlliance) : '#E2DDD8';

                return (
                  <tr
                    key={row.constituency_number}
                    onClick={() => {
                      const match = constituencies.find(c => c.number === row.constituency_number);
                      if (match) navigate(`/constituency/${match.id}`);
                    }}
                    style={{
                      background: rowBg,
                      borderBottom: '1px solid #E2DDD8',
                      borderLeft: `3px solid ${borderColor}`,
                      cursor: 'pointer',
                      transition: 'background 0.1s',
                    }}
                    onMouseEnter={e => (e.currentTarget as HTMLTableRowElement).style.background = '#EEF4FB'}
                    onMouseLeave={e => (e.currentTarget as HTMLTableRowElement).style.background = rowBg}
                  >
                    {/* # */}
                    <td style={{ padding: '10px 8px 10px 16px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: '#9CA3AF' }}>
                      {String(row.constituency_number).padStart(3, '0')}
                    </td>

                    {/* Constituency name */}
                    <td style={{ padding: '10px 14px' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-start' }}>
                        <span style={{ fontSize: 14, fontWeight: 600, color: '#1A1611' }}>
                          {row.constituency_name}
                        </span>
                        {row.la_2021?.winner_alliance && (
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 3, border: `1px solid ${ac(row.la_2021.winner_alliance)}40`, borderRadius: 12, padding: '1px 6px' }}>
                            <div style={{ width: 5, height: 5, borderRadius: '50%', background: ac(row.la_2021.winner_alliance), flexShrink: 0 }} />
                            <span style={{ fontSize: 9, fontWeight: 700, color: ac(row.la_2021.winner_alliance) }}>{row.la_2021.winner_alliance}</span>
                            <span style={{ fontSize: 9, color: '#9CA3AF' }}>seat (2021)</span>
                          </div>
                        )}
                      </div>
                    </td>

                    {/* District */}
                    <td style={{ padding: '10px 14px', fontSize: 13, color: '#5C5245' }}>
                      {row.district}
                    </td>

                    {/* 2011 */}
                    <ResultCell result={row.la_2011} />

                    {/* 2016 */}
                    <ResultCell result={row.la_2016} />

                    {/* LS 2019 */}
                    {showLS && <ResultCell result={row.ls_2019 || null} />}

                    {/* 2021 */}
                    <ResultCell result={row.la_2021} />

                    {/* LS 2024 */}
                    {showLS && <ResultCell result={row.ls_2024 || null} />}

                    {/* 2026 */}
                    <ResultCell result={row.la_2026} is2026 isLiveStatus={row._live?.status !== 'RESULT_DECLARED'} />

                    {/* Classification */}
                    <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                      <ClassBadge cls={row.seatClass} alliance={row.ownerAlliance} />
                      {/* Wave annotation for 2011 — LDF win against UDF wave */}
                      {row.la_2011?.winner_alliance && row.ownerAlliance &&
                        row.la_2011.winner_alliance === row.ownerAlliance &&
                        row.ownerAlliance !== 'UDF' && (
                        <div style={{ fontSize: 9, color: '#9CA3AF', marginTop: 4, lineHeight: 1.2 }}>
                          ↑ vs '11 UDF wave
                        </div>
                      )}
                    </td>

                    {/* Shift */}
                    <td style={{ padding: '10px 14px', verticalAlign: 'middle' }}>
                      {(() => {
                        const liveStatus = row._live?.status;
                        const curr = row.la_2026?.winner_alliance;
                        if (liveStatus !== 'RESULT_DECLARED' && !(liveStatus === 'IN_PROGRESS' && curr)) return <span style={{ color: '#D1D5DB', fontSize: 14 }}>—</span>;
                        
                        const prev = row.la_2021?.winner_alliance || 'OTH';
                        const currAlliance = curr || 'OTH';
                        
                        if (prev === currAlliance) {
                          return (
                            <span style={{
                              display: 'inline-flex', alignItems: 'center', gap: 4,
                              fontSize: 10, fontWeight: 700, letterSpacing: 0.5,
                              padding: '2px 6px', borderRadius: 4,
                              background: '#F3F4F6', color: '#4B5563',
                              border: '1px solid #E5E7EB'
                            }}>
                              HOLD
                            </span>
                          );
                        } else {
                          return (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                              <span style={{
                                fontSize: 10, fontWeight: 800, letterSpacing: 0.5,
                                color: '#1A1611'
                              }}>
                                SWING
                              </span>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, fontWeight: 700 }}>
                                <span style={{ color: ac(prev) }}>{prev}</span>
                                <span style={{ color: '#9CA3AF', fontSize: 9 }}>→</span>
                                <span style={{ color: ac(currAlliance) }}>{currAlliance}</span>
                              </div>
                            </div>
                          );
                        }
                      })()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {/* Row count */}
          <div style={{ padding: '12px 16px', fontSize: 12, color: '#9CA3AF', textAlign: 'right', borderTop: '1px solid #E2DDD8', background: '#F5F2EE' }}>
            Showing {filtered.length} of {classified.length} constituencies
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Shared table header style ─────────────────────────────────
const thStyle: React.CSSProperties = {
  padding: '10px 12px',
  fontSize: 10,
  fontWeight: 700,
  letterSpacing: '1.2px',
  textTransform: 'uppercase',
  color: '#5C5245',
  background: '#F5F2EE',
  borderBottom: '2px solid #E2DDD8',
  textAlign: 'left',
  userSelect: 'none',
};
