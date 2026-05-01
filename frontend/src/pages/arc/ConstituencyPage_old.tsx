import { useParams, Link } from 'react-router-dom';
import { useConstituencyDetail, useHistoricalComparison } from '../hooks/useElectionData';
import type { Alliance } from '../types';

function ConstituencyPage() {
  const { id } = useParams<{ id: string }>();
  const constituencyId = id ? parseInt(id) : null;
  
  const { data: constituency, loading } = useConstituencyDetail(constituencyId);
  const { data: historical, loading: historicalLoading } = useHistoricalComparison(
    constituency?.constituency.number || null
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-neutral-600">Loading constituency data...</p>
        </div>
      </div>
    );
  }

  if (!constituency) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-xl text-neutral-600">Constituency not found</p>
          <Link to="/" className="text-blue-600 hover:underline mt-4 inline-block">
            ← Back to home
          </Link>
        </div>
      </div>
    );
  }

  const allianceBadgeClasses = {
    UDF: 'badge-udf',
    LDF: 'badge-ldf',
    NDA: 'badge-nda',
    OTH: 'badge-oth',
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <Link to="/" className="text-blue-600 hover:underline text-sm mb-2 inline-block">
            ← Back to all constituencies
          </Link>
          <h1 className="text-3xl font-bold text-neutral-900">
            {constituency.constituency.number}. {constituency.constituency.name}
          </h1>
          <p className="text-neutral-600 mt-1">{constituency.constituency.district} District</p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Live Results Status */}
        {constituency.live_result && (
          <div className="card mb-8">
            <h2 className="text-xl font-bold mb-4">Counting Status</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatusItem 
                label="Total Electors" 
                value={constituency.live_result.total_electors.toLocaleString()} 
              />
              <StatusItem 
                label="Votes Polled" 
                value={constituency.live_result.votes_polled.toLocaleString()} 
              />
              <StatusItem 
                label="Votes Counted" 
                value={constituency.live_result.votes_counted.toLocaleString()} 
              />
              <StatusItem 
                label="Valid Votes" 
                value={constituency.live_result.valid_votes.toLocaleString()} 
              />
              <StatusItem 
                label="Rounds Completed" 
                value={`${constituency.live_result.rounds_completed} / ${constituency.live_result.total_rounds}`} 
              />
              <StatusItem 
                label="Status" 
                value={constituency.live_result.status.replace('_', ' ')} 
              />
            </div>
          </div>
        )}

        {/* 2026 Results */}
        <div className="card mb-8">
          <h2 className="text-xl font-bold mb-4">2026 Results</h2>
          {constituency.candidates_2026.length === 0 ? (
            <p className="text-neutral-600">No candidates data available yet</p>
          ) : (
            <div className="space-y-3">
              {constituency.candidates_2026.map((candidate, index) => (
                <div 
                  key={index}
                  className={`flex items-center justify-between p-4 rounded-lg border-2 ${
                    candidate.is_winner 
                      ? 'border-green-500 bg-green-50' 
                      : candidate.is_leading 
                      ? 'border-yellow-500 bg-yellow-50' 
                      : 'border-neutral-200 bg-white'
                  }`}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      {candidate.is_winner && (
                        <span className="text-green-600 font-bold text-xl">✓</span>
                      )}
                      {candidate.is_leading && !candidate.is_winner && (
                        <span className="text-yellow-600 font-bold text-xl">→</span>
                      )}
                      <span className="font-semibold text-lg">{candidate.name}</span>
                      <span className={allianceBadgeClasses[candidate.alliance as Alliance]}>
                        {candidate.alliance}
                      </span>
                      <span className="text-neutral-600">({candidate.party})</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold">{candidate.votes.toLocaleString()}</p>
                    <p className="text-sm text-neutral-600">{candidate.percentage.toFixed(2)}%</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Historical Comparison */}
        {!historicalLoading && historical && (
          <div className="grid md:grid-cols-2 gap-8">
            {/* 2021 LA Results */}
            <div className="card">
              <h2 className="text-xl font-bold mb-4">2021 Assembly Election</h2>
              {historical.la_2021.winner && (
                <div className="mb-4 p-3 bg-green-50 rounded-lg">
                  <p className="text-sm text-neutral-600">Winner</p>
                  <p className="font-bold text-lg">{historical.la_2021.winner}</p>
                  <p className="text-neutral-600">
                    {historical.la_2021.party} • Margin: {historical.la_2021.margin?.toLocaleString()}
                  </p>
                </div>
              )}
              <div className="space-y-2">
                {historical.la_2021.top_5.map((candidate, index) => (
                  <div key={index} className="flex justify-between py-2 border-b border-neutral-200 last:border-0">
                    <div>
                      <span className="font-medium">{candidate.candidate}</span>
                      <span className="text-neutral-600 text-sm ml-2">({candidate.party})</span>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold">{candidate.votes.toLocaleString()}</p>
                      <p className="text-sm text-neutral-600">{candidate.percentage.toFixed(2)}%</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Parliament Results */}
            <div className="space-y-6">
              {/* 2024 LS */}
              {historical.ls_2024 && (
                <div className="card">
                  <h2 className="text-xl font-bold mb-4">2024 Lok Sabha</h2>
                  <p className="text-sm text-neutral-600 mb-3">
                    {historical.ls_2024.parliament_constituency}
                  </p>
                  <div className="space-y-2">
                    {(() => { const max = Math.max(historical.ls_2024.udf_votes, historical.ls_2024.ldf_votes, historical.ls_2024.nda_votes); return (<>
                    <AllianceBar 
                      alliance="UDF" 
                      votes={historical.ls_2024.udf_votes}
                      isLeader={historical.ls_2024.lead_alliance === 'UDF'}
                      maxVotes={max}
                    />
                    <AllianceBar 
                      alliance="LDF" 
                      votes={historical.ls_2024.ldf_votes}
                      isLeader={historical.ls_2024.lead_alliance === 'LDF'}
                      maxVotes={max}
                    />
                    <AllianceBar 
                      alliance="NDA" 
                      votes={historical.ls_2024.nda_votes}
                      isLeader={historical.ls_2024.lead_alliance === 'NDA'}
                      maxVotes={max}
                    />
                    </>); })()}
                  </div>
                </div>
              )}

              {/* 2019 LS */}
              {historical.ls_2019 && (
                <div className="card">
                  <h2 className="text-xl font-bold mb-4">2019 Lok Sabha</h2>
                  <p className="text-sm text-neutral-600 mb-3">
                    {historical.ls_2019.parliament_constituency}
                  </p>
                  <div className="space-y-2">
                    {(() => { const max = Math.max(historical.ls_2019.udf_votes, historical.ls_2019.ldf_votes, historical.ls_2019.nda_votes); return (<>
                    <AllianceBar 
                      alliance="UDF" 
                      votes={historical.ls_2019.udf_votes}
                      isLeader={historical.ls_2019.lead_alliance === 'UDF'}
                      maxVotes={max}
                    />
                    <AllianceBar 
                      alliance="LDF" 
                      votes={historical.ls_2019.ldf_votes}
                      isLeader={historical.ls_2019.lead_alliance === 'LDF'}
                      maxVotes={max}
                    />
                    <AllianceBar 
                      alliance="NDA" 
                      votes={historical.ls_2019.nda_votes}
                      isLeader={historical.ls_2019.lead_alliance === 'NDA'}
                      maxVotes={max}
                    />
                    </>); })()}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// Status Item Component
function StatusItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-sm text-neutral-600">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}

// Alliance Bar Component
function AllianceBar({ 
  alliance, 
  votes, 
  isLeader,
  maxVotes 
}: { 
  alliance: Alliance; 
  votes: number; 
  isLeader: boolean;
  maxVotes: number;
}) {
  const allianceColors = {
    UDF: 'bg-udf',
    LDF: 'bg-ldf',
    NDA: 'bg-nda',
    OTH: 'bg-gray-400',
  };

  const widthPct = maxVotes > 0 ? Math.round((votes / maxVotes) * 100) : 0;

  return (
    <div className={`p-3 rounded ${isLeader ? 'ring-2 ring-offset-2 ring-green-500' : ''}`}>
      <div className="flex justify-between mb-1">
        <span className="font-semibold">{alliance}</span>
        <span className="font-bold">{votes.toLocaleString()}</span>
      </div>
      <div className="w-full bg-neutral-200 rounded-full h-2">
        <div 
          className={`${allianceColors[alliance]} h-2 rounded-full transition-all duration-500`}
          style={{ width: `${widthPct}%` }}
        ></div>
      </div>
    </div>
  );
}

export default ConstituencyPage;
