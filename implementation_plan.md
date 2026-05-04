# Standardise Parties & Alliances with FK-based Schema

## Problem
The database currently stores party identifiers as **free-text CharField strings** (`party_code`) across all historical result models (2006, 2011, 2016, 2021) and uses string-based lookups in `PartyAllianceYear`. This causes:
- Multiple spellings for the same party (`CPI(M)` vs `CPM` vs `CPIM`)
- Alliance lookups rely on fragile string matching
- No referential integrity — typos or unknown codes silently go to `OTH`

## Proposed New Schema

### New: `Alliance` model
A small lookup table with exactly 4 rows: `UDF`, `LDF`, `NDA`, `OTH`.

```python
class Alliance(models.Model):
    code = models.CharField(max_length=3, unique=True)  # UDF, LDF, NDA, OTH
    full_name = models.CharField(max_length=100)
    color_code = models.CharField(max_length=7, default='#808080')
```

### Modified: `Party` model
- `alliance` CharField → FK to `Alliance` (the 2026 default)
- `code` remains the **canonical** identifier (e.g. `CPI_M`, `IUML`, `INC`)

### New: `PartyAlias` model
Maps ECI CSV abbreviations (per year) to canonical `Party` FK. Replaces the old string-based code resolution.

```python
class PartyAlias(models.Model):
    alias_code = models.CharField(max_length=50)    # e.g. "CPM", "MUL", "KEC(M)"
    party = models.ForeignKey(Party)                 # -> canonical Party
    election_year = models.IntegerField(null=True)   # null = all years
```

### Modified: `PartyAllianceYear`
- `party_code` CharField → FK to `Party`
- `canonical_code` removed (redundant with FK)
- `alliance` CharField → FK to `Alliance`

### Modified: Historical Result Models (2006, 2011, 2016Full, 2021)
- `party_code` CharField → FK to `Party` (named `party`)
- Old `party_code` kept temporarily as `party_code_legacy` for data migration

### `Candidate` (2026) — No change needed
Already uses FK to `Party`.

## Proposed Changes

### Models

#### [MODIFY] [models.py](file:///c:/Users/everl/Desktop/Other_projects/election-2026/backend/core/models.py)
1. Add `Alliance` model
2. Add `PartyAlias` model  
3. Modify `Party.alliance` → FK to `Alliance`
4. Modify `PartyAllianceYear` → FK to both `Party` and `Alliance`
5. Add `party` FK field to `HistoricalResult2011`, `HistoricalResult2016Full`, `HistoricalResult2021`, `HistoricalResult2006`
6. Keep `party_code` as `party_code_legacy` (read-only backup during migration)

---

### Data Migration

#### [NEW] `migrate_to_fk.py` management command
1. Create `Alliance` rows (UDF, LDF, NDA, OTH)
2. Standardise `Party` table — one canonical entry per real party with normalised `code` (e.g. `CPI_M` not `CPI(M)`)
3. Create `PartyAlias` entries mapping every ECI code variant to its canonical `Party`
4. Populate `PartyAllianceYear` with FK references
5. Update all historical result rows: resolve `party_code_legacy` → `Party` FK via aliases
6. Validate: ensure zero NULL `party` FK values remain

---

### API Layer

#### [MODIFY] [serializers.py](file:///c:/Users/everl/Desktop/Other_projects/election-2026/backend/core/api/serializers.py)
- `get_alliance()` → use `PartyAllianceYear.party.code` + `PartyAllianceYear.alliance.code` (FK lookups)
- `CandidateSerializer` → `party_code` already comes from `party.code`, no change
- Historical serializers → use `result.party.code` instead of `result.party_code`

#### [MODIFY] [views.py](file:///c:/Users/everl/Desktop/Other_projects/election-2026/backend/core/api/views.py)
- Replace all `r.party_code` references with `r.party.code`
- Replace string-based alliance maps with FK joins
- Remove `CONSTITUENCY_2016_OVERRIDE` dict — encode this in `PartyAllianceYear` as a per-constituency override or handle via `PartyAlias`

---

### Seed / Import Commands

#### [MODIFY] [seed_master_data.py](file:///c:/Users/everl/Desktop/Other_projects/election-2026/backend/core/management/commands/seed_master_data.py)
- Create `Alliance` objects first
- Update `Party` creation to use FK to `Alliance`

#### [MODIFY] [seed_party_alliances.py](file:///c:/Users/everl/Desktop/Other_projects/election-2026/backend/core/management/commands/seed_party_alliances.py)
- Rewrite to use FK-based `PartyAllianceYear` + `PartyAlias`

#### [MODIFY] Import commands (import_historical_candidates.py, import_2016_results.py, etc.)
- Resolve party codes via `PartyAlias` → `Party` FK during import

---

### Admin

#### [MODIFY] [admin.py](file:///c:/Users/everl/Desktop/Other_projects/election-2026/backend/core/admin.py)
- Register `Alliance` and `PartyAlias` models
- Update inline displays

## Open Questions

> [!IMPORTANT]
> **Canonical party codes**: Should we use underscore-based codes (`CPI_M`, `KC_M`) matching the tally JSON, or keep parenthesised codes (`CPI(M)`, `KC(M)`) matching how they're commonly written? Underscore codes are safer for URLs/lookups but less readable. **I recommend underscore codes** to match the tally we just corrected.

> [!IMPORTANT]
> **Party code for IND with alliance backing**: Alliance-backed independents (e.g. `IND-LDF`) — should these be stored as party=`IND` with the alliance FK on `PartyAllianceYear` set to `LDF`? Or should we create separate party entries like `IND_LDF`, `IND_UDF`? **I recommend** keeping a single `IND` party and tracking alliance backing purely through `PartyAllianceYear` per-year entries.

> [!WARNING]
> **Destructive migration**: This will require re-seeding all historical data. The existing DB data will need to be re-imported after the schema change. Are you OK with wiping and re-importing? Or do you need an in-place data migration that preserves existing rows?

## Verification Plan

### Automated Tests
1. Run `python manage.py migrate` — confirm no errors
2. Run the new `migrate_to_fk` command — confirm all historical rows get a valid `party` FK
3. Query: `HistoricalResult2021.objects.filter(party__isnull=True).count()` should be 0
4. Run `python manage.py runserver` and hit `/api/historical/1/` — confirm response shape is unchanged
5. Cross-check party counts against the corrected tally JSON

### Manual Verification
- Check the admin panel for Alliance, Party, PartyAlias tables
- Verify the frontend HistoryPage still renders correctly
