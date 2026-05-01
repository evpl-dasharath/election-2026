import { useState, useMemo, useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  useConstituencies,
  useConstituencyDetail,
  useHistoricalComparison,
  useStateSummary,
  prefetchConstituencyDetail,
} from '../hooks/useElectionData';
import GlobalHeader from '../components/GlobalHeader';
import { partyAbbr } from '../utils/partyAbbr';

// ── Design tokens ─────────────────────────────────────────────
const AC: Record<string, string> = {
  LDF: '#D42B2B', UDF: '#1A8FE3', NDA: '#F7921C', OTH: '#6B7280',
};
const ABG: Record<string, string> = {
  LDF: 'rgba(212,43,43,0.08)', UDF: 'rgba(26,143,227,0.08)',
  NDA: 'rgba(247,146,28,0.08)', OTH: 'rgba(107,114,128,0.06)',
};
const ATAG_BG: Record<string, string> = {
  LDF: '#FEE2E2', UDF: '#DBEAFE', NDA: '#FED7AA', OTH: '#F3F4F6',
};
const ATAG_FG: Record<string, string> = {
  LDF: '#D42B2B', UDF: '#1A8FE3', NDA: '#C2620A', OTH: '#6B7280',
};
function ac(a: string) { return AC[a] || '#6B7280'; }
/** Badge/dot color: alliance color for LDF/UDF/NDA; party-specific color for OTH non-IND; grey for IND */
function badgeColor(alliance: string, party: string, colorCode?: string) {
  if (alliance !== 'OTH') return ac(alliance);
  if (party === 'IND' || party === 'NOTA') return '#9CA3AF';
  return colorCode || '#6B7280';
}

