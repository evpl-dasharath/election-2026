import { useState, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useParties, usePartyDetail, useAllHistorical } from '../hooks/useElectionData';
import GlobalHeader from '../components/GlobalHeader';
import { partyAbbr } from '../utils/partyAbbr';
import { classifySeat } from '../utils/seatClassification';
import type { Party, ConstituencyListItem } from '../types';

// ── Design tokens ─────────────────────────────────────────────
const AC: Record<string, string> = {
  LDF: '#D42B2B', UDF: '#1A8FE3', NDA: '#F7921C', OTH: '#6B7280',
};
function ac(a: string) { return AC[a] || '#6B7280'; }

const TIGHT_MARGIN = 2000;

type SeatClass = 'Stronghold' | 'Fragile' | 'Leaning' | 'Swing' | "Opponent's";

// ── Classification badge ──────────────────────────────────────
function ClassBadge({ cls, alliance }: { cls: SeatClass; alliance: string | null }) {
  const color = alliance ? ac(alliance) : '#6B7280';
  const isStrong = cls === 'Stronghold';
  const isFragile = cls === 'Fragile';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      fontSize: 9, fontWeight: 700, letterSpacing: 0.4,
      padding: '2px 7px', borderRadius: 20,
      background: isFragile
        ? `repeating-linear-gradient(45deg,${color}22,${color}22 3px,transparent 3px,transparent 6px)`
        : isStrong ? color : alliance ? color + '22' : '#F5F2EE',
      color: isStrong ? '#fff' : color,
      border: `1px solid ${color}60`,
      whiteSpace: 'nowrap',
    }}>
      {alliance && <span style={{ width: 5, height: 5, borderRadius: '50%', background: color, display: 'inline-block', flexShrink: 0 }} />}
      {cls}
    </span>
  );
}

// ── Mini constituency card ────────────────────────────────────
function PartyConstCard({
  c,
  seatCls,
  ownerAl,
  partyCode,
  partyColor,
  onClick,
}: {
  c: ConstituencyListItem;
  seatCls: SeatClass;
  ownerAl: string | null;
  partyCode: string;
  partyColor: string;
  onClick: () => void;
}) {
  const counting = c.status === 'IN_PROGRESS' || c.status === 'RESULT_DECLARED';
  const margin = c.leader && c.runner_up ? c.leader.votes - c.runner_up.votes : null;
  const isClose = margin !== null && margin < TIGHT_MARGIN;
  const isWinning = c.leader?.party === partyCode;
  const cardBg = counting && isWinning ? partyColor : counting ? '#4B5563' : '#FDFCFB';

  return (
    <div
      onClick={onClick}
      style={{
        background: cardBg, border: counting ? 'none' : '1px solid #E2DDD8',
        borderRadius: 10, padding: '10px 12px', cursor: 'pointer',
        boxShadow: isClose ? '0 4px 18px rgba(0,0,0,0.25)' : '0 1px 4px rgba(0,0,0,0.1)',
        transition: 'transform 0.1s',
      }}
      onMouseEnter={e => (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-1px)'}
      onMouseLeave={e => (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)'}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 5 }}>
        <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 9, color: counting ? 'rgba(255,255,255,0.5)' : '#9CA3AF' }}>
          #{String(c.number).padStart(3, '0')}
        </span>
        <ClassBadge cls={seatCls} alliance={ownerAl} />
      </div>
      <div style={{ fontSize: 12, fontWeight: 700, color: counting ? 'white' : '#1A1611', marginBottom: 3, lineHeight: 1.3 }}>{c.name}</div>
      <div style={{ fontSize: 9, color: counting ? 'rgba(255,255,255,0.55)' : '#9CA3AF', marginBottom: 6 }}>
        {c.district}
        {c.sitting_alliance && <> · 2021: <span style={{ color: ac(c.sitting_alliance), fontWeight: 700 }}>{c.sitting_alliance}</span></>}
      </div>
      {counting && c.leader ? (
        <>
          <div style={{ fontSize: 18, fontWeight: 800, color: 'white', lineHeight: 1, marginBottom: 3 }}>
            {isWinning && margin !== null ? `+${margin.toLocaleString('en-IN')}` : c.leader.name}
          </div>
          {!isWinning && (
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.7)' }}>
              Leader: {c.leader.party} · {c.leader.alliance}
            </div>
          )}
          {c.runner_up && isWinning && (
            <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.65)' }}>2nd: {c.runner_up.name} · {c.runner_up.party}</div>
          )}
        </>
      ) : (
        <div style={{ fontSize: 10, color: '#9CA3AF', fontStyle: 'italic' }}>Awaited</div>
      )}
    </div>
  );
}

