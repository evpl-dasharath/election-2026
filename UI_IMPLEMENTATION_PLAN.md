# Kerala Election 2026 — UI Implementation Plan

**Prepared for:** Claude Code Sessions  
**Stack:** React 18 + TypeScript + Tailwind + React Router  
**Launch:** May 4, 2026  

---

## Navigation Structure

| Route | Page | Nav Label | Phase |
|-------|------|-----------|-------|
| `/` | Home — Scoreboard | Results | Pre-launch |
| `/constituency/:id` | Constituency Detail | — (via cards) | Pre-launch |
| `/party/:code` | Party Performance | Parties | Post-launch |
| `/history` | Historical Analysis | History | Post-launch |
| `/history/constituency/:id` | Constituency History | — (via History) | Post-launch |

**Nav Bar** (persistent, slim):
- Left: Site name / logo
- Centre: Results | Parties | History
- Right: Last updated timestamp + live pulse indicator
- History tab hidden or greyed out on launch day, activated post-result

Party page and Constituency page are not in the main nav — they are reached by clicking through from Home. Back button returns to Home.

---

## Priority 1 — Home Page

### Data Model Additions Needed
- `region` field on `Constituency` — one of: `north | central_north | south_central | south`
- Region mapping (config constant or DB field):
  - **North:** Kasaragod, Kannur, Wayanad, Kozhikode
  - **Central North:** Malappuram, Palakkad, Thrissur
  - **South Central:** Ernakulam, Idukki, Kottayam
  - **South:** Alappuzha, Pathanamthitta, Kollam, Thiruvananthapuram

---

### Section 1 — Alliance Summary Bar (existing, keep)
Top of page. Overall state tally:

```
LDF  72  |  UDF  54  |  NDA  8  |  OTH  2
Leading + Won combined. Colour coded.
```

---

### Section 2 — Regional Summary Panel (new)
Horizontal four-block panel below the alliance bar.

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│    North    │Central North│South Central│    South    │
│  Malabar    │             │             │ Trivandrum  │
├─────────────┼─────────────┼─────────────┼─────────────┤
│  LDF  18    │  LDF  12    │  UDF  14    │  UDF  11    │
│  UDF  10    │  UDF  11    │  LDF   9    │  LDF   8    │
│  NDA   2    │  NDA   1    │  NDA   0    │  NDA   2    │
│  35 seats   │  32 seats   │  38 seats   │  35 seats   │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

- Each block has a subtle background tint of the leading alliance colour
- Clicking a region block filters the card list below to that region
- Active region block gets a stronger colour + underline indicator

---

### Section 3 — District Filter Tabs (new)
Horizontal scrollable tab row:

```
[ All ] [ Kasaragod ] [ Kannur ] [ Kozhikode ] ... [ Thiruvananthapuram ]
```

- Selecting a region in Section 2 auto-highlights the districts in that region
- Tabs and region blocks work together — selecting a district tab activates the corresponding region block
- "All" resets both filters

---

### Section 4 — Constituency Compact Cards (refactored)
Grid of cards. Two columns on desktop, one on mobile.

**Card anatomy:**
```
[#42] Thrissur                         [ COUNTING ]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
K. Muraleedharan               UDF ●
vs P. Balachandran             LDF ●
Leading by 2,841 votes
▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░  62% counted
```

**Card states:**

| State | Visual Treatment |
|-------|-----------------|
| Not started | Muted grey, "Counting begins soon" |
| Counting | Normal, leader + runner-up + margin + progress bar |
| Close fight | Amber left border, margin < 500 votes |
| Won | Strong alliance colour left border, winner name bold |

**Fields on card:**
- Constituency number + name
- Status badge (Counting / Close / Won)
- Leader: name + alliance colour dot
- Runner-up: name + alliance colour dot (muted)
- Margin in votes
- Progress bar: votes counted / total polled (no numbers, just bar + %)
- District name (small muted text, hidden when district filter is active)

**Interactions:**
- Click card → navigate to `/constituency/:id`
- Click alliance dot → navigate to `/party/:code`

---

## Priority 2 — Constituency Detail Page

### Data Model Additions Needed
- `is_incumbent` — boolean on `Candidate`
- `total_votes_polled` — integer on `Constituency`
- `rounds_total` — integer on `Constituency` (optional, from ECI)
- `rounds_counted` — integer on `Constituency` (optional, from ECI)
- `last_updated` — datetime on `LiveResult`

