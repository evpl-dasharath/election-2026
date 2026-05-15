import { useState, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useParties, usePartyDetail, useAllHistorical, useConstituencies } from '../hooks/useElectionData';
import GlobalHeader from '../components/GlobalHeader';
import { partyAbbr } from '../utils/partyAbbr';
import { classifySeat, classifyForAlliance } from '../utils/seatClassification';
import type { Party, ConstituencyListItem, SeatClass } from '../types';

// ── Design tokens ─────────────────────────────────────────────
const AC: Record<string, string> = {
  LDF: '#D42B2B', UDF: '#1A8FE3', NDA: '#F7921C', OTH: '#6B7280',
};
function ac(a: string) { return AC[a] || '#6B7280'; }

const TIGHT_MARGIN = 2000;

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
  const status = c.status;
  const countingStarted = status !== 'NOT_STARTED';
  const outcome = c.placing || 'trailing';

  const outcomeLabels: Record<string, string> = {
    won: 'WON',
    leading: 'LEADING',
    '2nd': '2ND',
    close_3rd: 'CLOSE 3RD',
    distant_3rd: 'DISTANT 3RD',
    trailing: 'TRAILING',
    pending: 'AWAITED',
  };

  // Dynamic colors
  let cardBg = '#E8E4DF';
  let textPrimary = '#1A1611';
  let textSecondary = '#5C5245';
  let subTextOpacity = '0.7';
  let innerBoxBg = 'rgba(0,0,0,0.05)';
  let labelBg = 'rgba(0,0,0,0.45)';
  let labelFg = 'rgba(255,255,255,0.95)';

  let borderStyle = 'none';

  if (countingStarted) {
    if (outcome === 'won' || outcome === 'leading') {
      cardBg = partyColor;
      textPrimary = '#fff';
      textSecondary = 'rgba(255,255,255,0.85)';
      subTextOpacity = '0.6';
      innerBoxBg = 'rgba(0,0,0,0.2)';
    } else if (outcome === '2nd') {
      cardBg = partyColor + '15';
      textPrimary = '#1A1611';
      textSecondary = '#5C5245';
      subTextOpacity = '0.8';
      innerBoxBg = partyColor + '10';
      labelBg = partyColor;
      borderStyle = `1px solid ${partyColor}40`;
    } else if (outcome === 'close_3rd') {
      cardBg = '#FFFFFF';
      textPrimary = '#1A1611';
      textSecondary = '#5C5245';
      subTextOpacity = '0.8';
      innerBoxBg = 'rgba(0,0,0,0.03)';
      labelBg = '#D97706';
      borderStyle = `1px dashed ${partyColor}60`;
    } else {
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
        <span className="font-mono text-[9px]" style={{ color: (outcome === 'won' || outcome === 'leading') ? 'rgba(255,255,255,0.6)' : '#9CA3AF' }}>
          #{String(c.number).padStart(3, '0')}
        </span>
        <div className="flex gap-1 items-center">
          <ClassBadge cls={seatCls} alliance={ownerAl} />
          {countingStarted && (
            <span className="text-[8px] font-black tracking-wider px-1.5 py-0.5 rounded"
              style={{ backgroundColor: labelBg, color: labelFg }}>
              {outcomeLabels[outcome] || 'PENDING'}
            </span>
          )}
        </div>
      </div>

      <div className="font-bold leading-snug mb-1 text-[14px]" style={{ color: textPrimary }}>
        {c.name}
      </div>

      <div className="text-[9px] mb-2 flex items-center gap-1.5" style={{ color: textSecondary, opacity: subTextOpacity }}>
        <span>2021: <span style={{ fontWeight: 700, color: (outcome === 'won' || outcome === 'leading') ? '#fff' : ac(c.sitting_alliance || 'OTH') }}>{c.sitting_alliance}</span></span>
        {c.sitting_party && <span className="opacity-60">· {c.sitting_party}</span>}
      </div>

      {countingStarted && (c as any).party_candidate_name ? (
        <>
          <div className="mb-3">
            <div className="text-[10px] font-bold opacity-80" style={{ color: textPrimary }}>
              {partyCode} Candidate
            </div>
            <div className="text-[15px] font-black truncate" style={{ color: textPrimary }}>{(c as any).party_candidate_name}</div>
          </div>
          
          <div className="flex justify-between items-end mb-3">
            <div>
              <div className="font-black text-[24px] leading-none" style={{ color: textPrimary }}>
                {(c as any).partyVotes?.toLocaleString('en-IN') || '0'}
              </div>
              <div className="text-[9px] font-bold opacity-70 mt-1" style={{ color: textPrimary }}>VOTES</div>
            </div>
            <div className="text-right">
              <div className="font-black text-[24px] leading-none" style={{ color: textPrimary }}>
                {(c as any).voteShare?.toFixed(1)}%
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

// ── Sidebar party item ────────────────────────────────────────
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
      className="flex items-center gap-2.5 px-3.5 py-2.5 cursor-pointer transition-colors"
      style={{
        borderLeft: isActive ? `3px solid ${alColor}` : '3px solid transparent',
        background: isActive ? `${alColor}10` : 'transparent',
      }}
      onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLDivElement).style.background = '#F5F2EE'; }}
      onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLDivElement).style.background = 'transparent'; }}
    >
      <div className="w-2 h-2 rounded-full shrink-0" style={{ background: alColor }} />
      <div className="flex-1 min-w-0">
        <div className="text-[12px] truncate"
          style={{ fontWeight: isActive ? 700 : 500, color: isActive ? alColor : '#1A1611', letterSpacing: 0.2 }}>
          {party.code}
        </div>
        <div className="text-[10px] text-ink2 truncate">{party.full_name || party.name}</div>
      </div>
      {party.seats_leading_or_won !== undefined && (
        <span className="font-mono text-[13px] font-bold shrink-0" style={{ color: isActive ? alColor : '#5C5245' }}>
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
  const { data: detailData, loading: detailLoading } = usePartyDetail(code || null);
  const { data: allConst } = useConstituencies();
  const { data: allHistory } = useAllHistorical();

  const [sidebarSearch, setSidebarSearch] = useState('');
  const [sidebarAlFilter, setSidebarAlFilter] = useState<string>('all');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [rawProfile, setRawProfile] = useState<SeatClass | null>(null);
  const [rawOutcome, setRawOutcome] = useState<string | null>(null);
  const [rawMovement, setRawMovement] = useState<string | null>(null);
  const [rawMargin, setRawMargin] = useState<string | null>(null);
  const [rawVotes, setRawVotes] = useState<number | null>(null);
  const [rawVoteShare, setRawVoteShare] = useState<number | null>(null);
  const [sortBy, setSortBy] = useState<'number' | 'margin' | 'votes' | 'vote_share'>('number');

  const classMap = useMemo(() => {
    const map: Record<number, { seatClass: SeatClass; ownerAlliance: string | null }> = {};
    if (!allHistory || !detailData?.alliance) return map;
    
    const targetAl = detailData.alliance as 'LDF' | 'UDF' | 'NDA';

    allHistory.forEach(h => {
      const results = [h.la_2011, h.la_2016, h.la_2021];
      
      // 1. Check if the selected party's alliance "owns" it (Stronghold/Leaning/Fragile)
      const clsForUs = classifyForAlliance(targetAl, results);
      if (clsForUs === 'Stronghold' || clsForUs === 'Leaning' || clsForUs === 'Fragile') {
        map[h.constituency_number] = {
          seatClass: clsForUs,
          ownerAlliance: targetAl
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
  }, [allHistory, detailData?.alliance]);

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

  const enrichedConsts = useMemo(() => {
    if (!detailData?.constituencies) return [];
    const partyUpper = (code || '').toUpperCase();

    return detailData.constituencies.map(c => {
      const liveC = allConst?.find(ac => ac.number === c.number);
      const cls = classMap[c.number] || { seatClass: "Opponent's" as SeatClass, ownerAlliance: null };
      
      const status = liveC?.status || c.status;
      const leader = liveC?.leader || c.leader;
      const runner_up = liveC?.runner_up || c.runner_up;
      const sitting = c.sitting_alliance?.toUpperCase();

      const cand2026 = liveC?.candidates_2026?.find(cand => cand.party.toUpperCase() === partyUpper);
      const partyVotes = cand2026?.votes ?? c.party_votes ?? 0;
      const partyCandidateName = cand2026?.name ?? c.party_candidate_name;

      const totalCounted = liveC?.votes_counted || 0;
      const voteShareDenominator = totalCounted > 0 ? totalCounted : (c.total_valid || 0);
      const voteShare = voteShareDenominator > 0 ? (partyVotes / voteShareDenominator) * 100 : 0;

      const currentLeaderParty = leader?.party?.toUpperCase();
      const isDeclared = status === 'RESULT_DECLARED' || status === 'COMPLETED';

      // Placing
      let placing: string | null = null;
      if (currentLeaderParty === partyUpper) {
        placing = isDeclared ? 'won' : 'leading';
      } else if (runner_up?.party?.toUpperCase() === partyUpper) {
        placing = '2nd';
      } else {
        // Check live candidates rank
        if (liveC?.candidates_2026) {
          const sorted = liveC.candidates_2026;
          const idx = sorted.findIndex(cand => cand.party.toUpperCase() === partyUpper);
          if (idx === 2) {
            const m2 = sorted[1].votes - sorted[2].votes;
            placing = m2 < 10000 ? 'close_3rd' : 'distant_3rd';
          } else if (idx > 2) {
            placing = 'trailing';
          }
        }
        
        if (!placing) {
          const partyPos = c.party_pos !== undefined ? c.party_pos : null;
          if (partyPos === 1) placing = isDeclared ? 'won' : 'leading';
          else if (partyPos === 2) placing = '2nd';
          else if (partyPos === 3) {
            const m2 = c.margin_to_second !== undefined ? c.margin_to_second : 100000;
            placing = m2 < 10000 ? 'close_3rd' : 'distant_3rd';
          }
        }
      }

      // Movement
      let movement: string | null = null;
      if (status !== 'NOT_STARTED') {
        if (currentLeaderParty === partyUpper) {
          movement = sitting === detailData.alliance ? 'held' : 'gained';
        } else if (sitting === detailData.alliance) {
          movement = 'lost';
        }
      }

      // Margin
      let margin = null;
      if (leader) {
        if (currentLeaderParty === partyUpper) {
          margin = runner_up ? leader.votes - runner_up.votes : leader.votes;
        } else {
          margin = partyVotes - leader.votes;
        }
      }

      // Trends
      const shareDiff = (c as any).party_share_2021 !== undefined ? (voteShare - (c as any).party_share_2021) : 0;
      const votesDiff = (c as any).party_votes_2021 !== undefined ? (partyVotes - (c as any).party_votes_2021) : 0;

      return { 
        ...c, 
        status,
        leader,
        runner_up,
        seatClass: cls.seatClass, 
        ownerAlliance: cls.ownerAlliance, 
        margin, 
        placing, 
        movement, 
        partyVotes, 
        voteShare,
        party_candidate_name: partyCandidateName,
        shareDiff,
        votesDiff
      };
    });
  }, [detailData, allConst, classMap, code]);

  const liveSummary = useMemo(() => {
    const stats = {
      won: 0,
      leading: 0,
      second: 0,
      close3rd: 0,
      distant3rd: 0,
      trailing: 0,
      contested: enrichedConsts.length,
      totalVotes: 0,
      totalValid: 0, // Will be sum of competed seats
      shareInc: 0,
      shareDec: 0,
      shareHeld: 0,
      votesInc: 0,
      votesDec: 0,
      votesHeld: 0,
    };

    enrichedConsts.forEach(c => {
      stats.totalVotes += c.partyVotes || 0;
      stats.totalValid += (c.votes_counted || 0);

      if (c.placing === 'won') stats.won++;
      else if (c.placing === 'leading') stats.leading++;
      else if (c.placing === '2nd') stats.second++;
      else if (c.placing === 'close_3rd') stats.close3rd++;
      else if (c.placing === 'distant_3rd') stats.distant3rd++;
      else if (c.status !== 'NOT_STARTED') stats.trailing++;

      // Trend counts
      if (c.status !== 'NOT_STARTED') {
        const sd = (c as any).shareDiff || 0;
        const vd = (c as any).votesDiff || 0;
        
        if (sd > 0.1) stats.shareInc++;
        else if (sd < -0.1) stats.shareDec++;
        else stats.shareHeld++;

        if (vd > 10) stats.votesInc++;
        else if (vd < -10) stats.votesDec++;
        else stats.votesHeld++;
      }
    });

    return stats;
  }, [enrichedConsts]);

  const filteredConsts = useMemo(() => {
    let rows = enrichedConsts;
    if (rawProfile) rows = rows.filter(r => r.seatClass === rawProfile);
    if (rawOutcome) rows = rows.filter(r => r.placing === rawOutcome);
    if (rawMovement) rows = rows.filter(r => r.movement === rawMovement);

    if (rawMargin === 'safe') rows = rows.filter(r => r.margin !== null && r.margin >= 10000);
    else if (rawMargin === 'comfortable') rows = rows.filter(r => r.margin !== null && r.margin >= 2000 && r.margin < 10000);
    else if (rawMargin === 'close') rows = rows.filter(r => r.margin !== null && r.margin > 0 && r.margin < 2000);
    else if (rawMargin === 'lost_safe') rows = rows.filter(r => r.margin !== null && r.margin <= -10000);
    else if (rawMargin === 'lost_comfortable') rows = rows.filter(r => r.margin !== null && r.margin <= -2000 && r.margin > -10000);
    else if (rawMargin === 'lost_close') rows = rows.filter(r => r.margin !== null && r.margin < 0 && r.margin > -2000);

    if (rawVotes !== null) {
      if (rawVotes === 100000) rows = rows.filter(r => r.partyVotes >= 90000);
      else rows = rows.filter(r => r.partyVotes >= rawVotes && r.partyVotes < rawVotes + 10000);
    }

    if (rawVoteShare !== null) {
      if (rawVoteShare === 55) rows = rows.filter(r => r.voteShare >= 55);
      else rows = rows.filter(r => r.voteShare >= rawVoteShare && r.voteShare < rawVoteShare + 5);
    }

    return [...rows].sort((a, b) => {
      if (sortBy === 'margin') return (b.margin ?? -1) - (a.margin ?? -1);
      if (sortBy === 'votes') return (b.partyVotes ?? -1) - (a.partyVotes ?? -1);
      if (sortBy === 'vote_share') return (b.voteShare ?? -1) - (a.voteShare ?? -1);
      return a.number - b.number;
    });
  }, [enrichedConsts, rawProfile, rawOutcome, rawMovement, rawMargin, rawVotes, rawVoteShare, sortBy, detailData]);

  const partyColor = detailData?.color_code || ac(detailData?.alliance || 'OTH');
  const allianceColor = ac(detailData?.alliance || 'OTH');
  const totalWonLeading = (detailData?.seats_won || 0) + (detailData?.seats_leading || 0);
  const swingVs2021 = detailData ? detailData.vote_share - detailData.vote_share_2021_pct : 0;
  const hasAnyFilter = rawProfile || rawOutcome || rawMovement || rawMargin || rawVotes !== null || rawVoteShare !== null;

  return (
    <div className="flex flex-col min-h-screen bg-pagebg text-ink">
      <GlobalHeader />

      <div className="flex-1 flex flex-col md:grid md:grid-cols-[280px_1fr] min-h-0 relative">

        {/* Mobile overlay */}
        {sidebarOpen && (
          <div className="md:hidden fixed inset-0 bg-black/40 z-40" onClick={() => setSidebarOpen(false)} />
        )}

        {/* ── Sidebar ── */}
        <aside className={`
          flex flex-col bg-surface border-r border-pageborder overflow-hidden
          fixed md:sticky top-0 md:top-[56px] h-[100dvh] md:h-[calc(100vh-56px)] z-50 md:z-auto
          w-[85%] max-w-[320px] md:w-auto md:max-w-none transition-transform duration-300
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        `}>
          {/* Sidebar header */}
          <div className="px-3.5 py-3 border-b border-pageborder shrink-0">
            {/* Search */}
            <div className="flex items-center gap-1.5 bg-pagebg border border-transparent focus-within:border-ink transition-colors rounded-lg px-2.5 py-2 mb-2">
              <span className="text-ink2 text-sm" aria-hidden="true">⌕</span>
              <input
                type="text"
                aria-label="Search party"
                placeholder="Search party…"
                value={sidebarSearch}
                onChange={e => setSidebarSearch(e.target.value)}
                className="bg-transparent border-none outline-none text-[12px] text-ink w-full placeholder-ink2"
              />
            </div>
            {/* Alliance filter chips */}
            <div className="flex gap-1.5">
              {(['all', 'LDF', 'UDF', 'NDA'] as const).map(f => {
                const active = sidebarAlFilter === f;
                const color = f === 'all' ? '#1A1611' : ac(f);
                return (
                  <button key={f} onClick={() => setSidebarAlFilter(f)}
                    className="text-[10px] font-bold px-2 py-1 rounded-full cursor-pointer transition-all"
                    style={{
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
          <div className="flex-1 overflow-y-auto">
            {partiesLoading ? (
              <div className="p-6 text-center text-ink2 text-[12px]">Loading…</div>
            ) : sidebarParties.length === 0 ? (
              <div className="p-6 text-center text-ink2 text-[12px]">No parties match</div>
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

        {/* ── Main panel ── */}
        <main className="overflow-y-auto min-w-0">

          {/* Mobile sidebar toggle + breadcrumb */}
          <div className="md:hidden flex items-center gap-2.5 px-4 py-2.5 border-b border-pageborder bg-surface">
            <button
              onClick={() => setSidebarOpen(true)}
              className="text-[12px] font-bold text-ink2 bg-pagebg border border-pageborder rounded px-3 py-1.5 cursor-pointer"
            >
              ☰ All Parties
            </button>
            {detailData && (
              <span className="text-[13px] font-bold" style={{ color: partyColor }}>{detailData.code}</span>
            )}
          </div>

          {!code || !detailData ? (
            <div className="flex items-center justify-center h-[60vh] flex-col gap-3">
              {detailLoading ? (
                <>
                  <div className="w-9 h-9 rounded-full border-[3px] border-pageborder"
                    style={{ borderTopColor: '#C8A84B', animation: 'spin 0.8s linear infinite' }} />
                  <p className="text-ink2 text-[13px]">Loading party data…</p>
                  <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
                </>
              ) : (
                <>
                  <div className="text-[32px]">🏛</div>
                  <p className="text-ink2 text-[14px]">Select a party from the sidebar</p>
                </>
              )}
            </div>
          ) : (
            <div className="px-4 md:px-8 py-5 pb-10">

              {/* ── Party header ── */}
              <div className="bg-surface rounded-xl px-5 py-4 mb-5 shadow-sm">
                <div className="flex items-start gap-3.5">
                  {/* Party circle */}
                  <div className="w-12 h-12 rounded-full flex items-center justify-center text-[14px] font-black text-white shrink-0"
                    style={{ background: partyColor }}>
                    {partyAbbr(detailData.code)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h1 className="font-sans text-[22px] font-bold text-ink leading-tight">
                        {detailData.code}
                      </h1>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                        style={{ background: allianceColor + '20', color: allianceColor }}>
                        {detailData.alliance}
                      </span>
                    </div>
                    <div className="text-[13px] text-ink2 mb-4">{detailData.full_name}</div>

                    {/* Stats — mirrors HomePage alliance row */}
                    <div className="flex items-end gap-0 overflow-x-auto custom-scrollbar pb-1 -mb-1">
                      {[
                        { label: 'Won', value: liveSummary.won, color: partyColor },
                        { label: '2nd', value: liveSummary.second, color: '#1A1611' },
                        { label: 'Close 3rd', value: liveSummary.close3rd, color: '#F59E0B', desc: '< 10k margin' },
                        { label: 'Dist. 3rd', value: liveSummary.distant3rd, color: '#6B7280', desc: '≥ 10k margin' },
                        { label: 'Contested', value: liveSummary.contested, color: '#6B7280' },
                      ].map((s, i, arr) => (
                        <div key={s.label} className={`px-4 md:px-5 shrink-0 ${i < arr.length - 1 ? 'border-r border-pageborder' : ''}`}>
                          <div className="w-2 h-2 mb-1.5" style={{ backgroundColor: s.color }} />
                          <div className="text-[12px] font-semibold mb-0.5" style={{ color: s.color }}>{s.label}</div>
                          <div className="font-sans font-bold text-[20px] leading-none" style={{ color: s.color }}>{s.value}</div>
                          {s.desc && <div className="text-[9px] text-ink2 mt-1 whitespace-nowrap font-medium">{s.desc}</div>}
                        </div>
                      ))}
                      <div className="px-4 md:px-5 shrink-0">
                        <div className="w-2 h-2 mb-1.5 bg-ink" />
                        <div className="text-[12px] font-semibold mb-0.5 text-ink">Vote Share</div>
                        <div className="font-sans font-bold text-[20px] leading-none text-ink">
                          {liveSummary.totalValid > 0 ? (liveSummary.totalVotes / liveSummary.totalValid * 100).toFixed(1) : '—'}%
                        </div>
                        <div className="text-[11px] font-bold mt-0.5" style={{ color: swingVs2021 >= 0 ? '#16A34A' : '#DC2626' }}>
                          {swingVs2021 >= 0 ? '▲' : '▼'}{Math.abs(swingVs2021).toFixed(1)}% vs 2021
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* ── Trend Analysis ── */}
              <div className="mb-6">
                <h2 className="text-[11px] font-bold tracking-widest uppercase text-ink2 mb-3">Vote & Share Trends (vs 2021)</h2>
                <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
                  {[
                    { label: 'Share Up', value: liveSummary.shareInc, color: '#16A34A', desc: '> 0.1% increase' },
                    { label: 'Share Held', value: liveSummary.shareHeld, color: '#6B7280', desc: '± 0.1% change' },
                    { label: 'Share Down', value: liveSummary.shareDec, color: '#DC2626', desc: '> 0.1% decrease' },
                    { label: 'Votes Up', value: liveSummary.votesInc, color: '#16A34A', desc: 'Absolute increase' },
                    { label: 'Votes Held', value: liveSummary.votesHeld, color: '#6B7280', desc: 'No change' },
                    { label: 'Votes Down', value: liveSummary.votesDec, color: '#DC2626', desc: 'Absolute decrease' },
                  ].map(s => (
                    <div key={s.label} className="bg-surface rounded-xl px-3.5 py-2.5 shadow-sm border border-pageborder/50">
                      <div className="font-mono text-[22px] font-black leading-none mb-1" style={{ color: s.color }}>{s.value}</div>
                      <div className="text-[11px] font-bold text-ink truncate">{s.label}</div>
                      <div className="text-[9px] text-ink2 mt-0.5 whitespace-nowrap">{s.desc}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* ── Constituency cards ── */}
              <div>
                <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
                  <h2 className="text-[11px] font-bold tracking-widest uppercase text-ink2">
                    Constituencies · {filteredConsts.length} / {enrichedConsts.length}
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
                        border: `1px solid ${rawProfile === p ? partyColor : '#D1CBC4'}`,
                        background: rawProfile === p ? partyColor : 'transparent',
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
                  <span className="text-[10px] font-bold text-ink2 ml-1">Win Margin:</span>
                  {[{ k: 'safe', l: 'Safe 10k+' }, { k: 'comfortable', l: '2–10k' }, { k: 'close', l: '<2k' }].map(({ k, l }) => (
                    <button key={k}
                      onClick={() => setRawMargin(rawMargin === k ? null : k)}
                      className="text-[10px] px-2.5 py-1 rounded-full cursor-pointer border font-medium transition-all"
                      style={{
                        border: `1px solid ${rawMargin === k ? '#16A34A' : '#D1CBC4'}`,
                        background: rawMargin === k ? '#16A34A' : 'transparent',
                        color: rawMargin === k ? '#fff' : '#5C5245',
                      }}>{l}</button>
                  ))}
                  
                  <span className="text-[10px] font-bold text-ink2 ml-1">Loss Margin:</span>
                  {[{ k: 'lost_safe', l: 'Large 10k+' }, { k: 'lost_comfortable', l: '2–10k' }, { k: 'lost_close', l: '<2k' }].map(({ k, l }) => (
                    <button key={k}
                      onClick={() => setRawMargin(rawMargin === k ? null : k)}
                      className="text-[10px] px-2.5 py-1 rounded-full cursor-pointer border font-medium transition-all"
                      style={{
                        border: `1px solid ${rawMargin === k ? '#DC2626' : '#D1CBC4'}`,
                        background: rawMargin === k ? '#DC2626' : 'transparent',
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

                {filteredConsts.length === 0 ? (
                  <div className="text-center py-10 text-ink2 text-[13px]">No constituencies match</div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: 10 }}>
                    {filteredConsts.map(c => (
                      <PartyConstCard
                        key={c.id}
                        c={c}
                        seatCls={c.seatClass}
                        ownerAl={c.ownerAlliance}
                        partyCode={detailData.code}
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
