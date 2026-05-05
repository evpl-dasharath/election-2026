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
  if (Math.abs(value) < 0.1) return <span className="text-ink2 text-[11px]">≈</span>;
  const up = value > 0;
  return (
    <span className="font-mono text-[11px] font-bold" style={{ color: up ? '#16A34A' : '#DC2626' }}>
      {up ? '▲' : '▼'}{Math.abs(value).toFixed(1)}%
    </span>
  );
}

// ── Constituency card ─────────────────────────────────────────
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
        background: countingStarted ? cardColor : '#E8E4DF',
        borderRadius: 12,
        padding: '12px 14px',
        cursor: 'pointer',
        position: 'relative',
        boxShadow: isClose ? '0 4px 18px rgba(0,0,0,0.35)' : countingStarted ? '0 4px 14px rgba(26,22,17,0.14)' : '0 1px 4px rgba(0,0,0,0.15)',
        transition: 'transform 0.1s',
      }}
      onMouseEnter={e => (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)'}
      onMouseLeave={e => (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)'}
    >
      <div className="flex justify-between items-start mb-2">
        <span className="font-mono text-[9px]" style={{ color: countingStarted ? 'rgba(255,255,255,0.5)' : '#9CA3AF' }}>
          #{String(c.number).padStart(3, '0')}
        </span>
        <div className="flex gap-1 items-center">
          <ClassBadge cls={seatCls} alliance={ownerAl} />
          <span className="text-[8px] font-black tracking-wider px-1.5 py-0.5 rounded"
            style={{ backgroundColor: 'rgba(0,0,0,0.45)', color: 'rgba(255,255,255,0.95)' }}>
            {outcomeBadge[outcome].label}
          </span>
        </div>
      </div>

      <div className="font-bold leading-snug mb-1 text-[13px]" style={{ color: countingStarted ? 'white' : '#1A1611' }}>
        {c.name}
      </div>

      {c.sitting_alliance && (
        <div className="text-[9px] mb-2" style={{ color: countingStarted ? 'rgba(255,255,255,0.6)' : '#9CA3AF' }}>
          2021: <span style={{ fontWeight: 700, color: countingStarted ? 'rgba(255,255,255,0.85)' : ac(c.sitting_alliance) }}>{c.sitting_alliance}</span>
          {(c as any).sitting_party && ` · ${(c as any).sitting_party}`}
        </div>
      )}

      {countingStarted && c.leader ? (
        <>
          <div className="flex justify-between items-center mb-1">
            <span className="font-black leading-none text-[20px]" style={{ color: 'white' }}>
              {margin !== null ? `+${margin.toLocaleString('en-IN')}` : '—'}
            </span>
            <div className="w-8 h-8 rounded-full flex items-center justify-center text-[9px] font-black shrink-0"
              style={{ background: 'rgba(255,255,255,0.92)', color: cardColor }}>
              {partyAbbr(c.leader.party)}
            </div>
          </div>
          <div className="text-[11px] font-semibold mb-1" style={{ color: 'white' }}>{c.leader.name}</div>
          {c.runner_up && (
            <div className="text-[9px]" style={{ color: 'rgba(255,255,255,0.7)' }}>
              2nd: {c.runner_up.name} · {c.runner_up.alliance}
            </div>
          )}
        </>
      ) : (
        <div className="text-[10px] italic flex items-center gap-1.5" style={{ color: '#9CA3AF' }}>
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-neutral-400/60" />
          Not yet started
        </div>
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

  const [namedFilter, setNamedFilter] = useState<NamedFilter | null>(null);
  const [rawProfile, setRawProfile] = useState<SeatClass | null>(null);
  const [rawOutcome, setRawOutcome] = useState<string | null>(null);
  const [rawMargin, setRawMargin] = useState<string | null>(null);
  const [rawVote, setRawVote] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'number' | 'margin' | 'swing'>('number');

  const classMap = useMemo(() => {
    const map: Record<number, { seatClass: SeatClass; ownerAlliance: string | null }> = {};
    if (!allHistory) return map;
    allHistory.forEach(h => {
      map[h.constituency_number] = classifySeat(h);
    });
    return map;
  }, [allHistory]);

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
        else outcome = 'trailing';
      }

      return { ...c, seatClass: cls.seatClass, ownerAlliance: cls.ownerAlliance, outcome, margin };
    });
  }, [data, classMap, allianceUpper, allHistory]);

  function applyNamed(f: NamedFilter | null) {
    setNamedFilter(f);
    setRawProfile(null);
    setRawOutcome(null);
    setRawMargin(null);
    setRawVote(null);
  }

  const filtered = useMemo(() => {
    let rows = enriched;

    if (namedFilter) {
      rows = rows.filter(r => {
        const cls = r.seatClass;
        const out = r.outcome;
        const m = r.margin;
        switch (namedFilter) {
          case 'strongholds_pressure': return cls === 'Stronghold' && (out === 'held') && false;
          case 'strongholds_lost': return cls === 'Stronghold' && out === 'lost';
          case 'fragile_holding': return cls === 'Fragile' && (out === 'held' || out === 'leading');
          case 'fragile_lost': return cls === 'Fragile' && out === 'lost';
          case 'swing_won': return cls === 'Swing' && (out === 'gained' || out === 'held');
          case 'opponent_captured': return cls === "Opponent's" && out === 'gained';
          case 'leaning_at_risk': return cls === 'Leaning' && (out === 'lost' || out === 'trailing');
          case 'surprise_collapse': return out === 'trailing' && m !== null && m < -10000;
          case 'growing_in_loss': return out === 'lost';
          default: return true;
        }
      });
    } else {
      if (rawProfile) rows = rows.filter(r => r.seatClass === rawProfile);
      if (rawOutcome === 'holding') rows = rows.filter(r => r.outcome === 'held' || r.outcome === 'leading');
      else if (rawOutcome === 'gained') rows = rows.filter(r => r.outcome === 'gained');
      else if (rawOutcome === 'lost') rows = rows.filter(r => r.outcome === 'lost');
      else if (rawOutcome === 'runner-up') rows = rows.filter(r => r.outcome === 'trailing');
      if (rawMargin === 'safe') rows = rows.filter(r => r.margin !== null && r.margin >= LARGE_MARGIN);
      else if (rawMargin === 'comfortable') rows = rows.filter(r => r.margin !== null && r.margin >= TIGHT_MARGIN && r.margin < LARGE_MARGIN);
      else if (rawMargin === 'close') rows = rows.filter(r => r.margin !== null && r.margin < TIGHT_MARGIN);
    }

    return [...rows].sort((a, b) => {
      if (sortBy === 'margin') return (b.margin ?? -1) - (a.margin ?? -1);
      return a.number - b.number;
    });
  }, [enriched, namedFilter, rawProfile, rawOutcome, rawMargin, rawVote, sortBy]);

  if (loading) {
    return (
      <div className="flex flex-col min-h-screen bg-pagebg text-ink">
        <GlobalHeader />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="w-10 h-10 rounded-full border-[3px] border-pageborder mx-auto mb-3"
              style={{ borderTopColor: allianceColor, animation: 'spin 0.8s linear infinite' }} />
            <p className="text-ink2 text-[13px]">Loading {allianceUpper} data…</p>
          </div>
          <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
        </div>
      </div>
    );
  }

  const totalWonLeading = (data?.seats_won || 0) + (data?.seats_leading || 0);
  const swingVs2021 = data ? data.vote_share - data.vote_share_2021_pct : 0;
  const hasAnyFilter = namedFilter || rawProfile || rawOutcome || rawMargin || rawVote;

  return (
    <div className="flex flex-col min-h-screen bg-pagebg text-ink">
      <GlobalHeader />

      {/* ── Alliance tab switcher ── */}
      <div className="bg-surface border-b border-pageborder shrink-0">
        <div className="flex items-center px-4 md:px-8 pt-2 gap-0">
          {(['ldf', 'udf', 'nda'] as const).map(al => {
            const active = allianceCode === al;
            const color = ac(al.toUpperCase());
            return (
              <button
                key={al}
                onClick={() => navigate(`/alliance/${al}`)}
                className="text-[11px] font-black tracking-widest uppercase px-5 py-2.5 border-b-2 transition-all duration-150"
                style={{
                  borderBottomColor: active ? color : 'transparent',
                  color: active ? color : '#9CA3AF',
                }}
              >
                {al.toUpperCase()}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Hero header ── */}
      <div className="bg-surface px-4 md:px-8 pt-5 pb-4 border-b border-pageborder shrink-0">
        <div className="flex items-start gap-3 mb-4">
          <div className="w-3 h-3 rounded-full mt-1.5 shrink-0" style={{ backgroundColor: allianceColor }} />
          <div>
            <div className="font-sans text-[22px] md:text-[26px] font-bold tracking-tight leading-none mb-1" style={{ color: allianceColor }}>
              {allianceUpper}
            </div>
            <div className="text-[14px] text-ink2 mb-4">{ALLIANCE_FULL[allianceCode]}</div>

            {/* Stat strip — mirrors HomePage alliance row */}
            <div className="flex items-end gap-0 overflow-x-auto custom-scrollbar pb-1 -mb-1">
              {[
                { label: 'Leading + Won', value: totalWonLeading, color: allianceColor },
                { label: 'Won', value: data?.seats_won || 0, color: '#1A1611' },
                { label: 'Trailing', value: data?.seats_trailing || 0, color: '#6B7280' },
                { label: 'Contested', value: data?.seats_contested || 0, color: '#6B7280' },
              ].map((s, i, arr) => (
                <div key={s.label} className={`px-5 md:px-6 shrink-0 ${i < arr.length - 1 ? 'border-r border-pageborder' : ''}`}>
                  <div className="w-2.5 h-2.5 mb-2" style={{ backgroundColor: s.color }} />
                  <div className="text-[13px] font-semibold mb-0.5" style={{ color: s.color }}>{s.label}</div>
                  <div className="font-sans font-bold text-[22px] leading-none" style={{ color: s.color }}>{s.value}</div>
                </div>
              ))}
              <div className="px-5 md:px-6 shrink-0">
                <div className="w-2.5 h-2.5 mb-2 bg-ink" />
                <div className="text-[13px] font-semibold mb-0.5 text-ink">Vote Share</div>
                <div className="font-sans font-bold text-[22px] leading-none text-ink">
                  {data?.vote_share?.toFixed(1) || '—'}%
                </div>
                {data && (
                  <div className="text-[11px] font-bold mt-0.5" style={{ color: swingVs2021 >= 0 ? '#16A34A' : '#DC2626' }}>
                    {swingVs2021 >= 0 ? '▲' : '▼'}{Math.abs(swingVs2021).toFixed(1)}% vs 2021
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Content ── */}
      <div className="flex-1 w-full px-4 md:px-8 py-5 space-y-6">

        {/* ── Seat Movement ── */}
        <section>
          <h2 className="text-[11px] font-bold tracking-widest uppercase text-ink2 mb-3">Seat Movement vs 2021</h2>
          <div className="grid grid-cols-3 gap-3 mb-4">
            {[
              { label: 'Gained', value: data?.seat_movement.gained || 0, color: '#7C3AED', desc: 'Not held in 2021' },
              { label: 'Held', value: data?.seat_movement.held || 0, color: allianceColor, desc: 'Sitting seats defended' },
              { label: 'Lost', value: data?.seat_movement.lost || 0, color: '#DC2626', desc: 'Sitting seats lost' },
            ].map(s => (
              <div key={s.label}
                className="bg-surface rounded-xl px-4 py-3 shadow-sm">
                <div className="font-mono text-[28px] font-black leading-none mb-1" style={{ color: s.color }}>{s.value}</div>
                <div className="text-[12px] font-bold text-ink">{s.label}</div>
                <div className="text-[11px] text-ink2 mt-0.5">{s.desc}</div>
              </div>
            ))}
          </div>

          {/* Party breakdown table */}
          {data?.parties && data.parties.length > 0 && (
            <div className="bg-surface rounded-xl overflow-hidden shadow-sm">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-pagebg border-b-2 border-pageborder">
                    {['Party', 'Contested', 'Won / Leading', 'Vote Share', 'vs 2021'].map(h => (
                      <th key={h} className="px-3 py-2.5 text-[10px] font-bold tracking-widest uppercase text-ink2"
                        style={{ textAlign: h === 'Party' ? 'left' : 'right' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.parties.map(p => (
                    <tr
                      key={p.code}
                      className="border-b border-pageborder cursor-pointer transition-colors hover:bg-pagebg"
                      onClick={() => navigate(`/party/${p.code}`)}
                    >
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full shrink-0" style={{ background: p.color || allianceColor }} />
                          <div>
                            <div className="text-[13px] font-semibold text-ink">{p.code}</div>
                            <div className="text-[11px] text-ink2">{p.name}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-right font-mono text-[13px] text-ink">{p.contested}</td>
                      <td className="px-3 py-2.5 text-right font-mono text-[13px] font-bold" style={{ color: allianceColor }}>{p.won + p.leading}</td>
                      <td className="px-3 py-2.5 text-right font-mono text-[13px] text-ink">{p.vote_share?.toFixed(1)}%</td>
                      <td className="px-3 py-2.5 text-right">
                        <SwingPill value={(p.vote_share || 0) - (p.vote_share_2021_pct || 0)} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* ── Swing Analysis ── */}
        {data?.swing_analysis && (
          <section>
            <h2 className="text-[11px] font-bold tracking-widest uppercase text-ink2 mb-3">Swing Analysis</h2>
            <div className="bg-surface rounded-xl px-5 py-4 shadow-sm flex gap-6 flex-wrap">
              <div>
                <div className="text-[10px] font-bold tracking-widest uppercase mb-2" style={{ color: '#16A34A' }}>GAINED FROM</div>
                <div className="flex gap-4">
                  {Object.entries(data.swing_analysis.gained_from).filter(([, v]) => v > 0).map(([al, v]) => (
                    <div key={al} className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full inline-block" style={{ background: ac(al) }} />
                      <span className="font-mono text-[18px] font-black" style={{ color: ac(al) }}>{v}</span>
                      <span className="text-[11px] text-ink2">{al}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="border-l border-pageborder pl-6">
                <div className="text-[10px] font-bold tracking-widest uppercase mb-2" style={{ color: '#DC2626' }}>LOST TO</div>
                <div className="flex gap-4">
                  {Object.entries(data.swing_analysis.lost_to).filter(([, v]) => v > 0).map(([al, v]) => (
                    <div key={al} className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full inline-block" style={{ background: ac(al) }} />
                      <span className="font-mono text-[18px] font-black" style={{ color: ac(al) }}>{v}</span>
                      <span className="text-[11px] text-ink2">{al}</span>
                    </div>
                  ))}
                </div>
              </div>
              {data.best_margin && (
                <div className="border-l border-pageborder pl-6">
                  <div className="text-[10px] font-bold tracking-widest uppercase mb-1" style={{ color: '#16A34A' }}>BEST MARGIN</div>
                  <div className="font-mono text-[16px] font-bold text-ink">+{data.best_margin.margin.toLocaleString('en-IN')}</div>
                  <div className="text-[11px] text-ink2">{data.best_margin.constituency}</div>
                </div>
              )}
              {data.worst_margin && (
                <div className="border-l border-pageborder pl-6">
                  <div className="text-[10px] font-bold tracking-widest uppercase mb-1" style={{ color: '#DC2626' }}>CLOSEST</div>
                  <div className="font-mono text-[16px] font-bold text-ink">+{data.worst_margin.margin.toLocaleString('en-IN')}</div>
                  <div className="text-[11px] text-ink2">{data.worst_margin.constituency}</div>
                </div>
              )}
            </div>
          </section>
        )}

        {/* ── Constituencies ── */}
        <section className="pb-8">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <h2 className="text-[11px] font-bold tracking-widest uppercase text-ink2">
              Constituencies · {filtered.length} shown
            </h2>
            <div className="flex gap-1.5">
              {(['number', 'margin'] as const).map(s => (
                <button key={s} onClick={() => setSortBy(s)}
                  className="text-[10px] px-2.5 py-1 rounded-full cursor-pointer transition-all duration-150 border font-semibold capitalize"
                  style={{
                    border: `1px solid ${sortBy === s ? '#1A1611' : '#D1CBC4'}`,
                    background: sortBy === s ? '#1A1611' : 'transparent',
                    color: sortBy === s ? '#fff' : '#5C5245',
                  }}>
                  {s === 'number' ? '# Order' : 'By Margin'}
                </button>
              ))}
            </div>
          </div>

          {/* Named filters */}
          <div className="bg-surface rounded-xl px-4 py-3 mb-2 shadow-sm flex gap-2 flex-wrap">
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
                className="text-[11px] px-3 py-1 rounded-full cursor-pointer transition-all duration-150 font-semibold"
                style={{
                  border: `1.5px solid ${namedFilter === f.key ? allianceColor : '#D1CBC4'}`,
                  background: namedFilter === f.key ? allianceColor : 'transparent',
                  color: namedFilter === f.key ? '#fff' : '#5C5245',
                }}>
                {f.label}
              </button>
            ))}
          </div>

          {/* Raw filters */}
          <div className="bg-surface rounded-xl px-4 py-3 mb-4 shadow-sm flex gap-2 flex-wrap items-center">
            {(['Stronghold', 'Fragile', 'Leaning', 'Swing', "Opponent's"] as SeatClass[]).map(p => (
              <button key={p}
                onClick={() => { setNamedFilter(null); setRawProfile(rawProfile === p ? null : p); }}
                className="text-[10px] px-2.5 py-1 rounded-full cursor-pointer border font-medium transition-all"
                style={{
                  border: `1px solid ${rawProfile === p ? '#1A1611' : '#D1CBC4'}`,
                  background: rawProfile === p ? '#1A1611' : 'transparent',
                  color: rawProfile === p ? '#fff' : '#5C5245',
                }}>{p}</button>
            ))}
            <span className="border-l border-pageborder h-4" />
            {(['holding', 'gained', 'lost', 'runner-up'] as const).map(o => (
              <button key={o}
                onClick={() => { setNamedFilter(null); setRawOutcome(rawOutcome === o ? null : o); }}
                className="text-[10px] px-2.5 py-1 rounded-full cursor-pointer border font-medium capitalize transition-all"
                style={{
                  border: `1px solid ${rawOutcome === o ? allianceColor : '#D1CBC4'}`,
                  background: rawOutcome === o ? allianceColor + '22' : 'transparent',
                  color: rawOutcome === o ? allianceColor : '#5C5245',
                }}>{o}</button>
            ))}
            <span className="border-l border-pageborder h-4" />
            {[{ k: 'safe', l: 'Safe 5k+' }, { k: 'comfortable', l: '2–5k' }, { k: 'close', l: 'Close <2k' }].map(({ k, l }) => (
              <button key={k}
                onClick={() => { setNamedFilter(null); setRawMargin(rawMargin === k ? null : k); }}
                className="text-[10px] px-2.5 py-1 rounded-full cursor-pointer border font-medium transition-all"
                style={{
                  border: `1px solid ${rawMargin === k ? '#1A1611' : '#D1CBC4'}`,
                  background: rawMargin === k ? '#1A1611' : 'transparent',
                  color: rawMargin === k ? '#fff' : '#5C5245',
                }}>{l}</button>
            ))}
            {hasAnyFilter && (
              <button
                onClick={() => { setNamedFilter(null); setRawProfile(null); setRawOutcome(null); setRawMargin(null); setRawVote(null); }}
                className="text-[10px] px-2.5 py-1 rounded-full cursor-pointer border font-medium transition-all ml-auto"
                style={{ border: '1px solid #DC2626', color: '#DC2626', background: 'transparent' }}>
                ✕ Clear
              </button>
            )}
          </div>

          {filtered.length === 0 ? (
            <div className="text-center py-12 text-ink2 text-[13px]">No constituencies match the current filters</div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: 10 }}>
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