---

### Section 1 — Slim Header (new, replaces full summary bar)
Thin persistent strip at top — does not take screen space from results:

```
LDF 72  |  UDF 54  |  NDA 8          [ ← Back to Results ]
```

Alliance totals in compact form. Back button right-aligned.

---

### Section 2 — Hero / Leader Panel (new)
Large callout at top of constituency view:

```
┌──────────────────────────────────────────────────────┐
│  K. Muraleedharan                            UDF ●   │
│  LEADING                                             │
│                                                      │
│  Leading by  2,841 votes        LDF ▲ 2.3% swing    │
│  vs P. Balachandran  LDF ●                          │
│                                                      │
│  ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░  62% counted                  │
│  Round 4 of 12  (if available)   Last updated 10:42  │
└──────────────────────────────────────────────────────┘
```

- Swing indicator compared to 2021 alliance vote share
- Incumbent flag shown if 2021 winner is contesting: "Defending seat" or "Seat lost"
- Progress: always show % from votes polled; show rounds only if ECI data available

---

### Section 3 — Candidate Results Table (enhanced)
All candidates ranked by current votes:

| # | Candidate | Party | Alliance | Votes | Vote % | vs 2021 | Status |
|---|-----------|-------|----------|-------|--------|---------|--------|
| 1 | K. Muraleedharan | INC | UDF ● | 48,320 | 38.2% | +2.1% | Leading |
| 2 | P. Balachandran | CPM | LDF ● | 45,479 | 35.9% | -1.4% | Trailing |
| 3 | ... | | | | | | Deposit lost |

- vs 2021 column only shows if same candidate contested in 2021
- Deposit lost indicator: candidate below 1/6th of total votes (ECI rule)
- Winner/leader row highlighted with alliance colour background tint
- Incumbent badge on candidate who won 2021

---

### Section 4 — Swing Analysis Panel (new)
Between live results and historical. Three columns, one per alliance:

```
          2021        2026        Change
UDF       34.2%       36.3%       ▲ 2.1%
LDF       48.1%       46.7%       ▼ 1.4%
NDA        8.3%        7.2%       ▼ 1.1%
```

Simple table, no charts needed for launch.

---

### Section 5 — Historical Panel (refactored)
Split into two sub-sections:

**2021 Legislative Assembly** (left / top)
- Candidate-level results as now
- Add "Same candidate contesting 2026?" tag linking past to present

**Parliament Context** (collapsible, collapsed by default)
- 2019 + 2024 LS results at alliance level
- Collapsed by default to save screen space
- Label: "Parliament Segment Results ▼"

---

### Navigation Within Detail Page
- Previous constituency `←` / Next constituency `→` buttons
- Navigates by constituency number so user doesn't return to home between seats

---

## Priority 3 — Party Page (post-launch polish)

### Page Header
```
Indian National Congress (INC)                  UDF ●
Candidates: 82    Leading: 31    Won: 0
Vote Share: 24.3%    vs 2021: ▲ 2.1%
```

### Performance Strip
- Seats contested vs winning (conversion rate)
- Total votes across all candidates
- Best margin / worst margin

### Constituency List
Compact cards same as home but sorted options:
- Closest fights first (default on results day)
- Safest seats first
- By constituency number
- By status

Two sections: **Leading** and **Trailing** — visually separated.

### Historical Table
| | 2021 | 2026 |
|---|---|---|
| Seats Won | 21 | — |
| Vote Share | 22.2% | 24.3% |
| Candidates | 80 | 82 |

### Navigation Into Party Page
- Alliance dot on home cards
- Party name on constituency detail candidate table
- Parties tab in main nav

---

## Priority 4 — Historical Analysis Page (post-launch)

### Overview
Different audience from live results — journalists, researchers, political workers doing post-election analysis. Depth over speed. All data pre-computed and served as static JSON.

### Data Needed — Source Before Building

| Data | Status | Source |
|------|--------|--------|
| 2021 LA results (candidate level) | ✅ Have | Imported |
| 2019 LS results (AC segment) | ✅ Have | Imported |
| 2024 LS results (AC segment) | ✅ Have | Imported |
| 2016 LA results | ⏳ Need | ECI / Datameet |
| 2011 LA results | ⏳ Need | ECI / Datameet |
| 2014 LS results (AC segment) | ⏳ Need | ECI |
| Turnout per constituency per election | ⏳ Need | ECI |
| Kerala constituency GeoJSON (140 boundaries) | ⏳ Need | Datameet India GitHub / ECI |
| Booth-wise results 2026 | ⏳ Post May 4 | ECI (released after counting) |
| Booth lat/long coordinates | ⏳ Post May 4 | ECI booth list |

