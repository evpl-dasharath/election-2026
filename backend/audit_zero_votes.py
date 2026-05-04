"""
Audit v2: For each constituency, examine only the LATEST scrape record.
Find:
  1. Confirmed matches with ECI votes > 0 but DB candidate.votes == 0
  2. Duplicate DB candidate assignments in that scrape
  3. Candidates with 0 votes in active (IN_PROGRESS/RESULT_DECLARED) seats
"""
from collections import defaultdict
from core.models import Constituency, Candidate, ECIScrapeRaw, LiveResult

print("Scanning all constituencies (latest scrape only)...\n")

case1_problems = []   # ECI votes committed to wrong place
case2_dupes    = []   # two ECI names -> same DB candidate
case3_zero     = []   # active seat with a named candidate at 0 votes

# Build latest-scrape-per-constituency map
seen = {}
for raw in ECIScrapeRaw.objects.select_related('constituency').order_by(
    'constituency__number', '-scraped_at'
):
    cid = raw.constituency_id
    if cid not in seen:
        seen[cid] = raw

latest_raws = list(seen.values())

for raw in latest_raws:
    c = raw.constituency

    confirmed = list(
        raw.matches.filter(is_confirmed=True, is_nota=False, candidate__isnull=False)
           .select_related('candidate', 'candidate__party')
    )

    # ── Case 1: ECI votes > 0 but DB candidate still shows 0 ────────────────
    for m in confirmed:
        eci_v = m.eci_total_votes or 0
        db_v  = m.candidate.votes  or 0
        if eci_v > 0 and db_v == 0:
            case1_problems.append({
                'ac':        c.number,
                'seat':      c.name,
                'eci_name':  m.eci_name,
                'eci_party': m.eci_party,
                'db_cand':   m.candidate.name,
                'db_party':  m.candidate.party.code if m.candidate.party else '?',
                'eci_votes': eci_v,
            })

    # ── Case 2: duplicate DB-candidate assignment ────────────────────────────
    db_id_to_matches = defaultdict(list)
    for m in confirmed:
        db_id_to_matches[m.candidate_id].append(m)
    for db_cand_id, matches in db_id_to_matches.items():
        if len(matches) > 1:
            # Only flag when at least one of the ECI entries has > 0 votes (real issue)
            if any(m.eci_total_votes for m in matches):
                first = matches[0]
                case2_dupes.append({
                    'ac':      c.number,
                    'seat':    c.name,
                    'db_cand': first.candidate.name,
                    'db_party': first.candidate.party.code if first.candidate.party else '?',
                    'eci_entries': [(m.eci_name, m.eci_total_votes or 0) for m in matches],
                })

# ── Case 3: active seats where a candidate has 0 votes and ECI is > 0 in raw ─
# (catches seats where the commit was skipped or partial)
active_lrs = {
    lr.constituency_id: lr
    for lr in LiveResult.objects.filter(status__in=['IN_PROGRESS', 'RESULT_DECLARED'])
}
for raw in latest_raws:
    c = raw.constituency
    if c.pk not in active_lrs:
        continue
    for m in raw.matches.filter(is_nota=False).select_related('candidate', 'candidate__party'):
        eci_v = m.eci_total_votes or 0
        if eci_v == 0:
            continue
        if not m.candidate:
            # Unmatched and has votes — also bad
            case3_zero.append({
                'ac':        c.number,
                'seat':      c.name,
                'eci_name':  m.eci_name,
                'eci_party': m.eci_party,
                'db_cand':   'UNMATCHED',
                'db_party':  '?',
                'eci_votes': eci_v,
                'confirmed': m.is_confirmed,
                'issue':     'UNMATCHED_WITH_VOTES',
            })
        elif (m.candidate.votes or 0) == 0:
            case3_zero.append({
                'ac':        c.number,
                'seat':      c.name,
                'eci_name':  m.eci_name,
                'eci_party': m.eci_party,
                'db_cand':   m.candidate.name,
                'db_party':  m.candidate.party.code if m.candidate.party else '?',
                'eci_votes': eci_v,
                'confirmed': m.is_confirmed,
                'issue':     'ZERO_VOTES_IN_ACTIVE_SEAT',
            })

# ── Print results ─────────────────────────────────────────────────────────────
print("=" * 72)
print(f"CASE 1: Matched candidate has ECI votes > 0 but DB votes = 0  [{len(case1_problems)} issues]")
print("=" * 72)
for p in case1_problems:
    print(f"  AC {p['ac']:3d} {p['seat']:28s}  ECI: {p['eci_name'][:35]!r} ({p['eci_party'][:25]})")
    print(f"  {'':38s}  DB:  {p['db_cand'][:35]!r} ({p['db_party']})  ECI_votes={p['eci_votes']}")
if not case1_problems:
    print("  ✅ None!")

print()
print("=" * 72)
print(f"CASE 2: Two ECI candidates mapped to the same DB candidate      [{len(case2_dupes)} issues]")
print("=" * 72)
for p in case2_dupes:
    print(f"  AC {p['ac']:3d} {p['seat']:28s}  DB cand: {p['db_cand']!r} ({p['db_party']})")
    for eci_name, votes in p['eci_entries']:
        print(f"  {'':38s}  → ECI: {eci_name!r}  votes={votes}")
if not case2_dupes:
    print("  ✅ None!")

print()
print("=" * 72)
print(f"CASE 3: Active seat — ECI has votes but DB candidate shows 0    [{len(case3_zero)} issues]")
print("=" * 72)
for p in sorted(case3_zero, key=lambda x: x['ac']):
    flag = "⚠ UNMATCHED" if p['issue'] == 'UNMATCHED_WITH_VOTES' else "⚠ ZERO DB"
    print(f"  AC {p['ac']:3d} {p['seat']:28s}  {flag}  ECI: {p['eci_name'][:30]!r} ({p['eci_party'][:20]})  eci_votes={p['eci_votes']}")
    if p['db_cand'] != 'UNMATCHED':
        print(f"  {'':38s}  DB:  {p['db_cand']!r} ({p['db_party']})")
if not case3_zero:
    print("  ✅ None!")

print()
print("=" * 72)
total_issues = len(case1_problems) + len(case2_dupes) + len(case3_zero)
affected_seats = len({p['ac'] for p in case1_problems + case2_dupes + case3_zero})
print(f"TOTAL: {total_issues} issues across {affected_seats} constituencies")
print("=" * 72)
