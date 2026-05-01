import type { Region, ConstituencyListItem, Alliance } from '../types';

const ALLIANCE_COLORS: Record<string, string> = {
  LDF: '#D42B2B', UDF: '#1A8FE3', NDA: '#F7921C', OTH: '#9CA3AF',
};

export const REGION_META: { key: Region; label: string; subtitle: string }[] = [
  { key: 'north', label: 'North', subtitle: 'Malabar' },
  { key: 'central_north', label: 'Central North', subtitle: '' },
  { key: 'south_central', label: 'South Central', subtitle: '' },
  { key: 'south', label: 'South', subtitle: 'Travancore' },
];

export const DISTRICT_ORDER = [
  'Kasaragod','Kannur','Wayanad','Kozhikode',
  'Malappuram','Palakkad','Thrissur',
  'Ernakulam','Idukki','Kottayam',
  'Alappuzha','Pathanamthitta','Kollam','Thiruvananthapuram',
];

export const DISTRICT_REGION: Record<string, Region> = {
  Kasaragod:'north', Kannur:'north', Wayanad:'north', Kozhikode:'north',
  Malappuram:'central_north', Palakkad:'central_north', Thrissur:'central_north',
  Ernakulam:'south_central', Idukki:'south_central', Kottayam:'south_central',
  Alappuzha:'south', Pathanamthitta:'south', Kollam:'south', Thiruvananthapuram:'south',
};

function regionTally(list: ConstituencyListItem[], region: Region) {
  const inRegion = list.filter(c => c.region === region);
  const t = { LDF: 0, UDF: 0, NDA: 0, OTH: 0, total: inRegion.length };
  inRegion.forEach(c => {
    const live = c.status === 'IN_PROGRESS' || c.status === 'RESULT_DECLARED';
    if (live && c.leader) t[c.leader.alliance as Alliance] = (t[c.leader.alliance as Alliance] || 0) + 1;
  });
  return t;
}

interface Props {
  constituencies: ConstituencyListItem[];
  activeRegion: Region | null;
  onRegionClick: (r: Region) => void;
}

export function RegionPanel({ constituencies, activeRegion, onRegionClick }: Props) {
  return (
    <div className="bg-surface px-8 py-3 border-b border-pageborder">
      <div className="grid grid-cols-4 gap-3">
        {REGION_META.map(rm => {
          const t = regionTally(constituencies, rm.key);
          const ranked = (['LDF','UDF','NDA'] as const).map(a => ({ a, s: t[a] })).sort((a,b) => b.s - a.s);
          const top = ranked[0].s > 0 ? ranked[0].a : null;
          const bgTint = top ? `${ALLIANCE_COLORS[top]}12` : 'transparent';
          const isActive = activeRegion === rm.key;
          return (
            <div
              key={rm.key}
              onClick={() => onRegionClick(rm.key)}
              className={`rounded-xl p-3.5 cursor-pointer border-2 transition-all duration-200 hover:shadow-md ${isActive ? 'border-ink shadow-lg' : 'border-transparent'}`}
              style={{ backgroundColor: bgTint }}
            >
              <div className="flex items-baseline gap-1.5 mb-2">
                <span className="text-[13px] font-bold text-ink">{rm.label}</span>
                {rm.subtitle && <span className="text-[11px] text-ink2">{rm.subtitle}</span>}
              </div>
              {ranked.map(al => (
                <div key={al.a} className="flex items-center justify-between mb-0.5">
                  <span className="text-[11px] font-semibold" style={{ color: ALLIANCE_COLORS[al.a] }}>{al.a}</span>
                  <span className="text-[12px] font-bold text-ink font-mono">{al.s}</span>
                </div>
              ))}
              <div className="text-[10px] text-ink2 mt-1.5">{t.total} seats</div>
              {isActive && <div className="h-[2px] bg-ink rounded-full mt-2" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