// ── Helpers ───────────────────────────────────────────────────
function sLabel(s: string) {
  if (s === 'RESULT_DECLARED') return 'Declared';
  if (s === 'IN_PROGRESS') return 'Counting';
  return 'Awaited';
}
function sDotColor(s: string) {
  if (s === 'RESULT_DECLARED') return '#6B7280';
  if (s === 'IN_PROGRESS') return '#22c55e';
  return '#D1D5DB';
}
function cPct(live: { rounds_completed: number; total_rounds: number } | null | undefined) {
  if (!live || live.total_rounds === 0) return 0;
  return Math.round((live.rounds_completed / live.total_rounds) * 100);
}
function rLabel(live: { rounds_completed: number; total_rounds: number; status: string } | null | undefined) {
  if (!live) return 'Awaited';
  if (live.status === 'COMPLETED') return 'All rounds complete';
  if (live.status === 'NOT_STARTED') return 'Not started';
  return `Round ${live.rounds_completed} of ${live.total_rounds}`;
}
function isDepositLost(votes: number, totalValid: number) {
  return totalValid > 0 && votes < totalValid / 6;
}
function inferAlliance(party: string): string {
  const p = party.toUpperCase();
  if (/CPM|CPI|LDF|RSP/.test(p)) return 'LDF';
  if (/INC|IUML|KERALA.CONGRESS|KC\(|UDF/.test(p)) return 'UDF';
  if (/BJP|BDJS|NDA/.test(p)) return 'NDA';
  return 'OTH';
}


// ─────────────────────────────────────────────────────────────
export default function ConstituencyPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const constituencyId = id ? parseInt(id) : null;

  const { data: summary } = useStateSummary();
  const { data: allConst, loading: allLoading } = useConstituencies();
  const { data: constituency, loading } = useConstituencyDetail(constituencyId);
  const { data: historical, loading: histLoading } = useHistoricalComparison(
    constituency?.constituency.number || null
  );

  const [search, setSearch] = useState('');
  const [allianceFilter, setAllianceFilter] = useState<string>('all');
  const [parliamentOpen, setParliamentOpen] = useState(false);

  // Sidebar list
  const sidebarList = useMemo(() => {
    return allConst.filter(c => {
      if (allianceFilter !== 'all' && c.leader?.alliance !== allianceFilter) return false;
      if (search) {
        const s = search.toLowerCase();
        return c.name.toLowerCase().includes(s) || c.district.toLowerCase().includes(s);
      }
      return true;
    });
  }, [allConst, allianceFilter, search]);

  // Prev / next
  const sorted = useMemo(() => [...allConst].sort((a, b) => a.number - b.number), [allConst]);
  const idx = sorted.findIndex(c => c.id === constituencyId);
  const prevC = idx > 0 ? sorted[idx - 1] : null;
  const nextC = idx < sorted.length - 1 ? sorted[idx + 1] : null;

  // Slim header totals
  const ldf = summary ? summary.alliance_summary.LDF.won + summary.alliance_summary.LDF.leading : 0;
  const udf = summary ? summary.alliance_summary.UDF.won + summary.alliance_summary.UDF.leading : 0;
  const nda = summary ? summary.alliance_summary.NDA.won + summary.alliance_summary.NDA.leading : 0;

  // Derive these safely before early returns so hook order is stable
  const candidates_2026_safe = constituency?.candidates_2026 ?? [];

  // Swing — must be before any early return (Rules of Hooks)
  const swingData = useMemo(() => {
    if (!historical?.la_2021 || candidates_2026_safe.length === 0) return null;
    const has2016 = !!(historical.la_2016?.alliance_shares);
    return (['LDF', 'UDF', 'NDA', 'OTH'] as const).map(al => {
      const v26raw = candidates_2026_safe.filter(cd => cd.alliance === al).reduce((s, cd) => s + cd.percentage, 0);
      const v21raw = historical.la_2021.alliance_shares?.[al] ?? 0;
      const v16raw = has2016 ? (historical.la_2016!.alliance_shares?.[al] ?? 0) : null;
      const swing2126 = v26raw - v21raw;
      const swing1621 = v16raw !== null ? v21raw - v16raw : null;
      return { alliance: al, v16: v16raw, v21: v21raw, v26: v26raw, swing2126, swing1621, has2016 };
    });
  }, [historical, candidates_2026_safe]);

  // ── Background prefetch ────────────────────────────────────────────────────
  // Prefetch next constituency immediately; then prefetch all others quietly.
  useEffect(() => {
    if (!allConst.length || !constituencyId) return;

    const sortedAll = [...allConst].sort((a, b) => a.number - b.number);
    const curIdx = sortedAll.findIndex(c => c.id === constituencyId);
    const nextId = curIdx < sortedAll.length - 1 ? sortedAll[curIdx + 1].id : null;
    const prevId = curIdx > 0 ? sortedAll[curIdx - 1].id : null;

    // Prefetch immediate neighbours right away
    if (nextId) prefetchConstituencyDetail(nextId);
    if (prevId) prefetchConstituencyDetail(prevId);

    // Then prefetch all others in the background with a small throttle
    let cancelled = false;
    const timer = setTimeout(async () => {
      for (const c of sortedAll) {
        if (cancelled) break;
        if (c.id === constituencyId || c.id === nextId || c.id === prevId) continue;
        await prefetchConstituencyDetail(c.id);
        if (!cancelled) await new Promise(r => setTimeout(r, 80));
      }
    }, 800); // start after 800ms so current page paint is never delayed

    return () => { cancelled = true; clearTimeout(timer); };
  }, [constituencyId, allConst]);

  // Loading
  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: '#F5F2EE', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ width: 40, height: 40, border: '3px solid #E2DDD8', borderTopColor: '#C8A84B', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto 12px' }} />
          <p style={{ color: '#5C5245', fontFamily: "'DM Sans',sans-serif", fontSize: 13 }}>Loading constituency…</p>
        </div>
        <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      </div>
    );
  }
  if (!constituency) {
    return (
      <div style={{ minHeight: '100vh', background: '#F5F2EE', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <p style={{ color: '#5C5245', fontFamily: "'DM Sans',sans-serif" }}>Constituency not found</p>
          <Link to="/" style={{ color: '#1A8FE3', fontSize: 13, display: 'inline-block', marginTop: 12 }}>← Back</Link>
        </div>
      </div>
    );
  }

  const { constituency: c, candidates_2026, live_result } = constituency;
  const pct = cPct(live_result);
  const totalValid = live_result?.valid_votes || 0;
  const maxVotes = candidates_2026_safe.length > 0 ? Math.max(...candidates_2026_safe.map(cd => cd.votes)) : 1;

  const countingStarted = live_result && live_result.status !== 'NOT_STARTED';
  // Only derive a leader once counting has actually begun — no fallback to [0]
  const leader = countingStarted
    ? (candidates_2026_safe.find(cd => cd.is_winner) || candidates_2026_safe.find(cd => cd.is_leading) || null)
    : null;
  const runnerUp = leader ? candidates_2026_safe.filter(cd => cd !== leader)[0] : null;
  const margin = leader && runnerUp ? leader.votes - runnerUp.votes : null;

  const hasSwing = swingData && swingData.some(s => s.v21 > 0.05);
  // 2026 vote-share data only shown once counting is fully declared
  const is2026Final = live_result?.status === 'RESULT_DECLARED';

  // ── Sitting-MLA & vote-delta helpers (need historical context) ──
  const normName = (s: string) => s.toLowerCase().replace(/[^a-z]/g, '');
  const isSittingMla = (candidateName: string): boolean => {
    if (!historical?.la_2021?.winner) return false;
    const cn = normName(candidateName);
    const sn = normName(historical.la_2021.winner);
    if (cn === sn) return true;
    // Tolerate minor spelling variants: match first 4 chars AND last 4 chars
    if (cn.length >= 6 && sn.length >= 6) {
      return cn.slice(0, 4) === sn.slice(0, 4) && cn.slice(-4) === sn.slice(-4);
    }
    return cn.slice(0, Math.min(cn.length, sn.length)) === sn.slice(0, Math.min(cn.length, sn.length));
  };
  const get2021Pct = (candidateName: string): number | null => {
    if (!historical?.la_2021?.candidates?.length) return null;
    const cn = normName(candidateName);
    const found = historical.la_2021.candidates.find(r => {
      const rn = normName(r.candidate);
      if (cn.length < 5 || rn.length < 5) return cn === rn;
      const pfx = Math.min(cn.length, rn.length, 8);
      return cn.slice(0, pfx) === rn.slice(0, pfx);
    });
    return found ? found.percentage : null;
  };

  return (
    <div style={{ fontFamily: "'DM Sans',sans-serif", background: '#F5F2EE', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>

      <GlobalHeader />

      {/* ── BODY ─────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '300px 1fr', minHeight: 0 }}>

        {/* ══ SIDEBAR ══════════════════════════════════════════ */}
        <div style={{ background: '#FDFCFB', borderRight: '1px solid #E2DDD8', display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'sticky', top: 56, height: 'calc(100vh - 56px)' }}>

          {/* Toolbar */}
          <div style={{ padding: '12px 14px', borderBottom: '1px solid #E2DDD8', flexShrink: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: '#F5F2EE', border: '1px solid #E2DDD8', borderRadius: 7, padding: '7px 11px', marginBottom: 10 }}>
              <span style={{ color: '#5C5245', fontSize: 14 }}>⌕</span>
              <input
                type="text"
                placeholder="Search constituency…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{ border: 'none', background: 'none', outline: 'none', fontFamily: "'DM Sans',sans-serif", fontSize: 13, color: '#1A1611', width: '100%' }}
              />
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {(['all', 'LDF', 'UDF', 'NDA'] as const).map(f => {
                const active = allianceFilter === f;
                const color = f === 'all' ? '#1A1611' : ac(f);
                return (
                  <button key={f} onClick={() => setAllianceFilter(f)} style={{ fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 20, cursor: 'pointer', fontFamily: "'DM Sans',sans-serif", border: `1.5px solid ${color}`, background: active ? color : 'transparent', color: active ? '#fff' : color, transition: 'all 0.15s' }}>
                    {f === 'all' ? `All ${allConst.length}` : f}
                  </button>
                );
              })}
            </div>
          </div>

          {/* List */}
          <div style={{ overflowY: 'auto', flex: 1 }}
            // Custom scrollbar via inline is not possible; handled via global CSS or Tailwind
          >
            {allLoading ? (
              <div style={{ padding: 24, textAlign: 'center', color: '#5C5245', fontSize: 13 }}>Loading…</div>
            ) : sidebarList.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', color: '#5C5245', fontSize: 13 }}>No results</div>
            ) : (
              sidebarList.map(ci => {
                const isActive = ci.id === constituencyId;
                const la = ci.leader?.alliance || 'OTH';
                return (
                  <div
                    key={ci.id}
                    onClick={() => navigate(`/constituency/${ci.id}`)}
                    style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '11px 14px', cursor: 'pointer', borderBottom: '1px solid #E2DDD8', background: isActive ? (ABG[la] || '#EEF6FF') : 'transparent', borderLeft: isActive ? `3px solid ${ac(la)}` : '3px solid transparent', transition: 'background 0.12s' }}
                    onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLDivElement).style.background = '#F5F2EE'; }}
                    onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLDivElement).style.background = 'transparent'; }}
                  >
                    <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, color: '#5C5245', width: 22, flexShrink: 0 }}>
                      {String(ci.number).padStart(3, '0')}
                    </span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: isActive ? 700 : 600, color: '#1A1611', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginBottom: 2 }}>{ci.name}</div>
                      <div style={{ fontSize: 11, color: '#5C5245' }}>{ci.district}</div>
                    </div>
                    <div style={{ textAlign: 'right', flexShrink: 0 }}>
                      {ci.leader && (
                        <div style={{ fontSize: 11, fontWeight: 700, padding: '2px 6px', borderRadius: 4, display: 'inline-block', marginBottom: 3, background: ATAG_BG[ci.leader.alliance] || '#F3F4F6', color: ATAG_FG[ci.leader.alliance] || '#6B7280' }}>
                          {ci.leader.party}
                        </div>
                      )}
                      <div style={{ fontSize: 10, color: '#5C5245', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 3 }}>
                        <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: sDotColor(ci.status), ...(ci.status === 'IN_PROGRESS' ? { animation: 'pulse 1.5s ease-in-out infinite' } : {}) }} />
                        {sLabel(ci.status)}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ══ MAIN CONTENT ═════════════════════════════════════ */}
        <div style={{ overflowY: 'auto', background: '#F5F2EE' }}>

          {/* ── HERO ──────────────────────────────────────────── */}
          <div style={{ background: leader ? (ABG[leader.alliance] || '#FDFCFB') : '#FDFCFB', borderBottom: `3px solid ${leader ? ac(leader.alliance) : '#E2DDD8'}`, padding: '24px 32px' }}>

            {/* Inline prev / next nav */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              {prevC ? (
                <button onClick={() => navigate(`/constituency/${prevC.id}`)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5, color: '#5C5245', fontSize: 12, fontFamily: "'DM Sans',sans-serif", padding: '4px 0' }}>
                  <span style={{ fontSize: 15 }}>←</span>
                  <span style={{ fontWeight: 600 }}>{prevC.name}</span>
                  <span style={{ color: '#9CA3AF', fontSize: 11 }}>{prevC.district}</span>
                </button>
              ) : <div />}
              {nextC ? (
                <button onClick={() => navigate(`/constituency/${nextC.id}`)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5, color: '#5C5245', fontSize: 12, fontFamily: "'DM Sans',sans-serif", padding: '4px 0' }}>
                  <span style={{ color: '#9CA3AF', fontSize: 11 }}>{nextC.district}</span>
                  <span style={{ fontWeight: 600 }}>{nextC.name}</span>
                  <span style={{ fontSize: 15 }}>→</span>
                </button>
              ) : <div />}
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18 }}>
              <div>
                <div style={{ fontFamily: "'DM Serif Display',serif", fontSize: 30, letterSpacing: '-0.4px', color: '#1A1611', lineHeight: 1.15, marginBottom: 8 }}>{c.name}</div>
                <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap' }}>
                  <MetaChip>{c.district} District</MetaChip>
                  <MetaChip># {c.number}</MetaChip>
                  {live_result && (
                    <MetaChip>
                      <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: sDotColor(live_result.status), marginRight: 5, verticalAlign: 'middle', ...(live_result.status === 'IN_PROGRESS' ? { animation: 'pulse 1.5s infinite' } : {}) }} />
                      {sLabel(live_result.status)}
                    </MetaChip>
                  )}
                </div>
                {/* Seat alliance pill */}
                {!histLoading && historical?.la_2021 && (() => {
                  // Use the candidates winner's alliance (from PartyAllianceYear — correctly maps INL→LDF etc.)
                  const sittingAlliance = historical.la_2021.candidates?.find(r => r.is_winner)?.alliance
                    ?? historical.la_2021.candidates?.[0]?.alliance
                    ?? null;
                  if (!sittingAlliance) return null;
                  const alColor = ac(sittingAlliance);
                  return (
                    <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 5, background: 'rgba(255,255,255,0.75)', border: `1px solid ${alColor}40`, borderRadius: 20, padding: '3px 10px' }}>
                        <div style={{ width: 7, height: 7, borderRadius: '50%', background: alColor, flexShrink: 0 }} />
                        <span style={{ fontSize: 11, fontWeight: 700, color: alColor }}>{sittingAlliance}</span>
                        <span style={{ fontSize: 10, color: '#5C5245' }}>seat (2021)</span>
                      </div>
                    </div>
                  );
                })()}
              </div>
              {live_result && (
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <div style={{ fontFamily: "'DM Serif Display',serif", fontSize: 40, color: '#1A1611', lineHeight: 1 }}>{pct}%</div>
                  <div style={{ fontSize: 11, color: '#5C5245', marginTop: 2 }}>votes counted</div>
                  <div style={{ width: 140, height: 5, background: '#E2DDD8', borderRadius: 3, overflow: 'hidden', marginTop: 8, marginLeft: 'auto' }}>
                    <div style={{ height: '100%', width: `${pct}%`, background: '#22c55e', borderRadius: 3, transition: 'width 0.8s ease' }} />
                  </div>
                  <div style={{ fontSize: 11, color: '#5C5245', marginTop: 5 }}>{rLabel(live_result)}</div>
                </div>
              )}
            </div>

            {/* Leader callout */}
            {leader && (
              <div style={{ background: 'rgba(255,255,255,0.75)', border: `1.5px solid ${ac(leader.alliance)}`, borderRadius: 10, padding: '16px 20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16 }}>
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 2, textTransform: 'uppercase', color: '#5C5245', marginBottom: 5 }}>
                      {leader.is_winner ? '✓ Winner' : '▲ Leading'}
                    </div>
                    <div style={{ fontFamily: "'DM Serif Display',serif", fontSize: 24, color: '#1A1611', marginBottom: 6 }}>{leader.name}</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', fontSize: 13, color: '#5C5245' }}>
                      <span style={{ background: ATAG_BG[leader.alliance], color: ATAG_FG[leader.alliance], fontWeight: 700, fontSize: 11, padding: '2px 7px', borderRadius: 4 }}>{leader.alliance}</span>
                      <span>{leader.party}</span>
                      {(leader as any).is_incumbent && <Badge bg="#854D0E">Incumbent</Badge>}
                    </div>
                    {runnerUp && (
                      <div style={{ marginTop: 8, fontSize: 12, color: '#5C5245' }}>
                        vs <span style={{ fontWeight: 600, color: '#1A1611' }}>{runnerUp.name}</span>
                        <span style={{ marginLeft: 6, fontSize: 11, color: ac(runnerUp.alliance) }}>{runnerUp.alliance} · {runnerUp.party}</span>
                      </div>
                    )}
                  </div>
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 30, fontWeight: 600, color: ac(leader.alliance), letterSpacing: '-1px' }}>{leader.votes.toLocaleString('en-IN')}</div>
                    <div style={{ fontSize: 11, color: '#5C5245' }}>{leader.percentage.toFixed(1)}% of votes</div>
                    {margin !== null && (
                      <div style={{ marginTop: 6 }}>
                        <div style={{ fontSize: 22, fontWeight: 800, fontFamily: "'JetBrains Mono',monospace", color: ac(leader.alliance), letterSpacing: '-1px', lineHeight: 1 }}>+{margin.toLocaleString('en-IN')}</div>
                        <div style={{ fontSize: 10, color: '#9CA3AF', marginTop: 2 }}>margin</div>
                      </div>
                    )}
                    {(live_result as any)?.last_updated && (
                      <div style={{ fontSize: 10, color: '#9CA3AF', marginTop: 6 }}>
                        Updated {new Date((live_result as any).last_updated).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })} IST
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* ── COUNTING STATS ────────────────────────────────── */}
          {live_result && (
            <div style={{ background: '#FDFCFB', borderBottom: '1px solid #E2DDD8', padding: '13px 32px', display: 'flex', gap: 28, flexWrap: 'wrap' }}>
              {([['Total Electors', live_result.total_electors], ['Votes Polled', live_result.votes_polled], ['Votes Counted', live_result.votes_counted], ['Valid Votes', live_result.valid_votes]] as [string, number][]).map(([label, value]) => (
                <div key={label}>
                  <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#5C5245', marginBottom: 2 }}>{label}</div>
                  <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 15, fontWeight: 600, color: '#1A1611' }}>{value.toLocaleString('en-IN')}</div>
                </div>
              ))}
            </div>
          )}

          {/* ── CANDIDATE RESULTS ─────────────────────────────── */}
          <div style={{ padding: '22px 32px' }}>
            <SectionTitle>Current Results</SectionTitle>
            {candidates_2026.length === 0 ? (
              <p style={{ color: '#5C5245', fontSize: 13 }}>No candidate data available yet</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {candidates_2026.map((cd, i) => {
                  const color = badgeColor(cd.alliance, cd.party, cd.party_color);
                  const isTop = cd.is_winner || cd.is_leading;
                  const barW = maxVotes > 0 ? Math.round((cd.votes / maxVotes) * 100) : 0;
                  const abbr = partyAbbr(cd.party);
                  const isIncumbent = isSittingMla(cd.name);
                  return (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '13px 15px', background: isTop ? (ABG[cd.alliance] || '#FDFCFB') : '#FDFCFB', borderRadius: 10, border: `1.5px solid ${isTop ? color : '#E2DDD8'}` }}>
                      <div style={{ width: 38, height: 38, borderRadius: '50%', background: color, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 700, color: '#fff', flexShrink: 0 }}>{abbr}</div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 14, fontWeight: 600, color: '#1A1611', display: 'flex', alignItems: 'center', gap: 7, flexWrap: 'wrap' }}>
                          {cd.name}
                          {cd.is_winner && <Badge bg="#15803D">✓ Winner</Badge>}
                          {cd.is_leading && !cd.is_winner && <Badge bg="#1D4ED8">▲ Leading</Badge>}
                          {isIncumbent && <Badge bg="#854D0E">Sitting MLA</Badge>}
                        </div>
                        <div style={{ fontSize: 11, color: '#5C5245', marginTop: 2 }}>{cd.party} · {cd.alliance}</div>
                      </div>
                      <div style={{ flex: 1, maxWidth: 180 }}>
                        <div style={{ fontSize: 10, color: '#5C5245', marginBottom: 3, fontFamily: "'JetBrains Mono',monospace", display: 'flex', alignItems: 'center', gap: 4 }}>
                          {cd.percentage.toFixed(1)}%
                          {live_result?.status === 'RESULT_DECLARED' && (() => {
                            const pct21 = get2021Pct(cd.name);
                            if (pct21 === null) return null;
                            const delta = cd.percentage - pct21;
                            return <span style={{ fontSize: 9, fontWeight: 700, color: delta >= 0 ? '#16A34A' : '#DC2626' }}>{delta >= 0 ? '▲' : '▼'}{Math.abs(delta).toFixed(1)}</span>;
                          })()}
                        </div>
                        <div style={{ height: 6, background: '#E2DDD8', borderRadius: 3, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${barW}%`, background: color, borderRadius: 3, transition: 'width 0.8s ease' }} />
                        </div>
                      </div>
                      <div style={{ textAlign: 'right', minWidth: 88, flexShrink: 0 }}>
                        <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 19, fontWeight: 600, color: '#1A1611', letterSpacing: '-0.5px' }}>{cd.votes.toLocaleString('en-IN')}</div>
                        <div style={{ fontSize: 11, color: '#5C5245' }}>votes</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* ── SWING ANALYSIS ────────────────────────────────── */}
          {swingData && (
            <div style={{ padding: '0 32px 22px' }}>
              <Divider />
              <SectionTitle>Vote Share Swing — 2016 / 2021 / 2026</SectionTitle>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, alignItems: 'stretch' }}>

                {/* LEFT: Table — fixed layout, tight columns */}
                <div style={{ background: '#FDFCFB', border: '1px solid #E2DDD8', borderRadius: 10, overflow: 'hidden' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed' }}>
                    <colgroup>
                      <col style={{ width: '28%' }} />
                      <col style={{ width: '24%' }} />
                      <col style={{ width: '24%' }} />
                      <col style={{ width: '24%' }} />
                    </colgroup>
                    <thead>
                      <tr style={{ borderBottom: '2px solid #E2DDD8', background: '#F5F2EE' }}>
                        <th style={{ padding: '8px 12px', textAlign: 'left', fontSize: 10, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#5C5245' }}>Alliance</th>
                        <th style={{ padding: '8px 8px', textAlign: 'right', fontSize: 10, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#5C5245' }}>2016</th>
                        <th style={{ padding: '8px 8px', textAlign: 'right', fontSize: 10, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#5C5245' }}>2021</th>
                        <th style={{ padding: '8px 8px', textAlign: 'right', fontSize: 10, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#5C5245', borderLeft: '1px solid #E2DDD8' }}>2026</th>
                      </tr>
                    </thead>
                    <tbody>
                      {swingData.map(({ alliance, v16, v21, v26, swing2126, swing1621, has2016: h16 }) => {
                        const clr = ac(alliance);
                        const isZero = v21 < 0.05 && v26 < 0.05 && (v16 === null || v16 < 0.05);
                        if (isZero) return null;
                        // Shared cell style for all 3 years — uniform look
                        const numStyle: React.CSSProperties = {
                          fontFamily: "'JetBrains Mono',monospace",
                          fontSize: 18, fontWeight: 700,
                          color: '#1A1611', letterSpacing: '-0.5px',
                        };
                        const pctStyle: React.CSSProperties = { fontSize: 11, fontWeight: 400 };
                        return (
                          <tr key={alliance} style={{ borderBottom: '1px solid #F5F2EE' }}>
                            <td style={{ padding: '8px 12px' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <div style={{ width: 10, height: 10, borderRadius: 2, background: clr, flexShrink: 0 }} />
                                <span style={{ fontWeight: 700, fontSize: 13, color: '#1A1611' }}>{alliance}</span>
                              </div>
                            </td>

                            {/* 2016 — same style as 2021; placeholder chip always shown */}
                            <td style={{ padding: '8px 8px', textAlign: 'right' }}>
                              <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                                {h16 && v16 !== null && v16 > 0.05
                                  ? <span style={numStyle}>{v16.toFixed(1)}<span style={pctStyle}>%</span></span>
                                  : <span style={{ color: '#D1D5DB', fontSize: 14 }}>—</span>
                                }
                                {/* Always show a placeholder to keep row height uniform */}
                                <span style={{ display: 'inline-flex', alignItems: 'center', background: '#F3F4F6', color: '#D1D5DB', fontSize: 10, fontFamily: "'JetBrains Mono',monospace", padding: '2px 6px', borderRadius: 4, whiteSpace: 'nowrap' }}>
                                  — base
                                </span>
                              </div>
                            </td>

                            {/* 2021 */}
                            <td style={{ padding: '8px 8px', textAlign: 'right' }}>
                              <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                                {v21 > 0.05
                                  ? <span style={numStyle}>{v21.toFixed(1)}<span style={pctStyle}>%</span></span>
                                  : <span style={{ color: '#D1D5DB', fontSize: 14 }}>—</span>
                                }
                                {h16 && swing1621 !== null && Math.abs(swing1621) >= 0.1
                                  ? <SwingChip value={swing1621} label="vs '16" />
                                  : <span style={{ display: 'inline-flex', alignItems: 'center', background: '#F3F4F6', color: '#D1D5DB', fontSize: 10, fontFamily: "'JetBrains Mono',monospace", padding: '2px 6px', borderRadius: 4, whiteSpace: 'nowrap' }}>— no chg</span>
                                }
                              </div>
                            </td>

                            {/* 2026 — only revealed once 100% counted (RESULT_DECLARED) */}
                            <td style={{ padding: '8px 8px', textAlign: 'right', borderLeft: '1px solid #E2DDD8' }}>
                              <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                                {is2026Final && v26 > 0.05
                                  ? <span style={numStyle}>{v26.toFixed(1)}<span style={pctStyle}>%</span></span>
                                  : <span style={{ color: '#D1D5DB', fontSize: 14 }}>—</span>
                                }
                                {is2026Final && Math.abs(swing2126) >= 0.1
                                  ? <SwingChip value={swing2126} label="vs '21" />
                                  : <span style={{ display: 'inline-flex', alignItems: 'center', background: '#F3F4F6', color: '#D1D5DB', fontSize: 10, fontFamily: "'JetBrains Mono',monospace", padding: '2px 6px', borderRadius: 4, whiteSpace: 'nowrap' }}>{is2026Final ? '— no chg' : '— pending'}</span>
                                }
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* RIGHT: Vertical stacked columns — fills full height of table */}
                <div style={{ background: '#FDFCFB', border: '1px solid #E2DDD8', borderRadius: 10, padding: '12px 10px 10px', overflow: 'hidden', display: 'flex', flexDirection: 'column', height: '100%', boxSizing: 'border-box' }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'stretch', flex: 1, minHeight: 0 }}>
                    {(['2016', '2021', '2026'] as const).map(yr => {
                      const has16 = swingData[0]?.has2016;
                      if (yr === '2016' && !has16) return null;
                      // 2026 bar: only show real data if fully declared; else show grey placeholder
                      const showData = yr !== '2026' || is2026Final;
                      const yData = showData
                        ? swingData.map(({ alliance, v16, v21, v26 }) => ({
                            alliance,
                            value: yr === '2016' ? (v16 ?? 0) : yr === '2021' ? v21 : v26,
                            color: ac(alliance),
                          })).filter(d => d.value > 0.05)
                        : [];
                      const total = yData.reduce((s, d) => s + d.value, 0);
                      return (
                        <div key={yr} style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                          {/* Label on top — same style as table column header */}
                          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase' as const, color: yr === '2026' ? '#1A1611' : '#9CA3AF', textAlign: 'center', marginBottom: 5 }}>
                            {yr}{yr === '2026' && !is2026Final && <span style={{ fontSize: 7, color: '#D1D5DB', marginLeft: 2, textTransform: 'none' as const, letterSpacing: 0 }}>pending</span>}
                          </div>
                          {/* Stacked bar */}
                          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderRadius: 4, overflow: 'hidden' }}>
                            {showData && yData.map(({ alliance, value, color }) => (
                              <div
                                key={alliance}
                                style={{
                                  height: `${(value / Math.max(total, 100)) * 100}%`,
                                  background: color,
                                  minHeight: value > 0.5 ? 2 : 0,
                                  transition: 'height 0.6s ease',
                                }}
                                title={`${alliance} ${yr}: ${value.toFixed(1)}%`}
                              />
                            ))}
                            {/* Grey remainder or full grey if pending */}
                            {(!showData || total < 98) && (
                              <div style={{ flex: 1, background: '#E2DDD8', opacity: showData ? 0.35 : 0.6 }} />
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  {/* Legend */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 8px', marginTop: 8 }}>
                    {swingData.filter(d => d.v21 > 0.05 || d.v26 > 0.05).map(({ alliance }) => (
                      <div key={alliance} style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                        <div style={{ width: 7, height: 7, borderRadius: 2, background: ac(alliance) }} />
                        <span style={{ fontSize: 8, fontWeight: 700, color: ac(alliance) }}>{alliance}</span>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* ── 2021 RESULTS ──────────────────────────────────── */}
          {!histLoading && historical?.la_2021 && (
            <div style={{ padding: '0 32px 22px' }}>
              <Divider />
              <SectionTitle>2021 Assembly Election</SectionTitle>
              <HistoricalCandidateTable
                candidates={historical.la_2021.candidates}
                margin={historical.la_2021.margin}
                prevCandidates={historical.la_2016?.candidates ?? null}
              />
            </div>
          )}

          {/* ── 2016 RESULTS ──────────────────────────────────── */}
          {!histLoading && historical?.la_2016 && (
            <div style={{ padding: '0 32px 22px' }}>
              <Divider />
              <SectionTitle>2016 Assembly Election</SectionTitle>
              <HistoricalCandidateTable
                candidates={historical.la_2016.candidates}
                margin={historical.la_2016.margin}
                prevCandidates={null}
              />
            </div>
          )}

          {/* ── PARLIAMENT CONTEXT (collapsible) ──────────────── */}
          {!histLoading && historical && (historical.ls_2024 || historical.ls_2019) && (
            <div style={{ padding: '0 32px 24px' }}>
              <button
                onClick={() => setParliamentOpen(v => !v)}
                style={{ background: '#FDFCFB', border: '1px solid #E2DDD8', borderRadius: 8, padding: '10px 16px', cursor: 'pointer', width: '100%', textAlign: 'left', fontFamily: "'DM Sans',sans-serif", fontSize: 12, fontWeight: 600, color: '#5C5245', letterSpacing: '1.5px', textTransform: 'uppercase', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
              >
                Parliament Segment Results
                <span style={{ fontSize: 14, display: 'inline-block', transform: parliamentOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>▾</span>
              </button>
              {parliamentOpen && (
                <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
                  {([
                    historical.ls_2024 && { title: '2024 Lok Sabha', data: historical.ls_2024 },
                    historical.ls_2019 && { title: '2019 Lok Sabha', data: historical.ls_2019 },
                  ] as any[]).filter(Boolean).map(({ title, data }: any) => (
                    <HistCard key={title} title={title}>
                      <div style={{ fontSize: 12, color: '#5C5245', marginBottom: 12 }}>{data.parliament_constituency}</div>
                      <AllianceShareBars items={[
                        { alliance: 'UDF', votes: data.udf_votes, leading: data.lead_alliance === 'UDF' },
                        { alliance: 'LDF', votes: data.ldf_votes, leading: data.lead_alliance === 'LDF' },
                        { alliance: 'NDA', votes: data.nda_votes, leading: data.lead_alliance === 'NDA' },
                      ]} />
                    </HistCard>
                  ))}
                </div>
              )}
            </div>
          )}

          <div style={{ height: 32 }} />

        </div>{/* end main */}
      </div>{/* end grid */}

      <style>{`
        @keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.7)}}
        @keyframes spin{to{transform:rotate(360deg)}}
      `}</style>
    </div>
  );
}

// ── Tiny shared components ────────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: '#5C5245', marginBottom: 14 }}>{children}</div>;
}

function MetaChip({ children }: { children: React.ReactNode }) {
  return <span style={{ background: '#F5F2EE', border: '1px solid #E2DDD8', borderRadius: 5, padding: '3px 9px', fontSize: 11, color: '#5C5245', fontWeight: 500, display: 'inline-flex', alignItems: 'center' }}>{children}</span>;
}

function Badge({ children, bg }: { children: React.ReactNode; bg: string }) {
  return <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', background: bg, color: '#fff', padding: '2px 7px', borderRadius: 3 }}>{children}</span>;
}

function Divider() {
  return <div style={{ height: 1, background: '#E2DDD8', marginBottom: 22 }} />;
}

function SwingChip({ value, label }: { value: number; label: string }) {
  const isPos = value >= 0;
  const clr = isPos ? '#16A34A' : '#DC2626';
  const bg = isPos ? 'rgba(22,163,74,0.1)' : 'rgba(220,38,38,0.1)';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 2,
      background: bg, color: clr, fontSize: 10, fontWeight: 700,
      fontFamily: "'JetBrains Mono',monospace",
      padding: '2px 6px', borderRadius: 4, letterSpacing: '-0.3px', whiteSpace: 'nowrap',
    }}>
      {isPos ? '▲' : '▼'} {isPos ? '+' : ''}{value.toFixed(1)}pp
      <span style={{ fontSize: 8, fontWeight: 400, color: isPos ? '#15803D' : '#B91C1C', marginLeft: 2 }}>{label}</span>
    </span>
  );
}

function HistCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: '#FDFCFB', border: '1px solid #E2DDD8', borderRadius: 10, padding: 16 }}>
      <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '1.5px', color: '#5C5245', textTransform: 'uppercase', marginBottom: 10 }}>{title}</div>
      {children}
    </div>
  );
}

function AllianceShareBars({ items }: { items: { alliance: string; votes: number; leading: boolean }[] }) {
  const max = Math.max(...items.map(x => x.votes), 1);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {items.map(({ alliance, votes, leading }) => {
        const color = ac(alliance);
        const w = Math.round((votes / max) * 100);
        return (
          <div key={alliance} style={{ padding: '8px 10px', borderRadius: 6, border: leading ? `1.5px solid ${color}` : '1.5px solid transparent', background: leading ? (ABG[alliance] || 'transparent') : 'transparent' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontWeight: 600, fontSize: 12, color: '#1A1611' }}>{alliance}</span>
              <span style={{ fontFamily: "'JetBrains Mono',monospace", fontWeight: 600, fontSize: 12, color: '#1A1611' }}>{votes.toLocaleString('en-IN')}</span>
            </div>
            <div style={{ height: 5, background: '#E2DDD8', borderRadius: 3, overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${w}%`, background: color, borderRadius: 3, transition: 'width 0.6s ease' }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function NavButton({ dir, label, sub, onClick }: { dir: 'prev' | 'next'; label: string; sub: string; onClick: () => void }) {
  const isPrev = dir === 'prev';
  return (
    <button
      onClick={onClick}
      style={{ flex: 1, background: '#FDFCFB', border: '1px solid #E2DDD8', borderRadius: 8, padding: '12px 16px', cursor: 'pointer', textAlign: isPrev ? 'left' : 'right', fontFamily: "'DM Sans',sans-serif", transition: 'border-color 0.15s, background 0.15s' }}
      onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.borderColor = '#C8A84B'; (e.currentTarget as HTMLButtonElement).style.background = '#FFFDF5'; }}
      onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.borderColor = '#E2DDD8'; (e.currentTarget as HTMLButtonElement).style.background = '#FDFCFB'; }}
    >
      <div style={{ fontSize: 10, color: '#9CA3AF', letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 4 }}>{isPrev ? '← Previous' : 'Next →'}</div>
      <div style={{ fontSize: 13, fontWeight: 600, color: '#1A1611' }}>{label}</div>
      <div style={{ fontSize: 11, color: '#5C5245' }}>{sub}</div>
    </button>
  );
}

