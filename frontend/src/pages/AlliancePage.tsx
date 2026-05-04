import { useState, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAllianceSummary, useAllHistorical, useConstituencies } from '../hooks/useElectionData';
import GlobalHeader from '../components/GlobalHeader';
import { partyAbbr, partyDisplay } from '../utils/partyAbbr';
import { ALLIANCE_COLORS, resolvePartyColor, resolveCardBg } from '../utils/colorUtils';
import { classifyForAlliance, classifySeat } from '../utils/seatClassification';
import type { ConstituencyListItem } from '../types';

// ── Design tokens ─────────────────────────────────────────────
const AC: Record<string, string> = {
  LDF: '#D42B2B', UDF: '#1A8FE3', NDA: '#F7921C', OTH: '#6B7280',
};
function ac(a: string) { return AC[a] || '#6B7280'; }

const ALLIANCE_FULL: Record<string, string> = {
  ldf: 'Left Democratic Front',
  udf: 'United Democratic Front',
  nda: 'National Democratic Alliance',
};

const LARGE_MARGIN = 5000;
const TIGHT_MARGIN = 2000;

// ── Seat classification badge ─────────────────────────────────
type SeatClass = 'Stronghold' | 'Fragile' | 'Leaning' | 'Swing' | "Opponent's";

function ClassBadge({ cls, alliance }: { cls: SeatClass; alliance: string | null }) {
  const color = alliance ? ac(alliance) : '#6B7280';
  const isStrong = cls === 'Stronghold';
  const isFragile = cls === 'Fragile';

  const bg = isStrong
    ? color
    : isFragile
    ? 'transparent'
    : alliance
    ? color + '22'
    : '#F5F2EE';

  const fg = isStrong ? '#fff' : color;

  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      fontSize: 9, fontWeight: 700, letterSpacing: 0.4,
      padding: '2px 7px', borderRadius: 20,
      background: isFragile
        ? `repeating-linear-gradient(45deg, ${color}22, ${color}22 3px, transparent 3px, transparent 6px)`
        : bg,
      color: fg,
      border: `1px solid ${color}60`,
      whiteSpace: 'nowrap',
    }}>
      {alliance && <span style={{ width: 5, height: 5, borderRadius: '50%', background: color, display: 'inline-block', flexShrink: 0 }} />}
      {cls}
    </span>
  );
}

// ── Swing delta pill ──────────────────────────────────────────
function SwingPill({ value }: { value: number }) {
  if (Math.abs(value) < 0.1) return <span style={{ color: '#9CA3AF', fontSize: 11 }}>≈</span>;
  const up = value > 0;
  return (
    <span style={{ fontSize: 11, fontWeight: 700, fontFamily: "'JetBrains Mono',monospace", color: up ? '#16A34A' : '#DC2626' }}>
      {up ? '▲' : '▼'}{Math.abs(value).toFixed(1)}%
    </span>
  );
}

