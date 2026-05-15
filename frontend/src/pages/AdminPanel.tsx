import { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';

function usePrevious<T>(value: T): T | undefined {
  const ref = useRef<T>();
  useEffect(() => {
    ref.current = value;
  }, [value]);
  return ref.current;
}

const API_BASE = 'http://localhost:8001/api';

interface ScrapeInfo {
  id: number;
  scraped_at: string;
  rounds_completed: number;
  total_rounds: number;
  is_final: boolean;
  match_status: string;
}

interface ConstituencyRow {
  number: number;
  name: string;
  district: string;
  latest_scrape: ScrapeInfo | null;
}

interface ScrapeMatch {
  id: number;
  eci_name: string;
  eci_party: string;
  eci_total_votes: number;
  eci_vote_percentage: number;
  eci_is_leading: boolean;
  is_nota: boolean;
  is_confirmed: boolean;
  candidate_id: number | null;
  candidate_name: string | null;
  candidate_party: string | null;
}

interface DBCandidate {
  id: number;
  name: string;
  party: string;
}

interface ScrapeDetail extends ScrapeInfo {
  constituency_number: number;
  constituency_name: string;
  matches: ScrapeMatch[];
}

interface StatusResponse {
  total: number;
  scraped: number;
  pending_match: number;
  committed: number;
  constituencies: ConstituencyRow[];
}

function AdminPanel() {
  const [password, setPassword] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Scraper state
  const [statusData, setStatusData] = useState<StatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [scraping, setScraping] = useState<number | 'all' | null>(null);
  const [testMode, setTestMode] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Inline scrape result view
  const [activeScrape, setActiveScrape] = useState<ScrapeDetail | null>(null);
  const [dbCandidates, setDbCandidates] = useState<DBCandidate[]>([]);
  const [pendingMatches, setPendingMatches] = useState<Record<number, string>>({});
  const [savingMatches, setSavingMatches] = useState(false);

  // Committing state
  const [committing, setCommitting] = useState<number | null>(null);

  // Clearing state
  const [clearing, setClearing] = useState<number | null>(null);

  // Deploy state
  const [deploying, setDeploying] = useState(false);

  const showToast = (type: 'success' | 'error', message: string) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 5000);
  };

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (password === 'admin2026') {
      setIsAuthenticated(true);
    } else {
      showToast('error', 'Invalid password');
    }
  };

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/scraper/status/`);
      const data = await res.json();
      setStatusData(data);
    } catch {
      showToast('error', 'Failed to load scraper status');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch status on mount
  useEffect(() => {
    if (isAuthenticated) fetchStatus();
  }, [isAuthenticated]);

  const prevStatusData = usePrevious(statusData);

  // Show toasts for newly matched constituencies
  useEffect(() => {
    if (prevStatusData && statusData) {
      statusData.constituencies.forEach((c) => {
        const prevC = prevStatusData.constituencies.find((pc) => pc.number === c.number);
        // If a new scrape appeared and it's MATCHED, OR an existing PENDING scrape turned into MATCHED
        if (
          c.latest_scrape?.match_status === 'MATCHED' &&
          (!prevC?.latest_scrape || prevC.latest_scrape.id !== c.latest_scrape.id || prevC.latest_scrape.match_status !== 'MATCHED')
        ) {
          showToast('success', `Scraped AC ${c.number} (${c.name}) — Round ${c.latest_scrape.rounds_completed}/${c.latest_scrape.total_rounds} — ✅ All candidates auto-matched`);
        }
      });
    }
  }, [statusData, prevStatusData]);

  // Poll status when scraping all
  useEffect(() => {
    let interval: number;
    if (scraping === 'all') {
      interval = window.setInterval(() => {
        fetchStatus();
      }, 3000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [scraping]);

  const handleViewDetails = async (scrapeId: number) => {
    try {
      const res = await fetch(`${API_BASE}/scraper/scrape/${scrapeId}/`);
      const data = await res.json();
      if (res.ok) {
        setActiveScrape(data.scrape);
        setDbCandidates(data.db_candidates);
        setPendingMatches({});
      } else {
        showToast('error', data.error || 'Failed to load details');
      }
    } catch {
      showToast('error', 'Network error');
    }
  };

  const handleSaveMatches = async () => {
    if (!activeScrape) return;
    setSavingMatches(true);
    try {
      const res = await fetch(`${API_BASE}/scraper/scrape/${activeScrape.id}/save-matches/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ matches: pendingMatches }),
      });
      const data = await res.json();
      if (res.ok) {
        showToast('success', `Saved ${data.updated} matches`);
        setActiveScrape(data.scrape);
        setPendingMatches({});
        fetchStatus();
      } else {
        showToast('error', data.error || 'Failed to save matches');
      }
    } catch {
      showToast('error', 'Network error');
    } finally {
      setSavingMatches(false);
    }
  };

  const handleScrape = async (acNumber: number | 'all') => {
    setScraping(acNumber);
    setActiveScrape(null);
    try {
      const res = await fetch(`${API_BASE}/scraper/run/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ac_number: acNumber, test_mode: testMode }),
      });
      const data = await res.json();

      if (!res.ok) {
        showToast('error', data.error || 'Scrape failed');
        setScraping(null);
        return;
      }

      if (acNumber === 'all') {
        showToast('success', '🚀 Scraping all constituencies in background. Auto-refreshing...');
        // Don't clear scraping state — let auto-refresh handle it
        setTimeout(() => setScraping(null), 120000); // clear after 2 min
      } else {
        showToast('success', `✅ Scraped AC ${acNumber} — ${data.scrape?.match_status}`);
        setActiveScrape(data.scrape);
        setScraping(null);
      }
      fetchStatus();
    } catch {
      showToast('error', 'Network error during scrape');
      setScraping(null);
    }
  };

  const handleCommit = async (scrapeId: number) => {
    setCommitting(scrapeId);
    try {
      const res = await fetch(`${API_BASE}/scraper/commit/${scrapeId}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await res.json();

      if (!res.ok) {
        showToast('error', data.error || 'Commit failed');
      } else {
        showToast('success', `✅ Committed ${data.committed} results for ${data.constituency}`);
        setActiveScrape(null);
        fetchStatus();
      }
    } catch {
      showToast('error', 'Network error during commit');
    } finally {
      setCommitting(null);
    }
  };

  const handleClear = async (acNumber: number) => {
    if (!window.confirm(`Clear all live data for AC #${acNumber}? This will reset votes and delete scrape records.`)) return;
    setClearing(acNumber);
    try {
      const res = await fetch(`${API_BASE}/scraper/clear/${acNumber}/`, { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        showToast('success', `🗑 Cleared AC #${acNumber} (${data.constituency}) — ${data.candidates_reset} candidates reset${data.rtdb_cleared ? ', RTDB cleared' : ''}`);
        if (activeScrape?.constituency_number === acNumber) setActiveScrape(null);
        fetchStatus();
      } else {
        showToast('error', data.error || 'Clear failed');
      }
    } catch {
      showToast('error', 'Network error during clear');
    } finally {
      setClearing(null);
    }
  };

  const handleDeploy = async () => {
    setDeploying(true);
    showToast('success', '🚀 Starting Firebase deployment... This may take a minute.');
    try {
      const res = await fetch(`${API_BASE}/scraper/deploy/`, {
        method: 'POST',
      });
      const data = await res.json();
      if (res.ok) {
        showToast('success', '✅ Successfully exported, built, and deployed to Firebase!');
      } else {
        showToast('error', data.error || 'Deployment failed');
      }
    } catch {
      showToast('error', 'Network error during deployment');
    } finally {
      setDeploying(false);
    }
  };

  const filteredConstituencies = statusData?.constituencies?.filter(c =>
    searchTerm === '' ||
    c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.district.toLowerCase().includes(searchTerm.toLowerCase()) ||
    String(c.number).includes(searchTerm)
  ) || [];

  // Login screen
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-[#0f1117] flex items-center justify-center">
        <div className="w-full max-w-sm">
          <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-2xl p-8 shadow-2xl">
            <div className="text-center mb-8">
              <div className="text-2xl font-bold text-white mb-1">🗳 Admin Panel</div>
              <div className="text-sm text-[#8b8fa3]">Kerala Elections 2026</div>
            </div>
            <form onSubmit={handleLogin}>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 bg-[#0f1117] border border-[#2a2d3a] rounded-xl text-white placeholder-[#555] focus:outline-none focus:border-[#4f8eff] transition-colors mb-4"
                placeholder="Enter password"
              />
              <button
                type="submit"
                className="w-full py-3 bg-gradient-to-r from-[#4f8eff] to-[#6c5ce7] text-white font-semibold rounded-xl hover:opacity-90 transition-opacity"
              >
                Login
              </button>
            </form>
            <Link to="/" className="block text-center text-[#4f8eff] text-sm mt-6 hover:underline">
              ← Back to results
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Main dashboard
  return (
    <div className="min-h-screen bg-[#0f1117] text-white flex flex-col">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-5 py-3 rounded-xl shadow-2xl text-sm font-medium
          ${toast.type === 'success' ? 'bg-emerald-500/90 text-white' : 'bg-red-500/90 text-white'}
          animate-[slideIn_0.3s_ease]`}
        >
          {toast.message}
        </div>
      )}

      {/* Header */}
      <header className="bg-[#1a1d27] border-b border-[#2a2d3a] px-6 h-14 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link to="/" className="text-[#8b8fa3] hover:text-white transition-colors text-sm">
            ← Results
          </Link>
          <div className="h-5 w-px bg-[#2a2d3a]" />
          <div className="font-bold text-lg">🗳 ECI Scraper</div>
        </div>
        <div className="flex items-center gap-3">
          <a
            href="http://localhost:8001/admin/scrape/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-[#8b8fa3] hover:text-[#4f8eff] transition-colors"
          >
            Django Admin ↗
          </a>
          <button
            onClick={() => { setIsAuthenticated(false); setPassword(''); }}
            className="text-xs text-[#8b8fa3] hover:text-red-400 transition-colors"
          >
            Logout
          </button>
        </div>
      </header>

      {/* Stats + Controls */}
      <div className="bg-[#1a1d27] border-b border-[#2a2d3a] px-6 py-5">
        {/* Stats Row */}
        <div className="flex gap-4 mb-5">
          {[
            { label: 'Total ACs', value: statusData?.total ?? '—', color: '#4f8eff' },
            { label: 'Scraped', value: statusData?.scraped ?? '—', color: '#00d2d3' },
            { label: 'Needs Match', value: statusData?.pending_match ?? '—', color: '#ffa502' },
            { label: 'Committed', value: statusData?.committed ?? '—', color: '#2ed573' },
          ].map(s => (
            <div key={s.label} className="bg-[#0f1117] border border-[#2a2d3a] rounded-xl px-5 py-3 min-w-[130px]">
              <div className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</div>
              <div className="text-[11px] text-[#8b8fa3] uppercase tracking-wider mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Controls Row */}
        <div className="flex items-center gap-4 flex-wrap">
          {/* Mode Toggle */}
          <div className="flex items-center gap-2 bg-[#0f1117] border border-[#2a2d3a] rounded-xl px-4 py-2.5">
            <span className="text-xs text-[#8b8fa3] font-medium">Source:</span>
            <button
              onClick={() => setTestMode(true)}
              className={`text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors ${
                testMode
                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  : 'text-[#8b8fa3] hover:text-white'
              }`}
            >
              ⚠ Bihar Test
            </button>
            <button
              onClick={() => setTestMode(false)}
              className={`text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors ${
                !testMode
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'text-[#8b8fa3] hover:text-white'
              }`}
            >
              ✅ Kerala Live
            </button>
          </div>

          {/* Scrape All */}
          {scraping === 'all' ? (
            <button
              onClick={async () => {
                try {
                  await fetch(`${API_BASE}/scraper/stop/`, { method: 'POST' });
                  setScraping(null);
                  showToast('success', '⏹ Stopping scrape loop...');
                } catch {
                  showToast('error', 'Failed to stop scrape');
                }
              }}
              className="bg-red-500/20 text-red-500 border border-red-500/30 font-bold text-sm px-5 py-2.5 rounded-xl hover:bg-red-500/30 transition-colors flex items-center gap-2"
            >
              <span className="animate-spin">⏳</span> Stop Scrape
            </button>
          ) : (
            <button
              onClick={() => handleScrape('all')}
              className="bg-gradient-to-r from-emerald-500 to-emerald-600 text-white font-bold text-sm px-5 py-2.5 rounded-xl hover:opacity-90 transition-opacity flex items-center gap-2"
            >
              ⬇ Scrape All ({statusData?.total ?? 0})
            </button>
          )}

          {/* Refresh */}
          <button
            onClick={fetchStatus}
            disabled={loading}
            className="text-sm text-[#4f8eff] hover:text-white transition-colors disabled:opacity-50 mr-2"
          >
            ↻ Refresh
          </button>

          {/* Deploy */}
          <button
            onClick={handleDeploy}
            disabled={deploying}
            className="bg-gradient-to-r from-[#4f8eff] to-[#6c5ce7] text-white font-bold text-sm px-5 py-2.5 rounded-xl hover:opacity-90 transition-opacity flex items-center gap-2 disabled:opacity-50"
            title="Export JSON, Build React, and Deploy to Firebase"
          >
            {deploying ? '⏳ Deploying...' : '🚀 Deploy'}
          </button>

          {/* Search */}
          <div className="ml-auto flex items-center gap-2 bg-[#0f1117] border border-[#2a2d3a] rounded-xl px-3 py-2 min-w-[240px] focus-within:border-white transition-colors">
            <span className="text-[#555]" aria-hidden="true">⌕</span>
            <input
              type="text"
              aria-label="Search constituency"
              placeholder="Search constituency..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="bg-transparent border-none outline-none w-full text-sm text-white placeholder-[#555]"
            />
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Table */}
        <div className="flex-1 overflow-y-auto">
          {loading && !statusData ? (
            <div className="flex items-center justify-center h-64 text-[#8b8fa3]">
              Loading...
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="sticky top-0 z-10">
                <tr className="bg-[#1a1d27] border-b border-[#2a2d3a]">
                  <th className="text-left px-4 py-3 text-[11px] font-bold text-[#8b8fa3] uppercase tracking-wider w-12">#</th>
                  <th className="text-left px-4 py-3 text-[11px] font-bold text-[#8b8fa3] uppercase tracking-wider">Constituency</th>
                  <th className="text-left px-4 py-3 text-[11px] font-bold text-[#8b8fa3] uppercase tracking-wider">District</th>
                  <th className="text-left px-4 py-3 text-[11px] font-bold text-[#8b8fa3] uppercase tracking-wider">Last Scraped</th>
                  <th className="text-left px-4 py-3 text-[11px] font-bold text-[#8b8fa3] uppercase tracking-wider">Round</th>
                  <th className="text-left px-4 py-3 text-[11px] font-bold text-[#8b8fa3] uppercase tracking-wider">Status</th>
                  <th className="text-right px-4 py-3 text-[11px] font-bold text-[#8b8fa3] uppercase tracking-wider w-48">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredConstituencies.map(c => {
                  const s = c.latest_scrape;
                  const isActiveScraping = scraping === c.number;

                  return (
                    <tr
                      key={c.number}
                      className="border-b border-[#1e2130] hover:bg-[#1a1d27]/60 transition-colors"
                    >
                      <td className="px-4 py-3 text-[#8b8fa3] font-mono text-xs">{c.number}</td>
                      <td className="px-4 py-3 font-semibold text-white">{c.name}</td>
                      <td className="px-4 py-3 text-[#8b8fa3]">{c.district}</td>
                      <td className="px-4 py-3 text-[#8b8fa3] text-xs">
                        {s ? (
                          <span title={s.scraped_at}>
                            {formatRelativeTime(s.scraped_at)}
                          </span>
                        ) : (
                          <span className="text-[#444]">Never</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs">
                        {s ? (
                          <span className="text-[#8b8fa3]">
                            {s.rounds_completed}/{s.total_rounds}
                            {s.is_final && (
                              <span className="ml-1.5 text-[10px] bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded font-bold">
                                FINAL
                              </span>
                            )}
                          </span>
                        ) : '—'}
                      </td>
                      <td className="px-4 py-3">
                        {s ? (
                          <StatusBadge status={s.match_status} />
                        ) : (
                          <span className="text-[10px] text-[#444] bg-[#1a1d27] px-2 py-1 rounded-full">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleScrape(c.number)}
                            disabled={isActiveScraping}
                            className="text-xs font-semibold px-3 py-1.5 bg-[#4f8eff]/10 text-[#4f8eff] border border-[#4f8eff]/20 rounded-lg hover:bg-[#4f8eff]/20 transition-colors disabled:opacity-40"
                          >
                            {isActiveScraping ? '⏳...' : '⬇ Scrape'}
                          </button>

                          <button
                            onClick={() => handleClear(c.number)}
                            disabled={clearing === c.number}
                            className="text-xs font-semibold px-3 py-1.5 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/20 transition-colors disabled:opacity-40"
                            title="Reset votes, delete scrape & LiveResult, clear RTDB node"
                          >
                            {clearing === c.number ? '⏳...' : '🗑'}
                          </button>

                          {s && (
                            <button
                              onClick={() => handleViewDetails(s.id)}
                              className="text-xs font-semibold px-3 py-1.5 bg-[#8b8fa3]/10 text-[#8b8fa3] border border-[#8b8fa3]/20 rounded-lg hover:bg-[#8b8fa3]/20 hover:text-white transition-colors"
                            >
                              👁 Match
                            </button>
                          )}

                          {s && s.match_status === 'MATCHED' && (
                            <button
                              onClick={() => handleCommit(s.id)}
                              disabled={committing === s.id}
                              className="text-xs font-semibold px-3 py-1.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-lg hover:bg-emerald-500/20 transition-colors disabled:opacity-40"
                            >
                              {committing === s.id ? '⏳...' : '✔ Commit'}
                            </button>
                          )}

                          {s && (s.match_status === 'PENDING' || s.match_status === 'PARTIAL') && (
                            <button
                              onClick={() => handleCommit(s.id)}
                              disabled={committing === s.id}
                              className="text-xs font-semibold px-3 py-1.5 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-lg hover:bg-amber-500/20 transition-colors disabled:opacity-40"
                              title="Force commit matched candidates"
                            >
                              {committing === s.id ? '⏳...' : '⚡ Commit'}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Right sidebar — active scrape result */}
        {activeScrape && (
          <div className="w-[420px] bg-[#1a1d27] border-l border-[#2a2d3a] overflow-y-auto shrink-0">
            <div className="p-5 border-b border-[#2a2d3a]">
              <div className="flex items-center justify-between mb-3">
                <div className="font-bold text-lg">{activeScrape.constituency_name}</div>
                <button
                  onClick={() => setActiveScrape(null)}
                  className="text-[#8b8fa3] hover:text-white text-lg"
                >
                  ×
                </button>
              </div>
              <div className="flex items-center gap-3 text-xs text-[#8b8fa3]">
                <span>AC #{activeScrape.constituency_number}</span>
                <span>•</span>
                <span>Round {activeScrape.rounds_completed}/{activeScrape.total_rounds}</span>
                {activeScrape.is_final && (
                  <span className="bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded font-bold">FINAL</span>
                )}
                <span>•</span>
                <StatusBadge status={activeScrape.match_status} />
              </div>
            </div>

            {/* Candidate matches */}
            <div className="p-4">
              <div className="text-[10px] font-bold text-[#8b8fa3] uppercase tracking-wider mb-3">
                Scraped Candidates ({activeScrape.matches.length})
              </div>
              <div className="space-y-2">
                {activeScrape.matches.map(m => (
                  <div
                    key={m.id}
                    className={`p-3 rounded-xl border transition-colors ${
                      m.eci_is_leading
                        ? 'bg-emerald-500/5 border-emerald-500/20'
                        : m.is_nota
                        ? 'bg-[#0f1117]/50 border-[#2a2d3a]'
                        : 'bg-[#0f1117] border-[#2a2d3a]'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm">{m.eci_name}</span>
                        {m.eci_is_leading && (
                          <span className="text-[9px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded font-bold">
                            LEADING
                          </span>
                        )}
                        {m.is_nota && (
                          <span className="text-[9px] bg-[#2a2d3a] text-[#8b8fa3] px-1.5 py-0.5 rounded">
                            NOTA
                          </span>
                        )}
                      </div>
                      <div className="font-mono text-sm font-bold" style={{ color: '#4f8eff' }}>
                        {m.eci_total_votes.toLocaleString('en-IN')}
                      </div>
                    </div>
                    <div className="flex items-center justify-between text-xs text-[#8b8fa3]">
                      <span>{m.eci_party} • {m.eci_vote_percentage}%</span>
                      {m.is_confirmed && m.candidate_name ? (
                        <span className="text-emerald-400">
                          ✓ → {m.candidate_name} ({m.candidate_party})
                        </span>
                      ) : !m.is_nota ? (
                        <div className="flex items-center gap-2">
                          <span className="text-amber-400">⚠ Unmatched</span>
                          <select
                            className="bg-[#0f1117] border border-[#2a2d3a] rounded px-2 py-1 text-white w-48 text-xs"
                            value={pendingMatches[m.id] || m.candidate_id?.toString() || ''}
                            onChange={(e) => setPendingMatches({ ...pendingMatches, [m.id]: e.target.value })}
                          >
                            <option value="">-- Select Candidate --</option>
                            <option value="skip">Skip (Do not match)</option>
                            {dbCandidates.map(c => (
                              <option key={c.id} value={c.id}>
                                {c.name} ({c.party})
                              </option>
                            ))}
                          </select>
                        </div>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>

              {/* Match Save button */}
              {Object.keys(pendingMatches).length > 0 && (
                <button
                  onClick={handleSaveMatches}
                  disabled={savingMatches}
                  className="w-full mt-4 py-3 bg-[#4f8eff]/20 text-[#4f8eff] border border-[#4f8eff]/30 font-bold rounded-xl hover:bg-[#4f8eff]/30 transition-colors disabled:opacity-50"
                >
                  {savingMatches ? '⏳ Saving...' : '💾 Save Matches'}
                </button>
              )}

              {/* Commit button */}
              {(activeScrape.match_status === 'MATCHED' || activeScrape.match_status === 'PENDING' || activeScrape.match_status === 'PARTIAL') && (
                <button
                  onClick={() => handleCommit(activeScrape.id)}
                  disabled={committing === activeScrape.id}
                  className={`w-full mt-4 py-3 text-white font-bold rounded-xl hover:opacity-90 transition-opacity disabled:opacity-50 ${
                    activeScrape.match_status === 'MATCHED'
                      ? 'bg-gradient-to-r from-emerald-500 to-emerald-600'
                      : 'bg-gradient-to-r from-amber-500 to-amber-600'
                  }`}
                >
                  {committing === activeScrape.id
                    ? '⏳ Committing...'
                    : activeScrape.match_status === 'MATCHED'
                    ? '✔ Commit Results to Database'
                    : '⚡ Force Commit (Unmatched)'}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}


// ─── Sub-components ──────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    MATCHED: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
    PARTIAL: 'bg-amber-500/15 text-amber-400 border-amber-500/20',
    PENDING: 'bg-red-500/15 text-red-400 border-red-500/20',
    SKIPPED: 'bg-[#2a2d3a] text-[#8b8fa3] border-[#2a2d3a]',
  };
  const labels: Record<string, string> = {
    MATCHED: '✓ Matched',
    PARTIAL: '⚠ Partial',
    PENDING: '⏳ Pending',
    SKIPPED: 'Skipped',
  };

  return (
    <span className={`text-[10px] font-bold px-2 py-1 rounded-full border ${styles[status] || styles.SKIPPED}`}>
      {labels[status] || status}
    </span>
  );
}


function formatRelativeTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}


export default AdminPanel;
