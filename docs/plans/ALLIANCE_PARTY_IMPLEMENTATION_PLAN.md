# Alliance & Party Pages — Implementation Plan
## Kerala Elections 2026 · kl-2026.web.app

---

## Navigation

```
State  |  Constituency  |  Alliances  |  Parties  |  History
```

- **State** → `/` (existing home scoreboard)
- **Constituency** → `/constituency/:id` (existing, sidebar + detail)
- **Alliances** → `/alliance/ldf` (new — defaults to LDF)
- **Parties** → `/party/:code` (new — sidebar + detail, same layout pattern as Constituency)
- **History** → `/history` (existing stub)

Both Alliances and Parties are added to `GlobalHeader` nav.

---

## Backend Requirements

### 1. Alliance Summary Endpoint
`GET /api/alliance/:code/` → returns aggregate data for LDF, UDF, or NDA.

```json
{
  "alliance": "LDF",
  "seats_leading": 18,
  "seats_won": 81,
  "seats_trailing": 23,
  "seats_contested": 122,
  "total_valid_votes": 12400000,
  "vote_share_pct": 45.2,
  "vote_share_2021_pct": 46.3,
  "best_margin": { "constituency": "Dharmadam", "margin": 16018 },
  "worst_margin": { "constituency": "Thalassery", "margin": 153 },
  "parties": [
    {
      "code": "CPM",
      "name": "Communist Party of India (Marxist)",
      "seats_contested": 62,
      "seats_leading_or_won": 41,
      "vote_share_pct": 28.4,
      "vote_share_2021_pct": 29.1
    }
  ],
  "constituencies": [ /* full ConstituencyListItem for all 140 */ ]
}
```

### 2. Party Detail Endpoint
`GET /api/party/:code/` → returns data for a single party.

```json
{
  "code": "CPM",
  "name": "Communist Party of India (Marxist)",
  "alliance": "LDF",
  "color_code": "#D42B2B",
  "seats_contested": 62,
  "seats_leading_or_won": 41,
  "vote_share_pct": 28.4,
  "vote_share_2021_pct": 29.1,
  "constituencies": [ /* ConstituencyListItem for contested seats only */ ]
}
```

### 3. Parties List Endpoint
`GET /api/parties/` → already exists (`useParties`). Confirm it returns:
- `code`, `name`, `alliance`, `color_code`
- `seats_contested`, `seats_leading_or_won`

If not, extend the serializer to include these fields.