**Critical path:** GeoJSON and 2011/2016 data must be sourced before building this page.

---

### Data Model Additions Needed

- `HistoricalResult` model — election_year, election_type (LA/LS), constituency, candidate_name, party, alliance, votes, vote_pct, position, is_winner
- `ElectionMeta` model — year, type, total_seats, state_turnout_pct, date
- `turnout_pct` field on existing Constituency (per election, stored in HistoricalResult or separate model)
- New import command for 2011/2016 LA data following existing CSV import pattern

---

### View 1 — State Level Overview (landing view)

**Alliance seat tally table across all elections:**

| Election | LDF | UDF | NDA | OTH | Turnout |
|----------|-----|-----|-----|-----|---------|
| LA 2011 | 68 | 72 | 0 | 0 | 73.4% |
| LA 2016 | 91 | 47 | 1 | 1 | 77.1% |
| LA 2021 | 99 | 41 | 0 | 0 | 74.8% |
| LA 2026 | — | — | — | — | — |

**Charts on this view:**
- Alliance seat trend — grouped bar chart, one group per election year, four bars per group (LDF/UDF/NDA/OTH)
- Vote share trend — four line chart, one line per alliance across elections. More honest than seats due to FPTP mathematics
- Turnout trend — single line chart across elections

---

### View 2 — Constituency History

Reachable from:
- History page search/list
- "Full History" link at bottom of Constituency Detail page

**Election winner timeline — colour blocks:**
```
Thrissur  [UDF 2011] [LDF 2016] [LDF 2021] [UDF 2026]
```
Each block is the winning alliance colour. Seat changes immediately visible.

**Charts on this view:**
- Vote share per election — grouped bar chart showing UDF/LDF/NDA share for each election year in this constituency
- Margin trend — line chart, winning margin across elections (shrinking margin = bellwether signal)
- Candidate personal vote history — if same candidate contested multiple elections, their vote trajectory as a line
- Turnout per election — bar chart for this constituency

**Data table below charts:**

| Election | Winner | Party | Alliance | Votes | Vote % | Margin | Turnout |
|----------|--------|-------|----------|-------|--------|--------|---------|
| 2011 | ... | INC | UDF | 48,200 | 36.1% | 3,420 | 72.1% |
| 2016 | ... | CPM | LDF | 51,300 | 37.8% | 6,110 | 76.4% |
| 2021 | ... | CPM | LDF | 54,800 | 39.2% | 8,240 | 74.2% |
| 2026 | — | — | — | — | — | — | — |

---

### View 3 — Party Deep Dive

Per party across all elections:

**Charts:**
- Seats contested vs seats won per election — two bars side by side per year
- Vote share trend — single line across elections

**Tables:**
- Best performing constituencies historically (strongholds — won 3+ consecutive elections)
- Biggest gains and losses between elections
- Constituencies flipped from opponent

---

### View 4 — Swing Analysis

Filterable table showing vote share shift between elections per constituency.

**Filter options:**
- Biggest swings toward LDF
- Biggest swings toward UDF
- NDA decline constituencies (post 2016 pattern)
- Near misses — seat didn't change but margin under 2,000 votes
- Choose election pair: 2021→2026, 2016→2021, 2011→2016

**Table columns:** Constituency | 2021 Alliance % | 2026 Alliance % | Swing | Seat changed?

---

### View 5 — LS vs LA Comparison

How the same geography votes differently for state vs central elections.

**Chart:** Scatter plot — x axis = LA vote share for alliance, y axis = LS vote share. Points above diagonal = does better in LS, below = does better in LA.

**Table:** Constituencies with biggest divergence between LS and LA preference. NDA performance gap is usually the most interesting story in Kerala.

---

### View 6 — Kerala Map (two phases)

**Phase 1 — Constituency Choropleth (build first)**

Technology: React-Leaflet + Kerala GeoJSON (140 constituency boundaries)

- Each constituency polygon coloured by winning alliance
- Shade intensity = margin strength (dark = dominant win, light = razor thin)
- Toggle between election years: 2011 / 2016 / 2021 / 2026
- Click polygon → navigate to constituency history view
- Hover tooltip: constituency name, winner, margin

