import type { ConstituencyListItem } from '../types';

const ALLIANCE_COLORS: Record<string, string> = {
  LDF: '#D42B2B', UDF: '#1A8FE3', NDA: '#F7921C', OTH: '#9CA3AF',
};

// Full-bleed background tints per alliance
const ALLIANCE_BG: Record<string, string> = {
  LDF: 'rgba(212,43,43,0.10)',
  UDF: 'rgba(26,143,227,0.10)',
  NDA: 'rgba(247,146,28,0.10)',
  OTH: 'rgba(156,163,175,0.10)',
};

const ALLIANCE_BORDER: Record<string, string> = {
  LDF: '#D42B2B', UDF: '#1A8FE3', NDA: '#F7921C', OTH: '#9CA3AF',
};

interface Props {
  c: ConstituencyListItem;
  isActive: boolean;
  onClick: () => void;
}

export function SidebarCard({ c, isActive, onClick }: Props) {
  const isLive = c.status === 'IN_PROGRESS';
  const isDone = c.status === 'RESULT_DECLARED';
  const countingStarted = isLive || isDone;
  const alliance = c.leader?.alliance || null;

  const margin = (c.leader && c.runner_up && countingStarted)
    ? c.leader.votes - c.runner_up.votes : 0;
  const isClose = countingStarted && margin < 500 && !isDone && margin >= 0;

  // Base style
  const borderColor = isClose ? '#F59E0B' : alliance && countingStarted ? ALLIANCE_BORDER[alliance] : '#E2DDD8';
  const bgColor = isActive
    ? (alliance && countingStarted ? ALLIANCE_BG[alliance] : 'rgba(0,0,0,0.04)')
    : (alliance && countingStarted ? ALLIANCE_BG[alliance] : 'transparent');

  return (
    <div
      onClick={onClick}
      className="flex items-center p-2.5 px-4 cursor-pointer border-b border-pageborder transition-all gap-2 hover:brightness-95"
      style={{
        backgroundColor: bgColor,
        borderLeft: `3px solid ${borderColor}`,
      }}
    >
      <div className="font-mono text-[10px] text-ink2 w-6 shrink-0">{String(c.number).padStart(3,'0')}</div>
      <div className="flex-1 min-w-0">
        <div className="text-[12px] font-semibold text-ink truncate">{c.name}</div>
        <div className="text-[10px] text-ink2 truncate">
          {c.sitting_party && <span style={{ color: c.sitting_alliance === 'LDF' ? '#D42B2B' : c.sitting_alliance === 'UDF' ? '#1A8FE3' : c.sitting_alliance === 'NDA' ? '#F7921C' : '#9CA3AF' }}>{c.sitting_party}</span>}
          {c.sitting_party && ' · '}{c.district}
        </div>
      </div>
      <div className="text-right shrink-0">
        {countingStarted && c.leader ? (
          <div className="text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ color: ALLIANCE_COLORS[c.leader.alliance], backgroundColor: ALLIANCE_BG[c.leader.alliance] }}>
            {c.leader.party}
          </div>
        ) : null}
        <div className="text-[10px] text-ink2 flex items-center justify-end mt-0.5">
          <span className="inline-block w-1.5 h-1.5 rounded-full mr-1" style={{ backgroundColor: isLive ? '#22c55e' : isDone ? '#6B7280' : '#D1D5DB' }} />
          {isLive ? 'Counting' : isDone ? 'Declared' : 'Awaited'}
        </div>
      </div>
    </div>
  );
}