### 4. Seat Classification
The classification logic (Stronghold / Leaning / Swing / Opponent's) computed in
`HistoryPage.tsx` must be available as a utility function shared across pages.

**Extract to:** `src/utils/seatClassification.ts`

```ts
export type SeatClass = 'Stronghold' | 'Fragile' | 'Leaning' | 'Swing' | "Opponent's";
export function classifyForAlliance(alliance, results): SeatClass
export function classifySeat(history): { seatClass, ownerAlliance }
```

Both AlliancePage and PartyPage import from this util — no duplication.

---

## Constituency Classification — Final Logic

Window: **2011, 2016, 2021** (post-delimitation only).
Margin thresholds: **Large ≥ 5,000** · **Tight < 2,000**

Five classes:

| Pattern (2011→2021) | Rule | Classification |
|---------------------|------|---------------|
| ✓✓✓ all comfortable | Won all 3, all margins ≥ 2,000 | **Stronghold** |
| ✓✓✓ any tight win | Won all 3 but at least one margin < 2,000 | **Fragile** |
| ✗✓✓ | Won last 2 | **Leaning** |
| ✓✗✓ large wins + tight loss | Blip loss — both wins ≥ 5,000, loss < 2,000 | **Leaning** |
| ✓✗✓ otherwise | True alternation | **Swing** |
| anything else | No consistent pattern | **Opponent's** |

**Fragile** captures seats like Manjeshwar (IUML won 2011 +5,828 · 2016 +89 · 2021 +745) —
held every election but consistently on a knife edge. Distinct from Leaning because the
pattern is ✓✓✓, but the thin margins mean it cannot be relied upon.

```ts
// seatClassification.ts — classifyForAlliance()
if (w11 && w16 && w21) {
  const anyTight = m11 < TIGHT_MARGIN || m16 < TIGHT_MARGIN || m21 < TIGHT_MARGIN;
  return anyTight ? 'Fragile' : 'Stronghold';
}
```

**Badge display:**
- **Stronghold** — solid filled, alliance colour, white text
- **Fragile** — alliance colour border + diagonal stripe fill (CSS `repeating-linear-gradient`), alliance colour text — visually signals instability while acknowledging the win pattern
- **Leaning** — alliance colour tint background, alliance colour text
- **Swing** — neutral grey, no alliance association
- **Opponent's** — neutral grey, no alliance association

Wave context (2011 = UDF wave year) shown as annotation on cards, not baked
into classification. A win against the 2011 UDF wave is flagged `↑ vs '11 wave`.

---

## Alliance Page `/alliance/:code`

### URL & Routing
```
/alliance/ldf   → LDF page
/alliance/udf   → UDF page
/alliance/nda   → NDA page
```

Default route `/alliance` redirects to `/alliance/ldf`.

### Layout
Full-width page (no sidebar). Sections stack vertically.

---

### Section 1 — Header

```
● LDF  Left Democratic Front
Leading + Won: 99    Trailing: 23    Contested: 122
Vote Share: 45.2%    vs 2021: ▼ 1.1%

[ LDF ]  [ UDF ]  [ NDA ]     ← tab switcher, top-right
```

Alliance tabs switch page via `navigate('/alliance/:code')`.
Active tab filled in alliance colour.

---

### Section 2 — Seat Movement Summary

Three-column strip:

| Gained | Held | Lost |
|--------|------|------|
| 12 seats | 87 seats | 14 seats |
| Not held in 2021, winning 2026 | Sitting seats defended | Sitting seats lost |

Below the strip — party-wise breakdown table:

| Party | Contested | Won/Leading | Gained | Lost | Held |
|-------|-----------|-------------|--------|------|------|
| CPM   | 62        | 41          | 7      | 5    | 34   |
| CPI   | 18        | 12          | 2      | 3    | 10   |
| …     |           |             |        |      |      |

Each party row is clickable → navigates to `/party/:code`.

---

### Section 3 — Swing Analysis

```
Seats gained from:   UDF  8  |  NDA  2  |  OTH  2
Sitting seats lost to:   UDF  11  |  NDA  2  |  OTH  1
```

Simple horizontal stat row, colour-coded by the source/target alliance.

---

### Section 4 — Party Vote Share Performance

Per party within this alliance, in constituencies where they are contesting:

| Party | Seats | Avg Vote % | vs 2021 | Share ▲ | Share ▼ |
|-------|-------|------------|---------|---------|---------|
| CPM   | 62    | 38.2%      | ▼ 1.4%  | 28      | 34      |
| CPI   | 18    | 34.1%      | ▲ 0.8%  | 11      | 7       |

Each row clickable → `/party/:code`.

---

### Section 5 — Constituency Cards (filterable)

#### Named Filter Combinations (row 1)

Pre-built story filters — most useful analytical views:

| Filter | Logic |
|--------|-------|
| **Strongholds under pressure** | Stronghold + Holding + Vote share ▼ |
| **Strongholds lost** | Stronghold + Lost |
| **Fragile seats holding** | Fragile + Holding |
| **Fragile seats lost** | Fragile + Lost |
| **Swing seats won** | Swing + Gained |
| **Opponent territory captured** | Opponent's + Gained |
| **Leaning seats at risk** | Leaning + (Lost or Runner-up) |
| **Surprise collapses** | Any + Pushed to 3rd+ |
| **Growing in losses** | Lost + Vote share ▲ |

#### Raw Filter Chips (row 2)

For manual combining:

**By seat profile:** `Stronghold` · `Fragile` · `Leaning` · `Swing` · `Opponent's`

**By 2026 outcome:** `Holding` · `Gained` · `Lost` · `Runner-up` · `3rd+`

**By margin:** `Safe 5k+` · `Comfortable 2–5k` · `Close <2k`

**By vote movement:** `Share ▲` · `Share ▼` · `Marginal (±2%)`

Multiple raw chips combinable. Selecting a named filter sets the raw chips to
match — user can then adjust individually.

#### Card display adapts to active filter context

- **Strongholds under pressure** → show 2021 margin vs 2026 margin side by side
- **Swing seats won** → show who held it in 2021, current margin
- **Pushed to 3rd+** → show current rank, gap to 2nd place
- Default → standard ConstituencyCard (existing component, reused)

#### Card sort options
`By margin` · `By constituency number` · `By swing vs 2021`

---

### Section 6 — Historical Table (post-final only)

Shown only when `resultsFinalized` flag is true. Hidden with
"Available after final results" placeholder during live counting.

| Election | Seats Won | Vote Share | Turnout |
|----------|-----------|------------|---------|
| 2011 LA  | 72        | 43.2%      | 73.4%   |
| 2016 LA  | 91        | 46.9%      | 77.1%   |
| 2021 LA  | 99        | 46.3%      | 74.8%   |
| 2026 LA  | —         | —          | —       |

---

## Party Page `/party/:code`

### Layout
Two-panel — same pattern as `ConstituencyPage`:

```
[ Sidebar 300px ] | [ Main content ]
```

Mobile: sidebar collapses, main content full width.

---

### Sidebar

Same structure as Constituency sidebar:

```
[ Search party… ]

[ All ]  [ LDF ]  [ UDF ]  [ NDA ]

001  CPM      LDF   Leading
002  CPI      LDF   Leading
003  INC      UDF   Leading
…
```

- Search filters by party name
- Alliance filter chips: All / LDF / UDF / NDA
- Each row shows: party code, full name, alliance dot, status
- Active party highlighted with alliance-colour left border
- Clicking navigates to `/party/:code`

Party list sorted: alliance group (LDF → UDF → NDA → OTH), then by seats won desc.

---

### Main Panel

#### Header
```
● CPM  Communist Party of India (Marxist)
LDF Alliance

Contested: 62    Won/Leading: 41    Trailing: 21
Vote Share (contested seats): 38.2%    vs 2021: ▼ 1.4%
```

#### Constituency List
Cards for seats this party is personally contesting (not full alliance).
Same filter chips as Alliance page but scoped to this party's seats:
`Stronghold` · `Fragile` · `Leaning` · `Swing` · `Holding` · `Gained` · `Lost` · `Close`

Clicking a card → `/constituency/:id`

#### Historical Performance (party level)
Simple table — party's own seats and vote share across elections:

| Election | Seats Contested | Seats Won | Vote Share |
|----------|----------------|-----------|------------|
| 2011 LA  | 68             | 35        | 22.1%      |
| 2016 LA  | 65             | 58        | 26.3%      |
| 2021 LA  | 63             | 62        | 26.6%      |
| 2026 LA  | 62             | —         | —          |

Hidden until `resultsFinalized` for 2026 row.

---

## Shared Components to Build / Extend

| Component | Notes |
|-----------|-------|
| `AllianceTabs` | LDF / UDF / NDA switcher, reused in Alliance page header |
| `SeatMovementStrip` | Gained / Held / Lost three-column stat strip |
| `PartyPerformanceTable` | Party-wise breakdown table, reused in Alliance page sections 2 & 4 |
| `NamedFilterBar` | Story filter chips row (Section 5 row 1) |
| `RawFilterChips` | Raw combinable chips (Section 5 row 2) |
| `seatClassification.ts` | Extracted utility, shared across History / Alliance / Party pages |

Existing components reused as-is:
- `GlobalHeader` (add Alliances + Parties nav entries)
- `ConstituencyCard` (reused in Section 5 card grid)
- `AllianceDot`
- `ProgressBar`
- `StatusBadge`

---

## Build Order

### Phase 1 — Shared utilities + backend
1. Extract `seatClassification.ts` from HistoryPage
2. Extend `/api/parties/` serializer with seat counts
3. Build `/api/alliance/:code/` endpoint + serializer
4. Build `/api/party/:code/` endpoint + serializer
5. Add `useAllianceSummary(code)` and `usePartyDetail(code)` hooks

### Phase 2 — Alliance Page
1. Route `/alliance/:code` + redirect from `/alliance`
2. Add Alliances to GlobalHeader nav
3. Header + AllianceTabs
4. Seat Movement Strip (Section 2)
5. Swing Analysis row (Section 3)
6. Party Vote Share table (Section 4)
7. Constituency Cards with NamedFilterBar + RawFilterChips (Section 5)
8. Historical table stub with `resultsFinalized` gate (Section 6)

### Phase 3 — Party Page
1. Route `/party/:code`
2. Add Parties to GlobalHeader nav
3. Sidebar with search + alliance filter + party list
4. Party header panel
5. Constituency card list (party-scoped, with filters)
6. Historical performance table stub

### Phase 4 — Polish
- AlliancePage card context-aware display per named filter
- Wave annotation `↑ vs '11 UDF wave` on relevant cards
- Mobile sidebar collapse for Party page
- Loading skeletons for all new endpoints

---

## Data Notes

- **OTH / Independents:** No Alliance page for OTH. Individual party pages still
  load for OTH parties (accessible via URL or party sidebar "Others" group).
- **2026 data during live counting:** Vote share figures shown with `~` prefix
  and a counting progress indicator. Historical table row for 2026 hidden until
  `resultsFinalized = true`.
- **Delimitation:** Classification window is strictly 2011–2021. Pre-2011 data
  (2001, 2006) available in DB but not used for classification — may be shown
  in historical tables as informational rows with a delimitation disclaimer.
