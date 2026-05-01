import { Link, useParams } from 'react-router-dom';
import { useConstituencyDetail, useHistoricalComparison } from '../hooks/useElectionData';
import type { Alliance } from '../types';

// ── Alliance colours (match HTML reference) ──────────────────
const ALLIANCE_COLOR: Record<string, string> = {
  LDF: '#D42B2B',
  UDF: '#1A8FE3',
  NDA: '#F7921C',
  OTH: '#6B7280',
};

const ALLIANCE_BG: Record<string, string> = {
  LDF: 'rgba(212,43,43,0.07)',
  UDF: 'rgba(26,143,227,0.07)',
  NDA: 'rgba(247,146,28,0.07)',
  OTH: 'rgba(107,114,128,0.06)',
};

function allianceColor(a: string) {
  return ALLIANCE_COLOR[a] || '#6B7280';
}

// ── Status helpers ────────────────────────────────────────────
function statusDotClass(status: string) {
  if (status === 'RESULT_DECLARED') return 'dot-done';
  if (status === 'IN_PROGRESS') return 'dot-live';
  return 'dot-pending';
}

function statusLabel(status: string) {
  if (status === 'RESULT_DECLARED') return 'Declared';
  if (status === 'IN_PROGRESS') return 'Counting';
  return 'Awaited';
}

// ── Counting progress helpers ─────────────────────────────────
function countingPct(live: { rounds_completed: number; total_rounds: number } | null | undefined): number {
  if (!live || live.total_rounds === 0) return 0;
  return Math.round((live.rounds_completed / live.total_rounds) * 100);
}

function roundsLabel(live: { rounds_completed: number; total_rounds: number; status: string } | null | undefined): string {
  if (!live) return 'Awaited';
  if (live.status === 'COMPLETED') return 'All rounds complete';
  if (live.status === 'NOT_STARTED') return 'Not started';
  return `Round ${live.rounds_completed} of ${live.total_rounds}`;
}

