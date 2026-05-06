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

const LARGE_MARGIN = 10000;
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
  const countingStarted = c.status === 'IN_PROGRESS' || c.status === 'RESULT_DECLARED' || c.status === 'COMPLETED';
  
  const currentLeader = c.leader?.alliance?.toUpperCase();
  const sitting = c.sitting_alliance?.toUpperCase();
  const al = allianceCode.toUpperCase();
  let outcome: string = 'pending';
  if (countingStarted) {
    const enriched = c as any;
    if (enriched.movement === 'held' || enriched.movement === 'gained') {
      outcome = enriched.movement === 'held' ? 'leading' : 'gained';
    } else if (enriched.movement === 'lost') {
      outcome = 'lost';
    } else if (enriched.placing) {
      outcome = enriched.placing;
    } else {
      outcome = 'trailing';
    }
  }

  const allianceColor = ac(al);

  // Dynamic colors based on outcome
  let cardBg = '#E8E4DF';
  let textPrimary = '#1A1611';
  let textSecondary = '#5C5245';
  let subTextOpacity = '0.7';
  let innerBoxBg = 'rgba(0,0,0,0.05)';
  let labelBg = 'rgba(0,0,0,0.45)';
  let labelFg = 'rgba(255,255,255,0.95)';

  const outcomeLabels: Record<string, string> = {
    won: 'WON',
    leading: 'LEADING',
    gained: 'GAINED',
    lost: 'LOST',
    '2nd': '2ND',
    close_3rd: 'CLOSE 3RD',
    distant_3rd: 'DISTANT 3RD',
    trailing: 'TRAILING',
    pending: 'AWAITED',
  };

  let borderStyle = 'none';

  if (countingStarted) {
    if (outcome === 'won' || outcome === 'leading' || outcome === 'gained') {
      cardBg = allianceColor;
      textPrimary = '#fff';
      textSecondary = 'rgba(255,255,255,0.85)';
      subTextOpacity = '0.6';
      innerBoxBg = 'rgba(0,0,0,0.2)';
    } else if (outcome === '2nd') {
      cardBg = allianceColor + '15'; // Subtle tint
      textPrimary = '#1A1611';       // High contrast dark text
      textSecondary = '#5C5245';
      subTextOpacity = '0.8';
      innerBoxBg = allianceColor + '10';
      labelBg = allianceColor;
      borderStyle = `1px solid ${allianceColor}40`;
    } else if (outcome === 'close_3rd') {
      cardBg = '#FFFFFF';           // Clear white background for 3rd
      textPrimary = '#1A1611';
      textSecondary = '#5C5245';
      subTextOpacity = '0.8';
      innerBoxBg = 'rgba(0,0,0,0.03)';
      labelBg = '#D97706';          // Amber for close 3rd to distinguish
      borderStyle = `1px dashed ${allianceColor}60`;
    } else {
      // distant_3rd, trailing, lost
      cardBg = '#F9FAFB';
      textPrimary = '#6B7280';
      textSecondary = '#9CA3AF';
      subTextOpacity = '0.8';
      innerBoxBg = 'rgba(0,0,0,0.02)';
      labelBg = '#9CA3AF';
      borderStyle = '1px solid #E5E7EB';
    }
  }

  const marginValue = c.margin;
  const isClose = (marginValue !== null && marginValue !== undefined) && Math.abs(marginValue) < TIGHT_MARGIN;

  return (
    <div
      onClick={onClick}
      style={{
        background: cardBg,
        borderRadius: 12,
        padding: '12px 14px',
        cursor: 'pointer',
        position: 'relative',
        boxShadow: isClose ? '0 4px 18px rgba(0,0,0,0.15)' : countingStarted ? '0 2px 8px rgba(0,0,0,0.03)' : '0 1px 4px rgba(0,0,0,0.05)',
        transition: 'transform 0.1s',
        border: borderStyle,
      }}
      onMouseEnter={e => (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)'}
      onMouseLeave={e => (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)'}
    >
      <div className="flex justify-between items-start mb-2">
        <span className="font-mono text-[9px]" style={{ color: (outcome === 'won' || outcome === 'leading' || outcome === 'gained') ? 'rgba(255,255,255,0.6)' : '#9CA3AF' }}>
          #{String(c.number).padStart(3, '0')}
        </span>
        <div className="flex gap-1 items-center">
          <ClassBadge cls={seatCls} alliance={ownerAl} />
          <span className="text-[8px] font-black tracking-wider px-1.5 py-0.5 rounded"
            style={{ backgroundColor: labelBg, color: labelFg }}>
            {outcomeLabels[outcome]}
          </span>
        </div>
      </div>

      <div className="font-bold leading-snug mb-1 text-[14px]" style={{ color: textPrimary }}>
        {c.name}
      </div>

      <div className="text-[9px] mb-2 flex items-center gap-1.5" style={{ color: textSecondary, opacity: subTextOpacity }}>
        <span>2021: <span style={{ fontWeight: 700, color: (outcome === 'won' || outcome === 'leading' || outcome === 'gained') ? '#fff' : ac(c.sitting_alliance || 'OTH') }}>{c.sitting_alliance}</span></span>
        {c.sitting_party && <span className="opacity-60">· {c.sitting_party}</span>}
      </div>

      {countingStarted && c.alliance_candidate_name ? (
        <>
          <div className="mb-3">
            <div className="text-[10px] font-bold opacity-80" style={{ color: textPrimary }}>
              {c.alliance_party_code} Candidate
            </div>
            <div className="text-[15px] font-black truncate" style={{ color: textPrimary }}>{c.alliance_candidate_name}</div>
          </div>
          
          <div className="flex justify-between items-end mb-3">
            <div>
              <div className="font-black text-[24px] leading-none" style={{ color: textPrimary }}>
                {c.alliance_votes?.toLocaleString('en-IN') || '0'}
              </div>
              <div className="text-[9px] font-bold opacity-70 mt-1" style={{ color: textPrimary }}>VOTES</div>
            </div>
            <div className="text-right">
              <div className="font-black text-[24px] leading-none" style={{ color: textPrimary }}>
                {c.voteShare?.toFixed(1)}%
              </div>
              <div className="text-[9px] font-bold opacity-70 mt-1" style={{ color: textPrimary }}>SHARE</div>
            </div>
          </div>

          <div className="rounded-lg py-2 px-3 flex justify-between items-center" style={{ background: innerBoxBg }}>
            <div className="text-[10px] font-bold opacity-70 uppercase tracking-wider" style={{ color: textPrimary }}>Current Margin</div>
            <div className="text-right">
              <div className="font-black text-[16px] leading-none" style={{ color: textPrimary }}>
                {marginValue !== null && marginValue !== undefined ? (marginValue > 0 ? `+${marginValue.toLocaleString('en-IN')}` : marginValue.toLocaleString('en-IN')) : '—'}
              </div>
            </div>
          </div>
        </>
      ) : (
        <div className="text-[10px] italic flex items-center gap-1.5" style={{ color: '#9CA3AF' }}>
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-neutral-400/60" />
          {countingStarted ? 'No candidate info' : 'Awaiting results'}
        </div>
      )}
    </div>
  );
}


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

  const [rawProfile, setRawProfile] = useState<SeatClass | null>(null);
  const [rawOutcome, setRawOutcome] = useState<string | null>(null);
  const [rawMovement, setRawMovement] = useState<string | null>(null);
  const [rawMargin, setRawMargin] = useState<string | null>(null);
  const [rawVotes, setRawVotes] = useState<number | null>(null);
  const [rawVoteShare, setRawVoteShare] = useState<number | null>(null);
  const [sortBy, setSortBy] = useState<'number' | 'margin' | 'votes' | 'vote_share'>('number');
  const [activeTab, setActiveTab] = useState<'summary' | 'constituencies'>('summary');

  const classMap = useMemo(() => {
    const map: Record<number, { seatClass: SeatClass; ownerAlliance: string | null }> = {};
    if (!allHistory) return map;
    allHistory.forEach(h => {
      const results = [h.la_2011, h.la_2016, h.la_2021];
      
      // 1. Check if the selected alliance "owns" it (Strong/Lean/Fragile only)
      const clsForUs = classifyForAlliance(allianceUpper, results);
      if (clsForUs === 'Stronghold' || clsForUs === 'Leaning' || clsForUs === 'Fragile') {
        map[h.constituency_number] = {
          seatClass: clsForUs,
          ownerAlliance: allianceUpper
        };
      } else {
        // 2. Not ours. Is it a global Swing or belongs to someone else?
        const global = classifySeat(h);
        if (global.seatClass === 'Swing') {
          map[h.constituency_number] = {
            seatClass: 'Swing',
            ownerAlliance: null
          };
        } else {
          map[h.constituency_number] = {
            seatClass: "Opponent's",
            ownerAlliance: global.ownerAlliance
          };
        }
      }
    });
    return map;
  }, [allHistory, allianceUpper]);

  const enriched = useMemo(() => {
    if (!data?.constituencies) return [];
    return data.constituencies.map(c => {
      const liveC = allConst?.find(ac => ac.number === c.number);
      const cls = classMap[c.number] || { seatClass: "Opponent's" as SeatClass, ownerAlliance: null };
      
      const al = allianceUpper;
      
      // Merge live data
      const status = liveC?.status || c.status;
      const leader = liveC?.leader || c.leader;
      const runner_up = liveC?.runner_up || c.runner_up;
      
      const allianceCandidate = liveC?.candidates_2026?.find(cand => cand.alliance === al);
      const allianceVotes = allianceCandidate?.votes ?? c.alliance_votes ?? 0;
      const allianceCandidateName = allianceCandidate?.name ?? c.alliance_candidate_name;
      const alliancePartyCode = allianceCandidate?.party ?? c.alliance_party_code;

      const totalCounted = liveC?.votes_counted || 0;
      // VOTE SHARE FIX: Use total votes counted so far as the denominator for live share
      const voteShareDenominator = totalCounted > 0 ? totalCounted : (c.total_valid || 0);
      const voteShare = voteShareDenominator > 0 ? (allianceVotes / voteShareDenominator) * 100 : 0;

      const currentLeaderAl = leader?.alliance?.toUpperCase();
      const sitting = c.sitting_alliance?.toUpperCase();

      const isDeclared = status === 'RESULT_DECLARED' || status === 'COMPLETED';

      // Placing
      let placing: string | null = null;
      if (currentLeaderAl === al) {
        placing = isDeclared ? 'won' : 'leading';
      } else if (runner_up?.alliance?.toUpperCase() === al) {
        placing = '2nd';
      } else {
        // Fallback to static placement if live top-2 doesn't include us
        const alliancePos = c.alliance_pos !== undefined ? c.alliance_pos : null;
        if (alliancePos === 1) placing = isDeclared ? 'won' : 'leading';
        else if (alliancePos === 2) placing = '2nd';
        else if (alliancePos === 3) {
          const m2 = c.margin_to_second !== undefined ? c.margin_to_second : 100000;
          placing = m2 < 10000 ? 'close_3rd' : 'distant_3rd';
        }
      }

      // Movement
      let movement: string | null = null;
      if (status !== 'NOT_STARTED') {
        if (currentLeaderAl === al) movement = sitting === al ? 'held' : 'gained';
        else if (sitting === al) movement = 'lost';
      }

      // Margin
      let margin = null;
      if (leader) {
        if (currentLeaderAl === al) {
          margin = runner_up ? leader.votes - runner_up.votes : leader.votes;
        } else {
          margin = allianceVotes - leader.votes;
        }
      }

      return { 
        ...c, 
        status,
        leader,
        runner_up,
        seatClass: cls.seatClass, 
        ownerAlliance: cls.ownerAlliance, 
        placing,
        movement,
        margin,
        allianceVotes,
        voteShare,
        alliance_candidate_name: allianceCandidateName,
        alliance_party_code: alliancePartyCode
      };
    });
  }, [data, allConst, classMap, allianceUpper]);

  const liveSummary = useMemo(() => {
    const stats = {
      won: 0,
      leading: 0,
      second: 0,
      close3rd: 0,
      distant3rd: 0,
      trailing: 0,
      contested: enriched.length,
      gained: 0,
      held: 0,
      lost: 0,
      totalVotes: 0,
      totalValid: 0,
      partyStats: {} as Record<string, { won: number; leading: number; second: number; close3rd: number; distant3rd: number; contested: number; votes: number; totalValid: number }>
    };

    enriched.forEach(c => {
      const pCode = c.alliance_party_code || 'OTH';
      if (!stats.partyStats[pCode]) {
        stats.partyStats[pCode] = { won: 0, leading: 0, second: 0, close3rd: 0, distant3rd: 0, contested: 0, votes: 0, totalValid: 0 };
      }
      const ps = stats.partyStats[pCode];
      ps.contested++;
      ps.votes += c.allianceVotes || 0;
      const cValid = (c.status !== 'NOT_STARTED' && c.votes_counted) ? c.votes_counted : (c.total_valid || 0);
      ps.totalValid += cValid;
      stats.totalVotes += c.allianceVotes || 0;
      stats.totalValid += cValid;

      if (c.placing === 'won') { stats.won++; ps.won++; }
      else if (c.placing === 'leading') { stats.leading++; ps.leading++; }
      else if (c.placing === '2nd') { stats.second++; ps.second++; }
      else if (c.placing === 'close_3rd') { stats.close3rd++; ps.close3rd++; }
      else if (c.placing === 'distant_3rd') { stats.distant3rd++; ps.distant3rd++; }
      else if (c.status !== 'NOT_STARTED') { stats.trailing++; }

      if (c.movement === 'gained') stats.gained++;
      if (c.movement === 'held') stats.held++;
      if (c.movement === 'lost') stats.lost++;
    });

    return stats;
  }, [enriched]);

  const filtered = useMemo(() => {
    let rows = enriched;

    if (rawProfile) rows = rows.filter(r => r.seatClass === rawProfile);
    if (rawOutcome) rows = rows.filter(r => r.placing === rawOutcome);
    if (rawMovement) rows = rows.filter(r => r.movement === rawMovement);
    
    if (rawMargin === 'safe') rows = rows.filter(r => r.margin !== null && r.margin >= 10000);
    else if (rawMargin === 'comfortable') rows = rows.filter(r => r.margin !== null && r.margin >= 2000 && r.margin < 10000);
    else if (rawMargin === 'close') rows = rows.filter(r => r.margin !== null && Math.abs(r.margin) < 2000);

    if (rawVotes !== null) {
      if (rawVotes === 100000) rows = rows.filter(r => r.allianceVotes >= 90000); // Hack for >= max bucket
      else rows = rows.filter(r => r.allianceVotes >= rawVotes && r.allianceVotes < rawVotes + 10000);
    }
    
    if (rawVoteShare !== null) {
      if (rawVoteShare === 55) rows = rows.filter(r => r.voteShare >= 55);
      else rows = rows.filter(r => r.voteShare >= rawVoteShare && r.voteShare < rawVoteShare + 5);
    }

    return [...rows].sort((a, b) => {
      if (sortBy === 'margin') return (b.margin ?? -1) - (a.margin ?? -1);
      if (sortBy === 'votes') return (b.allianceVotes ?? -1) - (a.allianceVotes ?? -1);
      if (sortBy === 'vote_share') return (b.voteShare ?? -1) - (a.voteShare ?? -1);
      // Fallback
      return a.number - b.number;
    });
  }, [enriched, rawProfile, rawOutcome, rawMovement, rawMargin, rawVotes, sortBy, allianceUpper]);

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

  const swingVs2021 = data && liveSummary.totalValid > 0 ? (liveSummary.totalVotes / liveSummary.totalValid * 100) - data.vote_share_2021_pct : 0;
  const hasAnyFilter = rawProfile || rawOutcome || rawMovement || rawMargin || rawVotes !== null || rawVoteShare !== null;

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
                { label: 'Won', value: liveSummary.won, color: allianceColor },
                { label: 'Leading', value: liveSummary.leading, color: allianceColor + 'BB' },
                { label: '2nd', value: liveSummary.second, color: '#1A1611' },
                { label: 'Close 3rd', value: liveSummary.close3rd, color: '#F59E0B', desc: '< 10k margin' },
                { label: 'Distant 3rd', value: liveSummary.distant3rd, color: '#6B7280', desc: '≥ 10k margin' },
                { label: 'Contested', value: liveSummary.contested, color: '#6B7280' },
              ].map((s, i, arr) => (
                <div key={s.label} className={`px-5 md:px-6 shrink-0 ${i < arr.length - 1 ? 'border-r border-pageborder' : ''}`}>
                  <div className="w-2.5 h-2.5 mb-2" style={{ backgroundColor: s.color }} />
                  <div className="text-[13px] font-semibold mb-0.5" style={{ color: s.color }}>{s.label}</div>
                  <div className="font-sans font-bold text-[22px] leading-none" style={{ color: s.color }}>{s.value}</div>
                  {s.desc && <div className="text-[10px] text-ink2 mt-1 whitespace-nowrap font-medium">{s.desc}</div>}
                </div>
              ))}
              <div className="px-5 md:px-6 shrink-0 border-l border-pageborder">
                <div className="w-2.5 h-2.5 mb-2 bg-ink" />
                <div className="text-[13px] font-semibold mb-0.5 text-ink">Vote Share</div>
                <div className="font-sans font-bold text-[22px] leading-none text-ink">
                  {liveSummary.totalValid > 0 ? (liveSummary.totalVotes / liveSummary.totalValid * 100).toFixed(1) : '—'}%
                </div>
                {data && (
                  <div className="text-[11px] font-bold mt-0.5" style={{ color: swingVs2021 >= 0 ? '#16A34A' : '#DC2626' }}>
                    {swingVs2021 >= 0 ? '▲' : '▼'}{Math.abs(swingVs2021).toFixed(1)}% vs 2021
                  </div>
                )}
              </div>
              
              {data?.parties && data.parties.length > 0 && data.parties.map((p) => {
                const ps = liveSummary.partyStats[p.code];
                return (
                  <div key={p.code} className="px-5 md:px-6 shrink-0 border-l border-pageborder">
                    <div className="w-2.5 h-2.5 mb-2" style={{ backgroundColor: p.color || allianceColor }} />
                    <div className="text-[13px] font-semibold mb-0.5" style={{ color: p.color || allianceColor }}>{p.code}</div>
                    <div className="font-sans font-bold text-[22px] leading-none" style={{ color: p.color || allianceColor }}>
                      {ps ? ps.won + ps.leading : 0} <span className="font-sans font-semibold text-[14px] text-ink2 ml-0.5">/ {p.contested}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* ── Content ── */}
      <div className="flex-1 w-full px-4 md:px-8 py-5 space-y-6">

        {/* ── Tabs ── */}
        <div className="flex gap-6 border-b border-pageborder px-1">
          <button
            onClick={() => setActiveTab('summary')}
            className={`text-[12px] font-bold tracking-widest uppercase pb-3 transition-colors ${activeTab === 'summary' ? 'text-ink' : 'text-ink2 hover:text-ink'}`}
            style={{ borderBottom: activeTab === 'summary' ? `2px solid ${allianceColor}` : '2px solid transparent', marginBottom: '-1px' }}
          >
            Summary
          </button>
          <button
            onClick={() => setActiveTab('constituencies')}
            className={`text-[12px] font-bold tracking-widest uppercase pb-3 transition-colors ${activeTab === 'constituencies' ? 'text-ink' : 'text-ink2 hover:text-ink'}`}
            style={{ borderBottom: activeTab === 'constituencies' ? `2px solid ${allianceColor}` : '2px solid transparent', marginBottom: '-1px' }}
          >
            Constituencies
          </button>
        </div>

        {activeTab === 'summary' ? (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
            {/* ── Seat Movement ── */}
            <section>
              <h2 className="text-[11px] font-bold tracking-widest uppercase text-ink2 mb-3">Seat Movement vs 2021</h2>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
                {[
                  { label: 'Gained', value: liveSummary.gained, color: '#7C3AED', desc: 'Not held in 2021' },
                  { label: 'Held', value: liveSummary.held, color: allianceColor, desc: 'Sitting seats defended' },
                  { label: 'Lost', value: liveSummary.lost, color: '#DC2626', desc: 'Sitting seats lost' },
                  { label: 'Pulled to 2nd', value: data?.seat_movement.pulled_up_to_2nd || 0, color: '#10B981', desc: 'Was 3rd+ in 2021' },
                  { label: 'Pushed to 3rd', value: data?.seat_movement.pushed_to_3rd || 0, color: '#F59E0B', desc: 'Was 1st/2nd in 2021' },
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
                        {['Party', 'Contested', 'Won', '2nd', 'Close 3rd', 'Distant 3rd', 'Strike Rate', 'Vote Share', 'vs 2021'].map(h => (
                          <th key={h} className="px-3 py-2.5 text-[10px] font-bold tracking-widest uppercase text-ink2"
                            style={{ textAlign: h === 'Party' ? 'left' : 'right' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {data.parties.map(p => {
                        const ps = liveSummary.partyStats[p.code];
                        const wonLeading = ps ? ps.won + ps.leading : 0;
                        const vShare = ps && ps.totalValid > 0 ? (ps.votes / ps.totalValid * 100) : 0;
                        return (
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
                            <td className="px-3 py-2.5 text-right font-mono text-[13px] font-bold" style={{ color: allianceColor }}>{wonLeading}</td>
                            <td className="px-3 py-2.5 text-right font-mono text-[13px] text-ink">{ps?.second || 0}</td>
                            <td className="px-3 py-2.5 text-right font-mono text-[13px] text-ink">{ps?.close3rd || 0}</td>
                            <td className="px-3 py-2.5 text-right font-mono text-[13px] text-ink">{ps?.distant3rd || 0}</td>
                            <td className="px-3 py-2.5 text-right font-mono text-[13px] text-ink">{(p.contested > 0 ? (wonLeading / p.contested * 100) : 0).toFixed(1)}%</td>
                            <td className="px-3 py-2.5 text-right font-mono text-[13px] text-ink">{vShare.toFixed(1)}%</td>
                            <td className="px-3 py-2.5 text-right">
                              <SwingPill value={vShare - (p.vote_share_2021_pct || 0)} />
                            </td>
                          </tr>
                        );
                      })}
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
          </div>
        ) : (
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            {/* ── Constituencies ── */}
            <section className="pb-8">
              <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
                <h2 className="text-[11px] font-bold tracking-widest uppercase text-ink2">
                  Constituencies · {filtered.length} shown
                </h2>
                <div className="flex gap-1.5 flex-wrap justify-end">
                  {(['number', 'margin', 'votes', 'vote_share'] as const).map(s => (
                    <button key={s} onClick={() => setSortBy(s)}
                      className="text-[10px] px-2.5 py-1 rounded-full cursor-pointer transition-all duration-150 border font-semibold capitalize"
                      style={{
                        border: `1px solid ${sortBy === s ? '#1A1611' : '#D1CBC4'}`,
                        background: sortBy === s ? '#1A1611' : 'transparent',
                        color: sortBy === s ? '#fff' : '#5C5245',
                      }}>
                      {s === 'number' ? '# Order' : s === 'margin' ? 'By Margin' : s === 'votes' ? 'By Votes' : 'By Vote %'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Filter Row 1: Profile */}
              <div className="bg-surface rounded-xl px-4 py-3 mb-2 shadow-sm flex gap-2 flex-wrap items-center">
                <span className="text-[10px] font-bold tracking-widest uppercase text-ink2 mr-1">Profile:</span>
                {(['Stronghold', 'Leaning', 'Fragile', 'Swing', "Opponent's"] as SeatClass[]).map(p => (
                  <button key={p}
                    onClick={() => setRawProfile(rawProfile === p ? null : p)}
                    className="text-[10px] px-2.5 py-1 rounded-full cursor-pointer border font-medium transition-all"
                    style={{
                      border: `1px solid ${rawProfile === p ? allianceColor : '#D1CBC4'}`,
                      background: rawProfile === p ? allianceColor : 'transparent',
                      color: rawProfile === p ? '#fff' : '#5C5245',
                    }}>{p}</button>
                ))}
                {hasAnyFilter && (
                  <button
                    onClick={() => { setRawProfile(null); setRawOutcome(null); setRawMovement(null); setRawMargin(null); setRawVotes(null); setRawVoteShare(null); }}
                    className="text-[10px] px-2.5 py-1 rounded-full cursor-pointer border font-medium transition-all ml-auto"
                    style={{ border: '1px solid #DC2626', color: '#DC2626', background: 'transparent' }}>
                    ✕ Clear All
                  </button>
                )}
              </div>

              {/* Filter Row 2: Metrics */}
              <div className="bg-surface rounded-xl px-4 py-3 mb-4 shadow-sm flex gap-2 flex-wrap items-center">
                <span className="text-[10px] font-bold tracking-widest uppercase text-ink2 mr-1">Metrics:</span>
                
                {/* Placing */}
                {([
                  { k: 'won', l: 'Won' }, { k: '2nd', l: '2nd' }, { k: 'close_3rd', l: 'Close 3rd' }, { k: 'distant_3rd', l: 'Distant 3rd' }
                ] as const).map(({ k, l }) => (
                  <button key={k}
                    onClick={() => setRawOutcome(rawOutcome === k ? null : k)}
                    className="text-[10px] px-2.5 py-1 rounded-full cursor-pointer border font-medium transition-all"
                    style={{
                      border: `1px solid ${rawOutcome === k ? '#1A1611' : '#D1CBC4'}`,
                      background: rawOutcome === k ? '#1A1611' : 'transparent',
                      color: rawOutcome === k ? '#fff' : '#5C5245',
                    }}>{l}</button>
                ))}
                <span className="border-l border-pageborder h-4 mx-1" />
                
                {/* Movement */}
                {(['held', 'gained', 'lost'] as const).map(o => (
                  <button key={o}
                    onClick={() => setRawMovement(rawMovement === o ? null : o)}
                    className="text-[10px] px-2.5 py-1 rounded-full cursor-pointer border font-medium capitalize transition-all"
                    style={{
                      border: `1px solid ${rawMovement === o ? '#1A1611' : '#D1CBC4'}`,
                      background: rawMovement === o ? '#1A1611' : 'transparent',
                      color: rawMovement === o ? '#fff' : '#5C5245',
                    }}>{o}</button>
                ))}
                <span className="border-l border-pageborder h-4 mx-1" />
                
                {/* Margins */}
                {[{ k: 'safe', l: 'Safe 10k+' }, { k: 'comfortable', l: '2–10k' }, { k: 'close', l: 'Close <2k' }].map(({ k, l }) => (
                  <button key={k}
                    onClick={() => setRawMargin(rawMargin === k ? null : k)}
                    className="text-[10px] px-2.5 py-1 rounded-full cursor-pointer border font-medium transition-all"
                    style={{
                      border: `1px solid ${rawMargin === k ? '#1A1611' : '#D1CBC4'}`,
                      background: rawMargin === k ? '#1A1611' : 'transparent',
                      color: rawMargin === k ? '#fff' : '#5C5245',
                    }}>{l}</button>
                ))}
                <span className="border-l border-pageborder h-4 mx-1" />
                
                {/* Votes Bucket Select */}
                <select 
                  value={rawVotes || ''} 
                  onChange={(e) => setRawVotes(e.target.value ? Number(e.target.value) : null)}
                  className="text-[10px] px-2 py-1 rounded-full border border-pageborder bg-transparent outline-none cursor-pointer"
                  style={{ color: rawVotes ? '#1A1611' : '#5C5245', fontWeight: rawVotes ? 600 : 400 }}
                >
                  <option value="">Votes...</option>
                  {[5000, 10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000].map(v => (
                    <option key={v} value={v}>{v/1000}k - {(v+10000)/1000}k</option>
                  ))}
                  <option value={100000}>90k+</option>
                </select>
                
                {/* Vote Share Select */}
                <select 
                  value={rawVoteShare || ''} 
                  onChange={(e) => setRawVoteShare(e.target.value ? Number(e.target.value) : null)}
                  className="text-[10px] px-2 py-1 rounded-full border border-pageborder bg-transparent outline-none cursor-pointer"
                  style={{ color: rawVoteShare ? '#1A1611' : '#5C5245', fontWeight: rawVoteShare ? 600 : 400 }}
                >
                  <option value="">Vote %...</option>
                  {[5, 10, 15, 20, 25, 30, 35, 40, 45, 50].map(v => (
                    <option key={v} value={v}>{v}% - {v+5}%</option>
                  ))}
                  <option value={55}>55%+</option>
                </select>
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
        )}

      </div>
    </div>
  );
}