// ── Constituency card (mini, reuses HomePage card style) ──────
function ConstCard({
  c,
  seatCls,
  ownerAl,
  allianceCode,
  onClick,
}: {
  c: ConstituencyListItem & { competing?: boolean };
  seatCls: SeatClass;
  ownerAl: string | null;
  allianceCode: string;
  onClick: () => void;
}) {
  const countingStarted = c.status === 'IN_PROGRESS' || c.status === 'RESULT_DECLARED';
  const alliance = c.leader?.alliance || 'OTH';
  const cardColor = countingStarted ? ac(alliance) : undefined;
  const margin = c.leader && c.runner_up ? c.leader.votes - c.runner_up.votes : null;
  const isClose = margin !== null && margin < TIGHT_MARGIN;

  // 2026 outcome relative to this alliance
  const currentLeader = c.leader?.alliance?.toUpperCase();
  const sitting = c.sitting_alliance?.toUpperCase();
  const al = allianceCode.toUpperCase();
  let outcome: 'leading' | 'gained' | 'lost' | 'trailing' | 'pending' = 'pending';
  if (countingStarted && currentLeader) {
    if (currentLeader === al) {
      outcome = sitting === al ? 'leading' : 'gained';
    } else if (sitting === al) {
      outcome = 'lost';
    } else {
      outcome = 'trailing';
    }
  }

  const outcomeBadge: Record<string, { label: string; color: string }> = {
    leading: { label: c.status === 'RESULT_DECLARED' ? 'WON' : 'LEADING', color: '#16A34A' },
    gained: { label: c.status === 'RESULT_DECLARED' ? 'GAINED' : 'GAINING', color: '#7C3AED' },
    lost: { label: 'LOST', color: '#DC2626' },
    trailing: { label: '2ND', color: '#6B7280' },
    pending: { label: 'AWAITED', color: '#D1D5DB' },
  };

  return (
    <div
      onClick={onClick}
      style={{
        background: countingStarted ? cardColor : '#FDFCFB',
        border: countingStarted ? 'none' : '1px solid #E2DDD8',
        borderRadius: 10,
        padding: '10px 12px',
        cursor: 'pointer',
        position: 'relative',
        boxShadow: isClose ? '0 4px 18px rgba(0,0,0,0.25)' : '0 1px 4px rgba(0,0,0,0.1)',
        transition: 'transform 0.1s',
      }}
      onMouseEnter={e => (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-1px)'}
      onMouseLeave={e => (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)'}
    >
      {/* Header row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
        <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 9, color: countingStarted ? 'rgba(255,255,255,0.5)' : '#9CA3AF' }}>
          #{String(c.number).padStart(3, '0')}
        </span>
        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          <ClassBadge cls={seatCls} alliance={ownerAl} />
          <span style={{
            fontSize: 8, fontWeight: 700, letterSpacing: 0.5,
            padding: '1px 5px', borderRadius: 10,
            background: 'rgba(0,0,0,0.2)',
            color: outcomeBadge[outcome].color,
          }}>
            {outcomeBadge[outcome].label}
          </span>
        </div>
      </div>

      {/* Name */}
      <div style={{ fontSize: 12, fontWeight: 700, color: countingStarted ? 'white' : '#1A1611', marginBottom: 4, lineHeight: 1.3 }}>
        {c.name}
      </div>

      {/* 2021 holder */}
      {c.sitting_alliance && (
        <div style={{ fontSize: 9, color: countingStarted ? 'rgba(255,255,255,0.6)' : '#9CA3AF', marginBottom: 6 }}>
          2021: <span style={{ fontWeight: 700, color: ac(c.sitting_alliance) }}>{c.sitting_alliance}</span>
          {c.sitting_party && ` · ${c.sitting_party}`}
        </div>
      )}

      {/* Live data */}
      {countingStarted && c.leader ? (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <span style={{ fontSize: 20, fontWeight: 800, color: 'white', lineHeight: 1 }}>
              {margin !== null ? `+${margin.toLocaleString('en-IN')}` : '—'}
            </span>
            <div style={{
              width: 32, height: 32, borderRadius: '50%',
              background: 'rgba(255,255,255,0.92)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 9, fontWeight: 800, color: cardColor,
            }}>
              {partyAbbr(c.leader.party)}
            </div>
          </div>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'white', marginBottom: 2 }}>{c.leader.name}</div>
          {c.runner_up && (
            <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.7)' }}>
              2nd: {c.runner_up.name} · {c.runner_up.alliance}
            </div>
          )}
        </>
      ) : (
        <div style={{ fontSize: 10, color: '#9CA3AF', fontStyle: 'italic' }}>Not yet started</div>
      )}
    </div>
  );
}

// ── Named filter definitions ──────────────────────────────────
type NamedFilter =
  | 'strongholds_pressure'
  | 'strongholds_lost'
  | 'fragile_holding'
  | 'fragile_lost'
  | 'swing_won'
  | 'opponent_captured'
  | 'leaning_at_risk'
  | 'surprise_collapse'
  | 'growing_in_loss';