**Phase 2 — Booth Dot Density Map (post May 4 data)**

Technology: D3.js (more control needed for dot rendering at scale)

- Each booth plotted as a dot at its lat/long coordinate
- Dot colour = winning party/alliance at that booth
- Dot size = voter count at that booth
- No polygon boundaries needed — sidesteps the booth boundary change problem between elections
- Filter toggle: by alliance or by party
- Zoom into districts and constituencies
- Requires: booth-wise result CSV from ECI + booth lat/long coordinates

**Phase 3 — Comparison Mode (ambitious, if time allows)**
- Side-by-side map: 2021 left | 2026 right
- Or animated transition between election years
- Shows geographic shift of political support visually

---

## Implementation Order for Claude Code

### Phase 1 — Data Model (backend, before any UI)
1. Add `region` to Constituency model + migration
2. Add `is_incumbent` to Candidate model
3. Add `total_votes_polled`, `rounds_total`, `rounds_counted` to Constituency
4. Add `last_updated` to LiveResult
5. Update `export_json` command to include new fields
6. Update API serializers

### Phase 2 — Home Page
1. Refactor existing home into compact card grid
2. Build compact constituency card component (all five states)
3. Build regional summary panel (4 blocks)
4. Build district filter tabs
5. Wire region block ↔ district tab interaction

### Phase 3 — Constituency Detail Page
1. Build slim header component
2. Build hero/leader panel with swing + progress
3. Enhance candidate table with new columns
4. Build swing analysis panel
5. Add collapsible parliament context section
6. Add previous/next constituency navigation

### Phase 4 — Nav + Routing
1. Persistent nav bar with last updated + live indicator
2. React Router routes for all pages
3. Back navigation from detail → home
4. History tab (greyed out pre-launch, active post-launch)

### Phase 5 — Party Page
1. Party page layout + header
2. Filtered constituency card list
3. Leading / trailing sections
4. Historical comparison table (2021 vs 2026 only at launch)

### Phase 6 — Historical Page (post-launch)
1. Source and import 2011 + 2016 LA data
2. Source Kerala constituency GeoJSON
3. Add HistoricalResult + ElectionMeta models
4. Build state overview with seat tally table + three charts
5. Build constituency history view with timeline blocks + four charts
6. Build swing analysis filterable table
7. Build LS vs LA comparison view
8. Phase 1 map — choropleth with year toggle
9. Phase 2 map — booth dot density (after ECI releases booth data)

---

## Shared Components to Build Once

| Component | Used In |
|-----------|---------|
| `AllianceDot` | Cards, tables, headers everywhere |
| `ProgressBar` | Home cards, constituency hero |
| `StatusBadge` | Home cards, constituency detail |
| `SwingIndicator` | Constituency hero, party header, history |
| `ConstituencyCard` | Home page, party page |
| `SlimHeader` | Constituency detail, party page |
| `CandidateTable` | Constituency detail |
| `AllianceTrendChart` | History state overview, party page |
| `VoteShareBarChart` | History constituency view, party page |
| `MarginTrendChart` | History constituency view |
| `KeralaMap` | History map view |
| `ElectionTimelineBlocks` | History constituency view |

Build shared components before pages. Each component tested in isolation before wiring into a page.

---

## Technology Additions for Historical Page

| Library | Purpose | Install |
|---------|---------|---------|
| Recharts | All bar + line charts | Already likely in stack |
| React-Leaflet | Choropleth map Phase 1 | `npm install react-leaflet leaflet` |
| D3.js | Booth dot map Phase 2 | `npm install d3` |

---

## Asset Checklist for Claude Code Sessions

Before starting Phase 6, confirm these are ready:

- [ ] Kerala constituency GeoJSON sourced (Datameet India GitHub is best starting point)
- [ ] 2016 LA CSV imported and verified
- [ ] 2011 LA CSV imported and verified
- [ ] 2014 LS CSV imported and verified
- [ ] Turnout data per constituency per election added
- [ ] HistoricalResult model migration run
- [ ] export_json updated to include historical data

---

**Ready for Claude Code.** Start each session with `CLAUDE_CODE_STARTER.md` and reference this file for the full plan.  
Pre-launch priority: Phases 1–4. Post-launch: Phases 5–6.