// ── Sidebar item ──────────────────────────────────────────────
function SidebarPartyItem({
  party,
  isActive,
  onClick,
}: {
  party: Party & { seats_leading_or_won?: number };
  isActive: boolean;
  onClick: () => void;
}) {
  const alColor = ac(party.alliance);
  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '9px 14px',
        cursor: 'pointer',
        borderLeft: isActive ? `3px solid ${alColor}` : '3px solid transparent',
        background: isActive ? `${alColor}10` : 'transparent',
        transition: 'all 0.12s',
      }}
      onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLDivElement).style.background = '#F5F2EE'; }}
      onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLDivElement).style.background = 'transparent'; }}
    >
      {/* Color dot */}
      <div style={{ width: 8, height: 8, borderRadius: '50%', background: alColor, flexShrink: 0 }} />
      {/* Name */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, fontWeight: isActive ? 700 : 500, color: isActive ? alColor : '#1A1611', letterSpacing: 0.2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {party.code}
        </div>
        <div style={{ fontSize: 10, color: '#9CA3AF', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{party.full_name || party.name}</div>
      </div>
      {/* Seat count */}
      {party.seats_leading_or_won !== undefined && (
        <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 13, fontWeight: 700, color: isActive ? alColor : '#5C5245', flexShrink: 0 }}>
          {party.seats_leading_or_won}
        </span>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────
export default function PartyPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();

  const { data: parties, loading: partiesLoading } = useParties();
  const { data: partyDetail, loading: detailLoading } = usePartyDetail(code || null);
  const { data: allHistory } = useAllHistorical();

  const [sidebarSearch, setSidebarSearch] = useState('');
  const [sidebarAlFilter, setSidebarAlFilter] = useState<string>('all');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Card filters
  const [rawProfile, setRawProfile] = useState<SeatClass | null>(null);
  const [rawOutcome, setRawOutcome] = useState<string | null>(null);
  const [rawMargin, setRawMargin] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'number' | 'margin'>('number');

  // Classification map
  const classMap = useMemo(() => {
    const map: Record<number, { seatClass: SeatClass; ownerAlliance: string | null }> = {};
    if (!allHistory) return map;
    allHistory.forEach(h => { map[h.constituency_number] = classifySeat(h); });
    return map;
  }, [allHistory]);

  // Sidebar party list — sorted by alliance group then seats
  const sidebarParties = useMemo(() => {
    const alOrder = { LDF: 0, UDF: 1, NDA: 2, OTH: 3 };
    return [...(parties || [])]
      .filter(p => {
        if (sidebarAlFilter !== 'all' && p.alliance !== sidebarAlFilter) return false;
        if (sidebarSearch) {
          const s = sidebarSearch.toLowerCase();
          return p.code.toLowerCase().includes(s) || (p.full_name || p.name || '').toLowerCase().includes(s);
        }
        return true;
      })
      .sort((a, b) =>
        (alOrder[a.alliance as keyof typeof alOrder] ?? 4) - (alOrder[b.alliance as keyof typeof alOrder] ?? 4)
        || ((b as any).seats_leading_or_won || 0) - ((a as any).seats_leading_or_won || 0)
      );
  }, [parties, sidebarSearch, sidebarAlFilter]);

  // Enriched constituency list for the party
  const enrichedConsts = useMemo(() => {
    if (!partyDetail?.constituencies) return [];
    return partyDetail.constituencies.map(c => {
      const cls = classMap[c.number] || { seatClass: "Opponent's" as SeatClass, ownerAlliance: null };
      const margin = c.leader && c.runner_up ? c.leader.votes - c.runner_up.votes : null;
      const sitting = c.sitting_alliance?.toUpperCase();
      const currentLeader = c.leader?.alliance?.toUpperCase();
      const isWinning = c.leader?.party === partyDetail.code;
      let outcome = 'pending';
      if ((c.status === 'IN_PROGRESS' || c.status === 'RESULT_DECLARED') && currentLeader) {
        if (isWinning) outcome = sitting === partyDetail.alliance ? 'held' : 'gained';
        else if (sitting === partyDetail.alliance) outcome = 'lost';
        else outcome = 'trailing';
      }
      return { ...c, seatClass: cls.seatClass, ownerAlliance: cls.ownerAlliance, margin, outcome };
    });
  }, [partyDetail, classMap]);

  // Apply card filters
  const filteredConsts = useMemo(() => {
    let rows = enrichedConsts;
    if (rawProfile) rows = rows.filter(r => r.seatClass === rawProfile);
    if (rawOutcome === 'holding') rows = rows.filter(r => r.outcome === 'held');
    else if (rawOutcome === 'gained') rows = rows.filter(r => r.outcome === 'gained');
    else if (rawOutcome === 'lost') rows = rows.filter(r => r.outcome === 'lost');
    else if (rawOutcome === 'trailing') rows = rows.filter(r => r.outcome === 'trailing');
    if (rawMargin === 'safe') rows = rows.filter(r => r.margin !== null && r.margin >= 5000);
    else if (rawMargin === 'comfortable') rows = rows.filter(r => r.margin !== null && r.margin >= 2000 && r.margin < 5000);
    else if (rawMargin === 'close') rows = rows.filter(r => r.margin !== null && r.margin < 2000);
    return [...rows].sort((a, b) => sortBy === 'margin' ? (b.margin ?? -1) - (a.margin ?? -1) : a.number - b.number);
  }, [enrichedConsts, rawProfile, rawOutcome, rawMargin, sortBy]);

  const partyColor = partyDetail?.color_code || ac(partyDetail?.alliance || 'OTH');
  const allianceColor = ac(partyDetail?.alliance || 'OTH');
  const totalWonLeading = (partyDetail?.seats_won || 0) + (partyDetail?.seats_leading || 0);
  const swingVs2021 = partyDetail ? partyDetail.vote_share - partyDetail.vote_share_2021_pct : 0;

  return (
    <div style={{ fontFamily: "'DM Sans',sans-serif", background: '#F5F2EE', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <GlobalHeader />

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', position: 'relative' }}>

        {/* ── Sidebar ── */}
        <aside style={{
          width: 280, flexShrink: 0,
          background: '#FDFCFB', borderRight: '1px solid #E2DDD8',
          display: 'flex', flexDirection: 'column',
          // Mobile: slide over
          position: 'fixed', top: 0, left: 0, bottom: 0, zIndex: 40,
          transform: sidebarOpen ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform 0.2s',
        }}
          className="md:static md:transform-none md:flex md:z-auto"
        >
          {/* Sidebar header */}
          <div style={{ padding: '14px 14px 10px', borderBottom: '1px solid #E2DDD8', flexShrink: 0 }}>
            {/* Search */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#F5F2EE', border: '1px solid #E2DDD8', borderRadius: 7, padding: '6px 10px', marginBottom: 8 }}>
              <span style={{ color: '#5C5245', fontSize: 14 }}>⌕</span>
              <input
                type="text"
                placeholder="Search party…"
                value={sidebarSearch}
                onChange={e => setSidebarSearch(e.target.value)}
                style={{ border: 'none', background: 'none', outline: 'none', fontFamily: "'DM Sans',sans-serif", fontSize: 12, color: '#1A1611', width: '100%' }}
              />
            </div>
            {/* Alliance filter chips */}
            <div style={{ display: 'flex', gap: 4 }}>
              {(['all', 'LDF', 'UDF', 'NDA'] as const).map(f => {
                const active = sidebarAlFilter === f;
                const color = f === 'all' ? '#1A1611' : ac(f);
                return (
                  <button key={f} onClick={() => setSidebarAlFilter(f)} style={{
                    fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 20, cursor: 'pointer',
                    fontFamily: "'DM Sans',sans-serif",
                    border: `1.5px solid ${active ? color : '#D1CBC4'}`,
                    background: active ? color : 'transparent',
                    color: active ? '#fff' : color,
                  }}>
                    {f === 'all' ? 'All' : f}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Party list */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {partiesLoading ? (
              <div style={{ padding: 24, textAlign: 'center', color: '#9CA3AF', fontSize: 12 }}>Loading…</div>
            ) : sidebarParties.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', color: '#9CA3AF', fontSize: 12 }}>No parties match</div>
            ) : (
              sidebarParties.map(p => (
                <SidebarPartyItem
                  key={p.code}
                  party={p as any}
                  isActive={code === p.code}
                  onClick={() => { navigate(`/party/${p.code}`); setSidebarOpen(false); }}
                />
              ))
            )}
          </div>
        </aside>

        {/* Sidebar overlay for mobile */}
        {sidebarOpen && (
          <div
            onClick={() => setSidebarOpen(false)}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 39 }}
          />
        )}

        {/* ── Main Panel ── */}
        <main style={{ flex: 1, overflowY: 'auto', minWidth: 0 }}>

          {/* Mobile sidebar toggle */}
          <div style={{ padding: '10px 16px', borderBottom: '1px solid #E2DDD8', background: '#FDFCFB', display: 'flex', alignItems: 'center', gap: 10 }}
            className="md:hidden"
          >
            <button onClick={() => setSidebarOpen(true)} style={{ fontSize: 12, fontWeight: 600, color: '#5C5245', background: '#F5F2EE', border: '1px solid #E2DDD8', borderRadius: 6, padding: '5px 12px', cursor: 'pointer', fontFamily: "'DM Sans',sans-serif" }}>
              ☰ All Parties
            </button>
            {partyDetail && (
              <span style={{ fontSize: 13, fontWeight: 700, color: partyColor }}>{partyDetail.code}</span>
            )}
          </div>

          {!code || !partyDetail ? (
            /* No party selected */
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', flexDirection: 'column', gap: 12 }}>
              {detailLoading ? (
                <>
                  <div style={{ width: 36, height: 36, border: '3px solid #E2DDD8', borderTopColor: '#C8A84B', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                  <p style={{ color: '#9CA3AF', fontSize: 13 }}>Loading party data…</p>
                  <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
                </>
              ) : (
                <>
                  <div style={{ fontSize: 32 }}>🏛</div>
                  <p style={{ color: '#9CA3AF', fontSize: 14 }}>Select a party from the sidebar</p>
                </>
              )}
            </div>
          ) : (
            <div style={{ padding: '20px 24px 40px' }}>

              {/* ── Party header ── */}
              <div style={{ background: '#FDFCFB', border: '1px solid #E2DDD8', borderRadius: 12, padding: '20px 24px', marginBottom: 20, borderLeft: `4px solid ${partyColor}` }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
                  {/* Party circle */}
                  <div style={{ width: 48, height: 48, borderRadius: '50%', background: partyColor, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 800, color: '#fff', flexShrink: 0 }}>
                    {partyAbbr(partyDetail.code)}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                      <h1 style={{ fontFamily: "'DM Serif Display',serif", fontSize: 22, color: '#1A1611', lineHeight: 1.1 }}>
                        {partyDetail.code}
                      </h1>
                      <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20, background: allianceColor + '20', color: allianceColor, border: `1px solid ${allianceColor}50` }}>
                        {partyDetail.alliance}
                      </span>
                    </div>
                    <div style={{ fontSize: 13, color: '#5C5245', marginBottom: 14 }}>{partyDetail.full_name}</div>

                    {/* Stats */}
                    <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
                      {[
                        { label: 'Won + Leading', value: totalWonLeading, color: partyColor },
                        { label: 'Won', value: partyDetail.seats_won, color: '#1A1611' },
                        { label: 'Contested', value: partyDetail.seats_contested, color: '#6B7280' },
                      ].map(s => (
                        <div key={s.label}>
                          <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 20, fontWeight: 800, color: s.color, lineHeight: 1 }}>{s.value}</div>
                          <div style={{ fontSize: 10, color: '#9CA3AF', marginTop: 2 }}>{s.label}</div>
                        </div>
                      ))}
                      <div style={{ borderLeft: '1px solid #E2DDD8', paddingLeft: 20 }}>
                        <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 20, fontWeight: 800, color: '#1A1611', lineHeight: 1 }}>
                          {partyDetail.vote_share?.toFixed(1)}%
                        </div>
                        <div style={{ fontSize: 10, color: '#9CA3AF', marginTop: 2 }}>Vote Share</div>
                        <div style={{ fontSize: 11, fontWeight: 700, color: swingVs2021 >= 0 ? '#16A34A' : '#DC2626', marginTop: 2 }}>
                          {swingVs2021 >= 0 ? '▲' : '▼'}{Math.abs(swingVs2021).toFixed(1)}% vs 2021
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* ── Constituency cards ── */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10, flexWrap: 'wrap', gap: 6 }}>
                  <h2 style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', color: '#5C5245' }}>
                    Constituencies · {filteredConsts.length} / {enrichedConsts.length}
                  </h2>
                  <div style={{ display: 'flex', gap: 4 }}>
                    {(['number', 'margin'] as const).map(s => (
                      <button key={s} onClick={() => setSortBy(s)} style={{
                        fontSize: 10, padding: '3px 10px', borderRadius: 20, cursor: 'pointer',
                        fontFamily: "'DM Sans',sans-serif",
                        border: `1px solid ${sortBy === s ? '#1A1611' : '#D1CBC4'}`,
                        background: sortBy === s ? '#1A1611' : 'transparent',
                        color: sortBy === s ? '#fff' : '#5C5245',
                        textTransform: 'capitalize',
                      }}>
                        {s === 'number' ? '# Order' : 'By Margin'}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Filter chips */}
                <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginBottom: 14, paddingBottom: 10, borderBottom: '1px solid #E2DDD8' }}>
                  {(['Stronghold', 'Fragile', 'Leaning', 'Swing', "Opponent's"] as SeatClass[]).map(p => (
                    <button key={p} onClick={() => setRawProfile(rawProfile === p ? null : p)} style={{
                      fontSize: 10, padding: '3px 10px', borderRadius: 20, cursor: 'pointer', fontFamily: "'DM Sans',sans-serif",
                      border: `1px solid ${rawProfile === p ? '#1A1611' : '#D1CBC4'}`,
                      background: rawProfile === p ? '#1A1611' : 'transparent',
                      color: rawProfile === p ? '#fff' : '#5C5245',
                    }}>{p}</button>
                  ))}
                  <span style={{ borderLeft: '1px solid #E2DDD8', margin: '0 2px' }} />
                  {(['holding', 'gained', 'lost', 'trailing'] as const).map(o => (
                    <button key={o} onClick={() => setRawOutcome(rawOutcome === o ? null : o)} style={{
                      fontSize: 10, padding: '3px 10px', borderRadius: 20, cursor: 'pointer', fontFamily: "'DM Sans',sans-serif",
                      border: `1px solid ${rawOutcome === o ? partyColor : '#D1CBC4'}`,
                      background: rawOutcome === o ? partyColor + '22' : 'transparent',
                      color: rawOutcome === o ? partyColor : '#5C5245',
                      textTransform: 'capitalize',
                    }}>{o}</button>
                  ))}
                  <span style={{ borderLeft: '1px solid #E2DDD8', margin: '0 2px' }} />
                  {[{ k: 'safe', l: 'Safe 5k+' }, { k: 'comfortable', l: '2–5k' }, { k: 'close', l: '<2k' }].map(({ k, l }) => (
                    <button key={k} onClick={() => setRawMargin(rawMargin === k ? null : k)} style={{
                      fontSize: 10, padding: '3px 10px', borderRadius: 20, cursor: 'pointer', fontFamily: "'DM Sans',sans-serif",
                      border: `1px solid ${rawMargin === k ? '#1A1611' : '#D1CBC4'}`,
                      background: rawMargin === k ? '#1A1611' : 'transparent',
                      color: rawMargin === k ? '#fff' : '#5C5245',
                    }}>{l}</button>
                  ))}
                  {(rawProfile || rawOutcome || rawMargin) && (
                    <button onClick={() => { setRawProfile(null); setRawOutcome(null); setRawMargin(null); }} style={{
                      fontSize: 10, padding: '3px 10px', borderRadius: 20, cursor: 'pointer', fontFamily: "'DM Sans',sans-serif",
                      border: '1px solid #DC2626', color: '#DC2626', background: 'transparent',
                    }}>✕ Clear</button>
                  )}
                </div>

                {/* Grid */}
                {filteredConsts.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: 40, color: '#9CA3AF', fontSize: 13 }}>No constituencies match</div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: 10 }}>
                    {filteredConsts.map(c => (
                      <PartyConstCard
                        key={c.id}
                        c={c}
                        seatCls={c.seatClass}
                        ownerAl={c.ownerAlliance}
                        partyCode={partyDetail.code}
                        partyColor={partyColor}
                        onClick={() => navigate(`/constituency/${c.id}`)}
                      />
                    ))}
                  </div>
                )}
              </div>

            </div>
          )}
        </main>
      </div>
    </div>
  );
}