// ── Main page ─────────────────────────────────────────────────
export default function AlliancePage() {
  const { code = 'ldf' } = useParams<{ code: string }>();
  const navigate = useNavigate();

  const allianceCode = code.toLowerCase();
  const allianceUpper = allianceCode.toUpperCase() as 'LDF' | 'UDF' | 'NDA';
  const allianceColor = ac(allianceUpper);

  const { data, loading } = useAllianceSummary(allianceCode);
  const { data: allHistory } = useAllHistorical();
  const { data: allConst } = useConstituencies();

  // Named filter state
  const [namedFilter, setNamedFilter] = useState<NamedFilter | null>(null);
  // Raw filter state
  const [rawProfile, setRawProfile] = useState<SeatClass | null>(null);
  const [rawOutcome, setRawOutcome] = useState<string | null>(null);
  const [rawMargin, setRawMargin] = useState<string | null>(null);
  const [rawVote, setRawVote] = useState<string | null>(null);
  // Sort
  const [sortBy, setSortBy] = useState<'number' | 'margin' | 'swing'>('number');

  // Seat classifications from historical data
  const classMap = useMemo(() => {
    const map: Record<number, { seatClass: SeatClass; ownerAlliance: string | null }> = {};
    if (!allHistory) return map;
    allHistory.forEach(h => {
      map[h.constituency_number] = classifySeat(h);
    });
    return map;
  }, [allHistory]);

  // Build enriched constituency list
  const enriched = useMemo(() => {
    if (!data?.constituencies) return [];
    return data.constituencies.map(c => {
      const cls = classMap[c.number] || { seatClass: "Opponent's" as SeatClass, ownerAlliance: null };
      const currentLeader = c.leader?.alliance?.toUpperCase();
      const sitting = c.sitting_alliance?.toUpperCase();
      const al = allianceUpper;
      const margin = c.leader && c.runner_up ? c.leader.votes - c.runner_up.votes : null;

      let outcome: string = 'pending';
      if ((c.status === 'IN_PROGRESS' || c.status === 'RESULT_DECLARED') && currentLeader) {
        if (currentLeader === al) outcome = sitting === al ? 'held' : 'gained';
        else if (sitting === al) outcome = 'lost';
        else {
          // Check rank among all candidates — approximated by runner_up alliance
          outcome = 'trailing';
        }
      }

      // Historical alliance shares for vote swing
      const hist = allHistory?.find(h => h.constituency_number === c.number);
      const share2021 = hist?.la_2021?.winner_alliance
        ? (hist.la_2021.winner_alliance === al ? 100 : 0) // placeholder — real share from alliance_shares
        : null;

      return {
        ...c,
        seatClass: cls.seatClass,
        ownerAlliance: cls.ownerAlliance,
        outcome,
        margin,
      };
    });
  }, [data, classMap, allianceUpper, allHistory]);

  // Apply named filter → sets raw filters
  function applyNamed(f: NamedFilter | null) {
    setNamedFilter(f);
    setRawProfile(null);
    setRawOutcome(null);
    setRawMargin(null);
    setRawVote(null);
    if (!f) return;
    // Map named filters to raw combinations (handled in filter logic below)
  }

  // Filter logic
  const filtered = useMemo(() => {
    let rows = enriched;

    if (namedFilter) {
      rows = rows.filter(r => {
        const cls = r.seatClass;
        const out = r.outcome;
        const m = r.margin;
        switch (namedFilter) {
          case 'strongholds_pressure':
            return cls === 'Stronghold' && (out === 'held') && false; // + vote share ▼ — needs share data
          case 'strongholds_lost':
            return cls === 'Stronghold' && out === 'lost';
          case 'fragile_holding':
            return cls === 'Fragile' && (out === 'held' || out === 'leading');
          case 'fragile_lost':
            return cls === 'Fragile' && out === 'lost';
          case 'swing_won':
            return cls === 'Swing' && (out === 'gained' || out === 'held');
          case 'opponent_captured':
            return cls === "Opponent's" && out === 'gained';
          case 'leaning_at_risk':
            return cls === 'Leaning' && (out === 'lost' || out === 'trailing');
          case 'surprise_collapse':
            return out === 'trailing' && m !== null && m < -10000;
          case 'growing_in_loss':
            return out === 'lost'; // + vote share ▲ — needs share data
          default: return true;
        }
      });
    } else {
      if (rawProfile) rows = rows.filter(r => r.seatClass === rawProfile);
      if (rawOutcome === 'holding') rows = rows.filter(r => r.outcome === 'held' || r.outcome === 'leading');
      else if (rawOutcome === 'gained') rows = rows.filter(r => r.outcome === 'gained');
      else if (rawOutcome === 'lost') rows = rows.filter(r => r.outcome === 'lost');
      else if (rawOutcome === 'runner-up') rows = rows.filter(r => r.outcome === 'trailing');
      if (rawMargin === 'safe') rows = rows.filter(r => r.margin !== null && r.margin >= 5000);
      else if (rawMargin === 'comfortable') rows = rows.filter(r => r.margin !== null && r.margin >= 2000 && r.margin < 5000);
      else if (rawMargin === 'close') rows = rows.filter(r => r.margin !== null && r.margin < 2000);
    }

    return [...rows].sort((a, b) => {
      if (sortBy === 'margin') return (b.margin ?? -1) - (a.margin ?? -1);
      return a.number - b.number;
    });
  }, [enriched, namedFilter, rawProfile, rawOutcome, rawMargin, rawVote, sortBy]);

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: '#F5F2EE', display: 'flex', flexDirection: 'column' }}>
        <GlobalHeader />
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ width: 40, height: 40, border: `3px solid ${allianceColor}30`, borderTopColor: allianceColor, borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto 12px' }} />
            <p style={{ color: '#5C5245', fontSize: 13 }}>Loading {allianceUpper} data…</p>
          </div>
          <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
        </div>
      </div>
    );
  }

  const totalWonLeading = (data?.seats_won || 0) + (data?.seats_leading || 0);
  const swingVs2021 = data ? data.vote_share - data.vote_share_2021_pct : 0;

  return (
    <div style={{ fontFamily: "'DM Sans',sans-serif", background: '#F5F2EE', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <GlobalHeader />

      {/* ── Alliance tab switcher ── */}
      <div style={{ background: '#1A1611', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0, borderBottom: `3px solid ${allianceColor}` }}>
        {(['ldf', 'udf', 'nda'] as const).map(al => {
          const active = allianceCode === al;
          const color = ac(al.toUpperCase());
          return (
            <button
              key={al}
              onClick={() => navigate(`/alliance/${al}`)}
              style={{
                padding: '10px 32px',
                fontSize: 13, fontWeight: 800, letterSpacing: 1.5,
                textTransform: 'uppercase',
                border: 'none', cursor: 'pointer',
                background: active ? color : 'transparent',
                color: active ? '#fff' : color,
                borderBottom: active ? `3px solid ${color}` : '3px solid transparent',
                transition: 'all 0.15s',
                fontFamily: "'DM Sans',sans-serif",
                marginBottom: -3,
              }}
            >
              {al.toUpperCase()}
            </button>
          );
        })}
      </div>

      {/* ── Header ── */}
      <div style={{ background: '#FDFCFB', borderBottom: '1px solid #E2DDD8', padding: '20px 24px 16px' }}>
        <div style={{ maxWidth: 1400, margin: '0 auto' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 16 }}>
            <div style={{ width: 12, height: 12, borderRadius: '50%', background: allianceColor, marginTop: 5, flexShrink: 0 }} />
            <div>
              <h1 style={{ fontFamily: "'DM Serif Display',serif", fontSize: 28, color: '#1A1611', lineHeight: 1.1, marginBottom: 2 }}>
                {allianceUpper}
              </h1>
              <div style={{ fontSize: 14, color: '#5C5245', marginBottom: 12 }}>{ALLIANCE_FULL[allianceCode]}</div>
              {/* Stat strip */}
              <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
                {[
                  { label: 'Leading + Won', value: totalWonLeading, color: allianceColor },
                  { label: 'Won', value: data?.seats_won || 0, color: '#1A1611' },
                  { label: 'Trailing', value: data?.seats_trailing || 0, color: '#6B7280' },
                  { label: 'Contested', value: data?.seats_contested || 0, color: '#6B7280' },
                ].map(s => (
                  <div key={s.label}>
                    <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 22, fontWeight: 800, color: s.color, lineHeight: 1 }}>{s.value}</div>
                    <div style={{ fontSize: 10, color: '#9CA3AF', letterSpacing: 0.5, marginTop: 2 }}>{s.label}</div>
                  </div>
                ))}
                <div style={{ borderLeft: '1px solid #E2DDD8', paddingLeft: 24 }}>
                  <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 22, fontWeight: 800, color: '#1A1611', lineHeight: 1 }}>
                    {data?.vote_share?.toFixed(1) || '—'}%
                  </div>
                  <div style={{ fontSize: 10, color: '#9CA3AF', letterSpacing: 0.5, marginTop: 2 }}>Vote Share</div>
                  {data && (
                    <div style={{ fontSize: 11, fontWeight: 700, color: swingVs2021 >= 0 ? '#16A34A' : '#DC2626', marginTop: 2 }}>
                      {swingVs2021 >= 0 ? '▲' : '▼'}{Math.abs(swingVs2021).toFixed(1)}% vs 2021
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 1400, margin: '0 auto', width: '100%', padding: '0 24px' }}>

        {/* ── Section 2: Seat Movement ── */}
        <section style={{ padding: '20px 0 0' }}>
          <h2 style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', color: '#5C5245', marginBottom: 12 }}>Seat Movement vs 2021</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
            {[
              { label: 'Gained', value: data?.seat_movement.gained || 0, color: '#7C3AED', desc: 'Not held in 2021' },
              { label: 'Held', value: data?.seat_movement.held || 0, color: allianceColor, desc: 'Sitting seats defended' },
              { label: 'Lost', value: data?.seat_movement.lost || 0, color: '#DC2626', desc: 'Sitting seats lost' },
            ].map(s => (
              <div key={s.label} style={{ background: '#FDFCFB', border: '1px solid #E2DDD8', borderRadius: 10, padding: '14px 16px', borderTop: `3px solid ${s.color}` }}>
                <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 28, fontWeight: 800, color: s.color, lineHeight: 1 }}>{s.value}</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#1A1611', marginTop: 4 }}>{s.label}</div>
                <div style={{ fontSize: 11, color: '#9CA3AF', marginTop: 2 }}>{s.desc}</div>
              </div>
            ))}
          </div>

          {/* Party breakdown table */}
          {data?.parties && data.parties.length > 0 && (
            <div style={{ background: '#FDFCFB', border: '1px solid #E2DDD8', borderRadius: 10, overflow: 'hidden', marginBottom: 20 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#F5F2EE', borderBottom: '2px solid #E2DDD8' }}>
                    {['Party', 'Contested', 'Won / Leading', 'Vote Share', 'vs 2021'].map(h => (
                      <th key={h} style={{ padding: '8px 12px', fontSize: 10, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', color: '#5C5245', textAlign: h === 'Party' ? 'left' : 'right' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.parties.map(p => (
                    <tr
                      key={p.code}
                      style={{ borderBottom: '1px solid #F5F2EE', cursor: 'pointer' }}
                      onClick={() => navigate(`/party/${p.code}`)}
                      onMouseEnter={e => (e.currentTarget as HTMLTableRowElement).style.background = '#F5F2EE'}
                      onMouseLeave={e => (e.currentTarget as HTMLTableRowElement).style.background = 'transparent'}
                    >
                      <td style={{ padding: '10px 12px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div style={{ width: 8, height: 8, borderRadius: '50%', background: p.color || allianceColor, flexShrink: 0 }} />
                          <div>
                            <div style={{ fontSize: 13, fontWeight: 600, color: '#1A1611' }}>{p.code}</div>
                            <div style={{ fontSize: 11, color: '#6B7280' }}>{p.name}</div>
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'right', fontFamily: "'JetBrains Mono',monospace", fontSize: 13, color: '#1A1611' }}>{p.contested}</td>
                      <td style={{ padding: '10px 12px', textAlign: 'right', fontFamily: "'JetBrains Mono',monospace", fontSize: 13, color: allianceColor, fontWeight: 700 }}>{p.won + p.leading}</td>
                      <td style={{ padding: '10px 12px', textAlign: 'right', fontFamily: "'JetBrains Mono',monospace", fontSize: 13, color: '#1A1611' }}>{p.vote_share?.toFixed(1)}%</td>
                      <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                        <SwingPill value={(p.vote_share || 0) - (p.vote_share_2021_pct || 0)} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* ── Section 3: Swing Analysis ── */}
        {data?.swing_analysis && (
          <section style={{ paddingBottom: 20 }}>
            <h2 style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', color: '#5C5245', marginBottom: 12 }}>Swing Analysis</h2>
            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', background: '#FDFCFB', border: '1px solid #E2DDD8', borderRadius: 10, padding: '14px 20px' }}>
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#16A34A', letterSpacing: 0.5, marginBottom: 6 }}>GAINED FROM</div>
                <div style={{ display: 'flex', gap: 16 }}>
                  {Object.entries(data.swing_analysis.gained_from).filter(([, v]) => v > 0).map(([al, v]) => (
                    <div key={al} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ width: 8, height: 8, borderRadius: '50%', background: ac(al), display: 'inline-block' }} />
                      <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 18, fontWeight: 800, color: ac(al) }}>{v}</span>
                      <span style={{ fontSize: 11, color: '#6B7280' }}>{al}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div style={{ borderLeft: '1px solid #E2DDD8', paddingLeft: 24 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#DC2626', letterSpacing: 0.5, marginBottom: 6 }}>LOST TO</div>
                <div style={{ display: 'flex', gap: 16 }}>
                  {Object.entries(data.swing_analysis.lost_to).filter(([, v]) => v > 0).map(([al, v]) => (
                    <div key={al} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ width: 8, height: 8, borderRadius: '50%', background: ac(al), display: 'inline-block' }} />
                      <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 18, fontWeight: 800, color: ac(al) }}>{v}</span>
                      <span style={{ fontSize: 11, color: '#6B7280' }}>{al}</span>
                    </div>
                  ))}
                </div>
              </div>
              {data.best_margin && (
                <div style={{ borderLeft: '1px solid #E2DDD8', paddingLeft: 24 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#16A34A', letterSpacing: 0.5, marginBottom: 4 }}>BEST MARGIN</div>
                  <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 16, fontWeight: 700, color: '#1A1611' }}>+{data.best_margin.margin.toLocaleString('en-IN')}</div>
                  <div style={{ fontSize: 11, color: '#6B7280' }}>{data.best_margin.constituency}</div>
                </div>
              )}
              {data.worst_margin && (
                <div style={{ borderLeft: '1px solid #E2DDD8', paddingLeft: 24 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#DC2626', letterSpacing: 0.5, marginBottom: 4 }}>CLOSEST</div>
                  <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 16, fontWeight: 700, color: '#1A1611' }}>+{data.worst_margin.margin.toLocaleString('en-IN')}</div>
                  <div style={{ fontSize: 11, color: '#6B7280' }}>{data.worst_margin.constituency}</div>
                </div>
              )}
            </div>
          </section>
        )}

        {/* ── Section 5: Constituency Cards ── */}
        <section style={{ paddingBottom: 32 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
            <h2 style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', color: '#5C5245' }}>
              Constituencies · {filtered.length} shown
            </h2>
            {/* Sort */}
            <div style={{ display: 'flex', gap: 4 }}>
              {(['number', 'margin'] as const).map(s => (
                <button key={s} onClick={() => setSortBy(s)} style={{
                  fontSize: 10, padding: '3px 10px', borderRadius: 20, cursor: 'pointer',
                  border: `1px solid ${sortBy === s ? '#1A1611' : '#D1CBC4'}`,
                  background: sortBy === s ? '#1A1611' : 'transparent',
                  color: sortBy === s ? '#fff' : '#5C5245',
                  fontFamily: "'DM Sans',sans-serif", textTransform: 'capitalize',
                }}>
                  {s === 'number' ? '# Order' : 'By Margin'}
                </button>
              ))}
            </div>
          </div>

          {/* Named filters row 1 */}
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
            {([
              { key: 'strongholds_lost', label: '🔴 Strongholds Lost' },
              { key: 'fragile_holding', label: '⚡ Fragile Holding' },
              { key: 'fragile_lost', label: '⚡ Fragile Lost' },
              { key: 'swing_won', label: '🔄 Swing Won' },
              { key: 'opponent_captured', label: '🏹 Opponent Territory' },
              { key: 'leaning_at_risk', label: '📉 Leaning at Risk' },
            ] as { key: NamedFilter; label: string }[]).map(f => (
              <button
                key={f.key}
                onClick={() => applyNamed(namedFilter === f.key ? null : f.key)}
                style={{
                  fontSize: 11, padding: '4px 12px', borderRadius: 20, cursor: 'pointer',
                  fontFamily: "'DM Sans',sans-serif", fontWeight: 600,
                  border: `1.5px solid ${namedFilter === f.key ? allianceColor : '#D1CBC4'}`,
                  background: namedFilter === f.key ? allianceColor : 'transparent',
                  color: namedFilter === f.key ? '#fff' : '#5C5245',
                  transition: 'all 0.15s',
                }}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Raw filters row 2 */}
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 16, paddingTop: 8, borderTop: '1px solid #E2DDD8' }}>
            {/* Profile */}
            {(['Stronghold', 'Fragile', 'Leaning', 'Swing', "Opponent's"] as SeatClass[]).map(p => (
              <button key={p} onClick={() => { setNamedFilter(null); setRawProfile(rawProfile === p ? null : p); }}
                style={{ fontSize: 10, padding: '3px 10px', borderRadius: 20, cursor: 'pointer', fontFamily: "'DM Sans',sans-serif",
                  border: `1px solid ${rawProfile === p ? '#1A1611' : '#D1CBC4'}`,
                  background: rawProfile === p ? '#1A1611' : 'transparent',
                  color: rawProfile === p ? '#fff' : '#5C5245',
                }}>{p}</button>
            ))}
            <span style={{ borderLeft: '1px solid #E2DDD8', margin: '0 4px' }} />
            {/* Outcome */}
            {(['holding', 'gained', 'lost', 'runner-up'] as const).map(o => (
              <button key={o} onClick={() => { setNamedFilter(null); setRawOutcome(rawOutcome === o ? null : o); }}
                style={{ fontSize: 10, padding: '3px 10px', borderRadius: 20, cursor: 'pointer', fontFamily: "'DM Sans',sans-serif",
                  border: `1px solid ${rawOutcome === o ? allianceColor : '#D1CBC4'}`,
                  background: rawOutcome === o ? allianceColor + '22' : 'transparent',
                  color: rawOutcome === o ? allianceColor : '#5C5245',
                  textTransform: 'capitalize',
                }}>{o}</button>
            ))}
            <span style={{ borderLeft: '1px solid #E2DDD8', margin: '0 4px' }} />
            {/* Margin */}
            {[{ k: 'safe', l: 'Safe 5k+' }, { k: 'comfortable', l: '2–5k' }, { k: 'close', l: 'Close <2k' }].map(({ k, l }) => (
              <button key={k} onClick={() => { setNamedFilter(null); setRawMargin(rawMargin === k ? null : k); }}
                style={{ fontSize: 10, padding: '3px 10px', borderRadius: 20, cursor: 'pointer', fontFamily: "'DM Sans',sans-serif",
                  border: `1px solid ${rawMargin === k ? '#1A1611' : '#D1CBC4'}`,
                  background: rawMargin === k ? '#1A1611' : 'transparent',
                  color: rawMargin === k ? '#fff' : '#5C5245',
                }}>{l}</button>
            ))}
            {(namedFilter || rawProfile || rawOutcome || rawMargin) && (
              <button onClick={() => { setNamedFilter(null); setRawProfile(null); setRawOutcome(null); setRawMargin(null); setRawVote(null); }}
                style={{ fontSize: 10, padding: '3px 10px', borderRadius: 20, cursor: 'pointer', fontFamily: "'DM Sans',sans-serif",
                  border: '1px solid #DC2626', color: '#DC2626', background: 'transparent',
                }}>✕ Clear</button>
            )}
          </div>

          {/* Card grid */}
          {filtered.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 48, color: '#9CA3AF', fontSize: 13 }}>No constituencies match the current filters</div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10 }}>
              {filtered.map(c => (
                <ConstCard
                  key={c.id}
                  c={c}
                  seatCls={c.seatClass}
                  ownerAl={c.ownerAlliance}
                  allianceCode={allianceCode}
                  onClick={() => navigate(`/constituency/${c.id}`)}
                />
              ))}
            </div>
          )}
        </section>

      </div>
    </div>
  );
}