// ── Main page ─────────────────────────────────────────────────
export default function ConstituencyPage() {
  const { id } = useParams<{ id: string }>();
  const constituencyId = id ? parseInt(id) : null;

  const { data: constituency, loading } = useConstituencyDetail(constituencyId);
  const { data: historical, loading: historicalLoading } = useHistoricalComparison(
    constituency?.constituency.number || null
  );

  // ── Loading ──
  if (loading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: 'var(--bg, #F5F2EE)' }}
      >
        <div className="text-center">
          <div
            className="animate-spin rounded-full h-10 w-10 border-b-2 mx-auto mb-4"
            style={{ borderColor: '#C8A84B' }}
          />
          <p style={{ color: '#5C5245', fontFamily: "'DM Sans', sans-serif", fontSize: 13 }}>
            Loading constituency…
          </p>
        </div>
      </div>
    );
  }

  // ── Not found ──
  if (!constituency) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: 'var(--bg, #F5F2EE)' }}
      >
        <div className="text-center">
          <p style={{ color: '#5C5245', fontFamily: "'DM Sans', sans-serif" }}>
            Constituency not found
          </p>
          <Link
            to="/"
            style={{ color: '#1A8FE3', fontSize: 13, display: 'inline-block', marginTop: 12 }}
          >
            ← Back to all constituencies
          </Link>
        </div>
      </div>
    );
  }

  const { constituency: c, candidates_2026, live_result } = constituency;
  const pct = countingPct(live_result);

  const maxVotes =
    candidates_2026.length > 0 ? Math.max(...candidates_2026.map((cd) => cd.votes)) : 1;

  return (
    <div style={{ fontFamily: "'DM Sans', sans-serif", background: '#F5F2EE', minHeight: '100vh' }}>

      {/* ── DETAIL HEADER ───────────────────────────────────── */}
      <div
        style={{
          background: '#FDFCFB',
          borderBottom: '1px solid #E2DDD8',
          padding: '24px 32px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          gap: 20,
        }}
      >
        {/* Left: back + title */}
        <div>
          <Link
            to="/"
            style={{ color: '#1A8FE3', fontSize: 12, display: 'inline-block', marginBottom: 8 }}
          >
            ← All constituencies
          </Link>
          <div
            style={{
              fontFamily: "'DM Serif Display', serif",
              fontSize: 28,
              letterSpacing: '-0.4px',
              color: '#1A1611',
              marginBottom: 6,
              lineHeight: 1.15,
            }}
          >
            {c.name}
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <MetaChip>{c.district} District</MetaChip>
            <MetaChip># {c.number}</MetaChip>
            {live_result && (
              <MetaChip>
                <span
                  className="status-dot"
                  style={{
                    display: 'inline-block',
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    marginRight: 5,
                    background:
                      live_result.status === 'COMPLETED'
                        ? '#6B7280'
                        : live_result.status === 'IN_PROGRESS'
                        ? '#22c55e'
                        : '#D1D5DB',
                    verticalAlign: 'middle',
                  }}
                />
                {statusLabel(live_result.status)}
              </MetaChip>
            )}
          </div>
        </div>

        {/* Right: counting progress */}
        {live_result && (
          <div style={{ textAlign: 'right', flexShrink: 0 }}>
            <div
              style={{
                fontFamily: "'DM Serif Display', serif",
                fontSize: 36,
                color: '#1A1611',
                lineHeight: 1,
              }}
            >
              {pct}%
            </div>
            <div style={{ fontSize: 11, color: '#5C5245', marginTop: 2 }}>votes counted</div>
            <div
              style={{
                width: 140,
                height: 5,
                background: '#E2DDD8',
                borderRadius: 3,
                overflow: 'hidden',
                marginTop: 8,
                marginLeft: 'auto',
              }}
            >
              <div
                style={{
                  height: '100%',
                  width: `${pct}%`,
                  background: '#22c55e',
                  borderRadius: 3,
                  transition: 'width 0.8s ease',
                }}
              />
            </div>
            <div style={{ fontSize: 11, color: '#5C5245', marginTop: 5 }}>
              {roundsLabel(live_result)}
            </div>
          </div>
        )}
      </div>

      {/* ── COUNTING STATS BAR ──────────────────────────────── */}
      {live_result && (
        <div
          style={{
            background: '#FDFCFB',
            borderBottom: '1px solid #E2DDD8',
            padding: '14px 32px',
            display: 'flex',
            gap: 32,
            flexWrap: 'wrap',
          }}
        >
          {[
            ['Total Electors', live_result.total_electors.toLocaleString('en-IN')],
            ['Votes Polled', live_result.votes_polled.toLocaleString('en-IN')],
            ['Votes Counted', live_result.votes_counted.toLocaleString('en-IN')],
            ['Valid Votes', live_result.valid_votes.toLocaleString('en-IN')],
          ].map(([label, value]) => (
            <div key={label}>
              <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#5C5245', marginBottom: 3 }}>
                {label}
              </div>
              <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 16, fontWeight: 600, color: '#1A1611' }}>
                {value}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── CURRENT RESULTS ─────────────────────────────────── */}
      <div style={{ padding: '24px 32px' }}>
        <SectionTitle>Current Results</SectionTitle>

        {candidates_2026.length === 0 ? (
          <p style={{ color: '#5C5245', fontSize: 13 }}>No candidate data available yet</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {candidates_2026.map((cd, i) => {
              const color = allianceColor(cd.alliance);
              const isTop = cd.is_winner || cd.is_leading;
              const barW = maxVotes > 0 ? Math.round((cd.votes / maxVotes) * 100) : 0;
              const partyAbbr = cd.party.replace('(M)', '').replace('(J)', '').substring(0, 3);

              return (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 14,
                    padding: '14px 16px',
                    background: isTop ? ALLIANCE_BG[cd.alliance] || '#FFF' : '#FDFCFB',
                    borderRadius: 10,
                    border: `1.5px solid ${isTop ? color : '#E2DDD8'}`,
                    transition: 'border-color 0.15s',
                  }}
                >
                  {/* Party circle */}
                  <div
                    style={{
                      width: 38,
                      height: 38,
                      borderRadius: '50%',
                      background: color,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 11,
                      fontWeight: 700,
                      color: '#fff',
                      flexShrink: 0,
                      letterSpacing: '0.3px',
                    }}
                  >
                    {partyAbbr}
                  </div>

                  {/* Name + party */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: 14,
                        fontWeight: 600,
                        color: '#1A1611',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        flexWrap: 'wrap',
                      }}
                    >
                      {cd.name}
                      {cd.is_winner && (
                        <span
                          style={{
                            fontSize: 9,
                            fontWeight: 700,
                            letterSpacing: 1,
                            textTransform: 'uppercase',
                            background: '#15803D',
                            color: '#fff',
                            padding: '2px 7px',
                            borderRadius: 3,
                          }}
                        >
                          ✓ Winner
                        </span>
                      )}
                      {cd.is_leading && !cd.is_winner && (
                        <span
                          style={{
                            fontSize: 9,
                            fontWeight: 700,
                            letterSpacing: 1,
                            textTransform: 'uppercase',
                            background: '#1D4ED8',
                            color: '#fff',
                            padding: '2px 7px',
                            borderRadius: 3,
                          }}
                        >
                          ▲ Leading
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 11, color: '#5C5245', marginTop: 2 }}>
                      {cd.party} · {cd.alliance}
                    </div>
                  </div>

                  {/* Vote bar */}
                  <div style={{ flex: 1, maxWidth: 200 }}>
                    <div
                      style={{
                        fontSize: 10,
                        color: '#5C5245',
                        marginBottom: 3,
                        fontFamily: "'JetBrains Mono', monospace",
                      }}
                    >
                      {cd.percentage.toFixed(1)}%
                    </div>
                    <div
                      style={{
                        height: 6,
                        background: '#E2DDD8',
                        borderRadius: 3,
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          height: '100%',
                          width: `${barW}%`,
                          background: color,
                          borderRadius: 3,
                          transition: 'width 0.8s ease',
                        }}
                      />
                    </div>
                  </div>

                  {/* Vote count */}
                  <div style={{ textAlign: 'right', minWidth: 90, flexShrink: 0 }}>
                    <div
                      style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 20,
                        fontWeight: 600,
                        color: '#1A1611',
                        letterSpacing: '-0.5px',
                      }}
                    >
                      {cd.votes.toLocaleString('en-IN')}
                    </div>
                    <div style={{ fontSize: 11, color: '#5C5245' }}>votes</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── HISTORICAL COMPARISON ───────────────────────────── */}
      {!historicalLoading && historical && (
        <div style={{ padding: '0 32px 32px' }}>
          <div style={{ height: 1, background: '#E2DDD8', marginBottom: 24 }} />
          <SectionTitle>Historical Comparison</SectionTitle>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: 14,
            }}
          >
            {/* 2021 LA */}
            {historical.la_2021 && (
              <HistCard title="2021 Assembly">
                {historical.la_2021.winner && (
                  <>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#1A1611', marginBottom: 2 }}>
                      {historical.la_2021.winner}
                    </div>
                    <div style={{ fontSize: 12, color: '#5C5245' }}>
                      {historical.la_2021.party}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8, fontSize: 12 }}>
                      <div
                        style={{
                          width: 10,
                          height: 10,
                          borderRadius: 2,
                          background: '#D42B2B',
                          flexShrink: 0,
                        }}
                      />
                      {historical.la_2021.top_5[0] && (
                        <span>
                          {historical.la_2021.top_5[0].votes.toLocaleString('en-IN')} votes ·{' '}
                          {historical.la_2021.top_5[0].percentage.toFixed(1)}%
                        </span>
                      )}
                    </div>
                    {historical.la_2021.margin != null && (
                      <div style={{ marginTop: 10, fontSize: 12, color: '#5C5245', display: 'flex', gap: 16 }}>
                        <span>
                          Margin{' '}
                          <strong style={{ color: '#1A1611' }}>
                            {historical.la_2021.margin.toLocaleString('en-IN')}
                          </strong>
                        </span>
                      </div>
                    )}
                  </>
                )}
                {/* Top 5 mini list */}
                <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {historical.la_2021.top_5.slice(0, 4).map((cand, i) => (
                    <div
                      key={i}
                      style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: i === 0 ? '#1A1611' : '#5C5245' }}
                    >
                      <span style={{ fontWeight: i === 0 ? 600 : 400 }}>{cand.candidate}</span>
                      <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                        {cand.votes.toLocaleString('en-IN')}
                      </span>
                    </div>
                  ))}
                </div>
              </HistCard>
            )}

            {/* 2024 LS */}
            {historical.ls_2024 && (
              <HistCard title="2024 Lok Sabha">
                <div style={{ fontSize: 12, color: '#5C5245', marginBottom: 12 }}>
                  {historical.ls_2024.parliament_constituency}
                </div>
                <AllianceShareBars
                  items={[
                    { alliance: 'UDF', votes: historical.ls_2024.udf_votes, leading: historical.ls_2024.lead_alliance === 'UDF' },
                    { alliance: 'LDF', votes: historical.ls_2024.ldf_votes, leading: historical.ls_2024.lead_alliance === 'LDF' },
                    { alliance: 'NDA', votes: historical.ls_2024.nda_votes, leading: historical.ls_2024.lead_alliance === 'NDA' },
                  ]}
                />
              </HistCard>
            )}

            {/* 2019 LS */}
            {historical.ls_2019 && (
              <HistCard title="2019 Lok Sabha">
                <div style={{ fontSize: 12, color: '#5C5245', marginBottom: 12 }}>
                  {historical.ls_2019.parliament_constituency}
                </div>
                <AllianceShareBars
                  items={[
                    { alliance: 'UDF', votes: historical.ls_2019.udf_votes, leading: historical.ls_2019.lead_alliance === 'UDF' },
                    { alliance: 'LDF', votes: historical.ls_2019.ldf_votes, leading: historical.ls_2019.lead_alliance === 'LDF' },
                    { alliance: 'NDA', votes: historical.ls_2019.nda_votes, leading: historical.ls_2019.lead_alliance === 'NDA' },
                  ]}
                />
              </HistCard>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Small reusable components ─────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: '2px',
        textTransform: 'uppercase',
        color: '#5C5245',
        marginBottom: 14,
      }}
    >
      {children}
    </div>
  );
}

