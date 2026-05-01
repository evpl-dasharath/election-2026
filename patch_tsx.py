import re

with open('frontend/src/pages/ConstituencyPage.tsx', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# ── 1. Fix swingData ─────────────────────────────────────────────────────────
old = re.search(r'const swingData = useMemo\(\(\) =>.*?\}, \[historical, candidates_2026_safe\]\);', content, re.DOTALL)
if old:
    content = content[:old.start()] + """const swingData = useMemo(() => {
    const has2021 = !!(historical?.la_2021?.alliance_shares);
    const has2016 = !!(historical?.la_2016?.alliance_shares);
    const has2026 = candidates_2026_safe.length > 0;
    if (!has2021 && !has2026) return null;
    return (['LDF', 'UDF', 'NDA', 'OTH'] as const).map(al => {
      const v26 = has2026 ? candidates_2026_safe.filter(cd => cd.alliance === al).reduce((s, cd) => s + cd.percentage, 0) : null;
      const v21 = has2021 ? (historical!.la_2021.alliance_shares?.[al] ?? 0) : null;
      const v16 = has2016 ? (historical!.la_2016!.alliance_shares?.[al] ?? 0) : null;
      const swing2126 = (v21 !== null && v26 !== null) ? v26 - v21 : null;
      const swing1621 = (v16 !== null && v21 !== null) ? v21 - v16 : null;
      return { alliance: al, v16, v21, v26, swing1621, swing2126 };
    });
  }, [historical, candidates_2026_safe]);""" + content[old.end():]
    print('OK: swingData')
else:
    print('MISS: swingData')

# ── 2. hasSwing ───────────────────────────────────────────────────────────────
old_hs = "const hasSwing = swingData && swingData.some(s => parseFloat(s.v21) > 0);"
if old_hs in content:
    content = content.replace(old_hs, """const has2016Swing = !!(historical?.la_2016?.alliance_shares);
  const has2026Swing = candidates_2026_safe.length > 0;
  const hasSwing = !!(swingData && (has2016Swing || has2026Swing) && historical?.la_2021?.alliance_shares);""")
    print('OK: hasSwing')
else:
    print('MISS: hasSwing')

# ── 3. get2021Pct / sitting alliance ─────────────────────────────────────────
content = content.replace(
    'if (!historical?.la_2021?.top_5?.length) return null;',
    'if (!historical?.la_2021?.candidates?.length) return null;'
)
content = content.replace(
    'const found = historical.la_2021.top_5.find(r => {',
    'const found = historical.la_2021.candidates.find(r => {'
)
content = content.replace(
    'historical.la_2021.top_5?.find(r => r.is_winner)?.alliance',
    'historical.la_2021.candidates?.find(r => r.is_winner)?.alliance'
)
content = content.replace(
    'historical.la_2021.top_5?.[0]?.alliance',
    'historical.la_2021.candidates?.[0]?.alliance'
)
print('OK: top_5->candidates')

# ── 4. Remove winner highlight from 2026 cards ───────────────────────────────
content = content.replace(
    "background: isTop ? (ABG[cd.alliance] || '#FDFCFB') : '#FDFCFB'",
    "background: '#FDFCFB'"
)
content = content.replace(
    "border: `1.5px solid ${isTop ? color : '#E2DDD8'}`",
    "border: '1.5px solid #E2DDD8'"
)
print('OK: winner highlight removed')

# ── 5. Replace old swing section (vote share swing 2021 vs 2026 table) ───────
# Very tight match: from the "Vote Share Swing" SectionTitle to the closing of its outer div
old_swing_sec = re.search(
    r"<SectionTitle>Vote Share Swing.*?</SectionTitle>.*?</div>\s*\)\}(?=\s*\{/\*)",
    content, re.DOTALL
)
if old_swing_sec:
    new_swing_sec = """<SectionTitle>
                {has2016Swing && has2026Swing ? 'Vote Share Swing - 2016 / 2021 / 2026' :
                 has2016Swing ? 'Vote Share - 2016 / 2021' :
                 'Vote Share Swing - 2021 vs 2026'}
              </SectionTitle>
              <div style={{ background: '#FDFCFB', border: '1px solid #E2DDD8', borderRadius: 10, overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid #E2DDD8', background: '#F5F2EE' }}>
                      <th style={{ padding: '10px 16px', textAlign: 'left', fontSize: 10, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#5C5245' }}>Alliance</th>
                      {has2016Swing && <th style={{ padding: '10px 16px', textAlign: 'right', fontSize: 10, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#5C5245' }}>2016 %</th>}
                      <th style={{ padding: '10px 16px', textAlign: 'right', fontSize: 10, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#5C5245' }}>2021 %</th>
                      {has2026Swing && <th style={{ padding: '10px 16px', textAlign: 'right', fontSize: 10, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#5C5245' }}>2026 %</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {swingData!.map(({ alliance, v16, v21, v26, swing1621, swing2126 }) => {
                      const color = ac(alliance);
                      const isZero = (v16 ?? 0) < 0.1 && (v21 ?? 0) < 0.1 && (v26 ?? 0) < 0.1;
                      if (isZero) return null;
                      return (
                        <tr key={alliance} style={{ borderBottom: '1px solid #F5F2EE' }}>
                          <td style={{ padding: '11px 16px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <div style={{ width: 10, height: 10, borderRadius: 2, background: color }} />
                              <span style={{ fontWeight: 700, color: '#1A1611' }}>{alliance}</span>
                            </div>
                          </td>
                          {has2016Swing && (
                            <td style={{ padding: '11px 16px', textAlign: 'right' }}>
                              <span style={{ fontFamily: "'JetBrains Mono',monospace", color: '#5C5245', fontSize: 13 }}>
                                {v16 !== null && v16 > 0 ? `${v16.toFixed(1)}%` : '--'}
                              </span>
                            </td>
                          )}
                          <td style={{ padding: '11px 16px', textAlign: 'right' }}>
                            <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2 }}>
                              <span style={{ fontFamily: "'JetBrains Mono',monospace", fontWeight: 600, color: v21 && v21 > 0 ? '#1A1611' : '#9CA3AF', fontSize: 13 }}>
                                {v21 !== null && v21 > 0 ? `${v21.toFixed(1)}%` : '--'}
                              </span>
                              {has2016Swing && swing1621 !== null && Math.abs(swing1621) >= 0.1 && (
                                <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, fontWeight: 700, color: swing1621 > 0 ? '#16A34A' : '#DC2626' }}>
                                  {swing1621 > 0 ? '+' : ''}{Math.abs(swing1621).toFixed(1)}
                                </span>
                              )}
                            </div>
                          </td>
                          {has2026Swing && (
                            <td style={{ padding: '11px 16px', textAlign: 'right' }}>
                              <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2 }}>
                                <span style={{ fontFamily: "'JetBrains Mono',monospace", fontWeight: 700, color: v26 && v26 > 0 ? color : '#9CA3AF', fontSize: 13 }}>
                                  {v26 !== null && v26 > 0 ? `${v26.toFixed(1)}%` : '--'}
                                </span>
                                {swing2126 !== null && Math.abs(swing2126) >= 0.1 && (
                                  <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, fontWeight: 700, color: swing2126 > 0 ? '#16A34A' : '#DC2626' }}>
                                    {swing2126 > 0 ? '+' : ''}{Math.abs(swing2126).toFixed(1)}
                                  </span>
                                )}
                              </div>
                            </td>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}"""
    content = content[:old_swing_sec.start()] + new_swing_sec + content[old_swing_sec.end():]
    print('OK: swing section replaced')
else:
    print('MISS: swing section')

# ── 6. Replace 2021 section (very tight pattern) ──────────────────────────────
# Match from "2021 RESULTS" comment through the entire !histLoading && la_2021 block
old_2021 = re.search(
    r'\{/\*[^*]*2021 RESULTS[^*]*\*/\}\s*\{!histLoading && historical\?\.la_2021 && \(.*?\)\}(?=\s*\n\s*\{)',
    content, re.DOTALL
)
if old_2021:
    new_2021 = """{/* -- 2021 RESULTS -- */}
          {!histLoading && historical?.la_2021 && (
            <div style={{ padding: '0 32px 22px' }}>
              <Divider />
              <SectionTitle>2021 Assembly Election</SectionTitle>
              <HistoricalCandidateTable
                candidates={historical.la_2021.candidates.map(cd => ({
                  candidate: cd.candidate,
                  party: cd.party,
                  alliance: cd.alliance as string,
                  votes: cd.votes,
                  percentage: cd.percentage,
                  is_winner: cd.is_winner,
                }))}
                margin={historical.la_2021.margin ?? undefined}
              />
            </div>
          )}

          {/* -- 2016 RESULTS -- */}
          {!histLoading && historical?.la_2016 && (
            <div style={{ padding: '0 32px 22px' }}>
              <Divider />
              <SectionTitle>2016 Assembly Election</SectionTitle>
              <HistoricalCandidateTable
                candidates={(historical.la_2016.candidates ?? []).map(cd => ({
                  candidate: cd.candidate,
                  party: cd.party,
                  alliance: cd.alliance as string,
                  votes: cd.votes,
                  percentage: cd.percentage,
                  is_winner: cd.is_winner,
                }))}
                margin={historical.la_2016.margin}
              />
            </div>
          )}"""
    content = content[:old_2021.start()] + new_2021 + content[old_2021.end():]
    print('OK: 2021+2016 sections')
else:
    print('MISS: 2021 section — checking what is in file')
    idx = content.find('2021 RESULTS')
    print('  2021 RESULTS at char:', idx)
    print('  context:', repr(content[max(0,idx-20):idx+200]))

# ── 7. Add HistoricalCandidateTable component ─────────────────────────────────
component = '''
// -- Compact historical table (2021 & 2016) ---
interface CandidateRowHist {
  candidate: string;
  party: string;
  alliance: string;
  votes: number;
  percentage: number;
  is_winner: boolean;
}

function HistoricalCandidateTable({
  candidates,
  margin,
}: {
  candidates: CandidateRowHist[];
  margin?: number;
}) {
  const totalVotes = candidates.reduce((s, c) => s + c.votes, 0);
  const winner = candidates.find(c => c.is_winner) ?? candidates[0];
  const winColor = winner ? (AC[winner.alliance] || '#5C5245') : '#5C5245';

  return (
    <div style={{ border: '1px solid #E2DDD8', borderRadius: 10, overflow: 'hidden', background: '#FDFCFB' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ background: '#F5F2EE', borderBottom: '1px solid #E2DDD8' }}>
            <th style={{ padding: '8px 14px', textAlign: 'left', fontSize: 10, fontWeight: 700, letterSpacing: '1.2px', textTransform: 'uppercase', color: '#5C5245', width: '26%' }}>Party</th>
            <th style={{ padding: '8px 14px', textAlign: 'left', fontSize: 10, fontWeight: 700, letterSpacing: '1.2px', textTransform: 'uppercase', color: '#5C5245' }}>Candidate</th>
            <th style={{ padding: '8px 14px', textAlign: 'right', fontSize: 10, fontWeight: 700, letterSpacing: '1.2px', textTransform: 'uppercase', color: '#5C5245' }}>Votes</th>
            <th style={{ padding: '8px 14px', textAlign: 'right', fontSize: 10, fontWeight: 700, letterSpacing: '1.2px', textTransform: 'uppercase', color: '#5C5245' }}>%</th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((cd, i) => {
            const color = ac(cd.alliance);
            const abbr = partyAbbr(cd.party);
            const isFirst = i === 0;
            return (
              <tr key={i} style={{ borderBottom: '1px solid #F5F2EE' }}>
                <td style={{ padding: '9px 14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 28, height: 28, borderRadius: '50%', background: color, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 8, fontWeight: 800, color: '#fff', flexShrink: 0 }}>
                      {abbr}
                    </div>
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 700, color: color, lineHeight: 1.2 }}>{cd.party}</div>
                      <div style={{ fontSize: 10, color: '#9CA3AF', lineHeight: 1.2 }}>{cd.alliance}</div>
                    </div>
                  </div>
                </td>
                <td style={{ padding: '9px 14px', fontSize: 13, color: '#1A1611', fontWeight: isFirst ? 600 : 400 }}>
                  {cd.candidate}
                </td>
                <td style={{ padding: '9px 14px', textAlign: 'right', fontFamily: "'JetBrains Mono',monospace", fontSize: 13, fontWeight: isFirst ? 700 : 400, color: isFirst ? '#1A1611' : '#5C5245' }}>
                  {cd.votes.toLocaleString('en-IN')}
                </td>
                <td style={{ padding: '9px 14px', textAlign: 'right', fontFamily: "'JetBrains Mono',monospace", fontSize: 13, fontWeight: isFirst ? 700 : 400, color: isFirst ? winColor : '#5C5245' }}>
                  {cd.percentage.toFixed(2)}
                </td>
              </tr>
            );
          })}
        </tbody>
        {margin != null && (
          <tfoot>
            <tr style={{ background: '#F5F2EE', borderTop: '2px solid #E2DDD8' }}>
              <td colSpan={2} style={{ padding: '9px 14px', textAlign: 'right', fontSize: 11, color: '#5C5245', fontWeight: 600, fontStyle: 'italic' }}>
                Margin of victory
              </td>
              <td style={{ padding: '9px 14px', textAlign: 'right', fontFamily: "'JetBrains Mono',monospace", fontSize: 13, fontWeight: 700, color: winColor }}>
                {margin.toLocaleString('en-IN')}
              </td>
              <td style={{ padding: '9px 14px', textAlign: 'right', fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: '#5C5245' }}>
                {totalVotes > 0 ? ((margin / totalVotes) * 100).toFixed(2) + '%' : '--'}
              </td>
            </tr>
          </tfoot>
        )}
      </table>
    </div>
  );
}
'''

nav_pos = content.find('\nfunction NavButton(')
if nav_pos != -1:
    content = content[:nav_pos] + '\n' + component + content[nav_pos:]
    print('OK: HistoricalCandidateTable added before NavButton')
else:
    content += '\n' + component
    print('OK: HistoricalCandidateTable appended at end')

with open('frontend/src/pages/ConstituencyPage.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

lines = content.count('\n')
print(f'Done. Lines: {lines}, top_5 remaining: {content.count("top_5")}')