// ── Compact historical candidate table ────────────────────────────────────────
function HistoricalCandidateTable({
  candidates,
  margin,
  prevCandidates,
}: {
  candidates: Array<{ candidate: string; party: string; votes: number; percentage: number; is_winner: boolean; alliance: string; color_code?: string }>;
  margin: number | null;
  prevCandidates: Array<{ candidate: string; party: string; alliance: string; percentage: number }> | null;
}) {
  const totalVotes = candidates.reduce((s, c) => s + c.votes, 0);
  const winner = candidates.find(c => c.is_winner) ?? candidates[0];
  const winColor = winner ? ac(winner.alliance) : '#5C5245';

  // ── Vote-share change by alliance (main fronts) or party (OTH) ──────────
  // Aggregate current and previous totals by alliance and party
  const aggMap = (arr: Array<{ party: string; alliance: string; percentage: number }>) => {
    const al = new Map<string, number>();
    const pt = new Map<string, number>();
    for (const r of arr) {
      al.set(r.alliance, (al.get(r.alliance) ?? 0) + r.percentage);
      pt.set(r.party,    (pt.get(r.party)    ?? 0) + r.percentage);
    }
    return { al, pt };
  };
  const curr = aggMap(candidates);
  const prev = prevCandidates ? aggMap(prevCandidates) : null;

  const getChange = (alliance: string, party: string): number | null => {
    if (!prev) return null;
    if (alliance !== 'OTH') {
      const c = curr.al.get(alliance), p = prev.al.get(alliance);
      return (c !== undefined && p !== undefined) ? c - p : null;
    }
    const c = curr.pt.get(party), p = prev.pt.get(party);
    return (c !== undefined && p !== undefined) ? c - p : null;
  };

  // Previous margin % = gap between top-2 in previous election (by % since we don't have prev total votes)
  const prevMarginPct = (prevCandidates && prevCandidates.length >= 2)
    ? prevCandidates[0].percentage - prevCandidates[1].percentage
    : null;
  const currMarginPct = totalVotes > 0 && margin != null ? (margin / totalVotes) * 100 : null;
  const marginPctChange = (prevMarginPct !== null && currMarginPct !== null)
    ? currMarginPct - prevMarginPct
    : null;

  const thStyle: React.CSSProperties = {
    padding: '8px 8px', fontSize: 11, fontWeight: 700, letterSpacing: '1.2px',
    textTransform: 'uppercase', color: '#5C5245', background: '#F5F2EE',
    borderBottom: '2px solid #E2DDD8', textAlign: 'right',
  };

  return (
    <div style={{ background: '#FDFCFB', border: '1px solid #E2DDD8', borderRadius: 10, overflow: 'hidden' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed' }}>
        <colgroup>
          <col style={{ width: '3%' }} />
          <col />
          <col style={{ width: '18%' }} />
          <col style={{ width: '11%' }} />
          {prevCandidates !== null && <col style={{ width: '13%' }} />}
        </colgroup>
        <thead>
          <tr>
            <th style={{ ...thStyle, textAlign: 'left', paddingLeft: 12 }}>#</th>
            <th style={{ ...thStyle, textAlign: 'left' }}>Candidate</th>
            <th style={thStyle}>Votes</th>
            <th style={thStyle}>%</th>
            {prevCandidates !== null && <th style={{ ...thStyle, paddingRight: 12 }}>±%</th>}
          </tr>
        </thead>
        <tbody>
          {candidates.map((cand, i) => {
            const isWinner = cand.is_winner || i === 0;
            const clr = badgeColor(cand.alliance, cand.party, cand.color_code);
            const prevPct = getChange(cand.alliance, cand.party);
            const swing = prevPct;
            return (
              <tr key={i} style={{ borderBottom: '1px solid #F5F2EE' }}>
                <td style={{ padding: '7px 4px 7px 12px', color: '#9CA3AF', fontFamily: "'JetBrains Mono',monospace", fontSize: 12 }}>{i + 1}</td>
                <td style={{ padding: '7px 8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {/* Circle badge — solid alliance color, party abbr in white */}
                    <div style={{ width: 30, height: 30, borderRadius: '50%', background: clr, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 8, fontWeight: 800, color: '#fff', flexShrink: 0 }}>
                      {partyAbbr(cand.party)}
                    </div>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: isWinner ? 600 : 400, color: '#1A1611' }}>
                        {cand.candidate}
                      </div>
                      <div style={{ fontSize: 11, marginTop: 2, display: 'flex', alignItems: 'center', gap: 4 }}>
                        <span style={{ color: clr, fontWeight: 700 }}>{cand.party}</span>
                        {cand.alliance && cand.alliance !== 'OTH' && (
                          <span style={{ background: clr, color: '#fff', fontSize: 9, fontWeight: 700, padding: '1px 6px', borderRadius: 3, letterSpacing: 0.3 }}>{cand.alliance}</span>
                        )}
                      </div>
                    </div>
                  </div>
                </td>
                <td style={{ padding: '7px 8px', textAlign: 'right', fontFamily: "'JetBrains Mono',monospace", fontSize: 14, fontWeight: isWinner ? 600 : 400, color: '#1A1611' }}>
                  {cand.votes.toLocaleString('en-IN')}
                </td>
                <td style={{ padding: '7px 8px', textAlign: 'right', fontSize: 14, fontFamily: "'JetBrains Mono',monospace", color: '#1A1611' }}>
                  {cand.percentage.toFixed(1)}%
                </td>
                {prevCandidates !== null && (
                  <td style={{ padding: '7px 12px 7px 4px', textAlign: 'right' }}>
                    {swing !== null && Math.abs(swing) >= 0.1 ? (
                      <span style={{ fontSize: 14, fontWeight: 700, fontFamily: "'JetBrains Mono',monospace", color: swing >= 0 ? '#16A34A' : '#DC2626' }}>
                        {swing >= 0 ? '▲' : '▼'}{Math.abs(swing).toFixed(1)}
                      </span>
                    ) : swing !== null ? (
                      <span style={{ fontSize: 14, color: '#D1D5DB' }}>≈</span>
                    ) : (
                      <span style={{ fontSize: 14, color: '#E2DDD8' }}>—</span>
                    )}
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          {/* Margin row — label spanning # + Candidate, value in Votes and % cols */}
          {margin != null && (
            <tr style={{ background: '#F5F2EE', borderTop: '2px solid #E2DDD8' }}>
              <td colSpan={2} style={{ padding: '9px 12px', textAlign: 'right', fontSize: 12, color: '#5C5245', fontWeight: 600, fontStyle: 'italic' }}>
                Margin of victory
              </td>
              <td style={{ padding: '9px 8px', textAlign: 'right', fontFamily: "'JetBrains Mono',monospace", fontSize: 14, fontWeight: 700, color: winColor }}>
                {margin.toLocaleString('en-IN')}
              </td>
              <td style={{ padding: '9px 8px', textAlign: 'right', fontFamily: "'JetBrains Mono',monospace", fontSize: 13, color: '#5C5245' }}>
                {totalVotes > 0 ? ((margin / totalVotes) * 100).toFixed(2) + '%' : '—'}
              </td>
              {prevCandidates !== null && (
                <td style={{ padding: '9px 12px 9px 4px', textAlign: 'right' }}>
                  {marginPctChange !== null && Math.abs(marginPctChange) >= 0.1 ? (
                    <span style={{ fontSize: 11, fontWeight: 700, fontFamily: "'JetBrains Mono',monospace", color: marginPctChange >= 0 ? '#16A34A' : '#DC2626' }}>
                      {marginPctChange >= 0 ? '▲' : '▼'}{Math.abs(marginPctChange).toFixed(1)}
                    </span>
                  ) : (
                    <span style={{ fontSize: 11, color: '#D1D5DB' }}>≈</span>
                  )}
                </td>
              )}
            </tr>
          )}
        </tfoot>

      </table>
    </div>
  );
}