function MetaChip({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        background: '#F5F2EE',
        border: '1px solid #E2DDD8',
        borderRadius: 5,
        padding: '3px 9px',
        fontSize: 11,
        color: '#5C5245',
        fontWeight: 500,
        display: 'inline-flex',
        alignItems: 'center',
      }}
    >
      {children}
    </span>
  );
}

function HistCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      style={{
        background: '#FDFCFB',
        border: '1px solid #E2DDD8',
        borderRadius: 10,
        padding: 16,
      }}
    >
      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: '1.5px',
          color: '#5C5245',
          textTransform: 'uppercase',
          marginBottom: 10,
        }}
      >
        {title}
      </div>
      {children}
    </div>
  );
}

function AllianceShareBars({
  items,
}: {
  items: { alliance: string; votes: number; leading: boolean }[];
}) {
  const max = Math.max(...items.map((x) => x.votes), 1);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {items.map(({ alliance, votes, leading }) => {
        const color = allianceColor(alliance);
        const w = Math.round((votes / max) * 100);
        return (
          <div
            key={alliance}
            style={{
              padding: '8px 10px',
              borderRadius: 6,
              border: leading ? `1.5px solid ${color}` : '1.5px solid transparent',
              background: leading ? ALLIANCE_BG[alliance] : 'transparent',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontWeight: 600, fontSize: 12, color: '#1A1611' }}>{alliance}</span>
              <span
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontWeight: 600,
                  fontSize: 12,
                  color: '#1A1611',
                }}
              >
                {votes.toLocaleString('en-IN')}
              </span>
            </div>
            <div style={{ height: 5, background: '#E2DDD8', borderRadius: 3, overflow: 'hidden' }}>
              <div
                style={{
                  height: '100%',
                  width: `${w}%`,
                  background: color,
                  borderRadius: 3,
                  transition: 'width 0.6s ease',
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
