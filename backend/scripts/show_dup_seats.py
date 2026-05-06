"""
For each constituency with duplicate ECI→DB mappings, show:
  - All DB candidates (id, name, party, votes)
  - The ECI duplicate matches (eci_name, eci_party, eci_votes)
So we can manually identify the correct mapping.
"""
from collections import defaultdict
from core.models import Constituency, Candidate, ECIScrapeRaw, ECICandidateMatch

# The 12 affected AC numbers from the audit
AFFECTED_ACS = [1, 5, 6, 13, 23, 24, 27, 36, 37, 42, 45, 47]

# Build latest-scrape map
seen = {}
for raw in ECIScrapeRaw.objects.select_related('constituency').order_by(
    'constituency__number', '-scraped_at'
):
    cid = raw.constituency_id
    if cid not in seen:
        seen[cid] = raw

for ac_num in AFFECTED_ACS:
    try:
        c = Constituency.objects.get(number=ac_num)
    except Constituency.DoesNotExist:
        continue

    raw = seen.get(c.pk)
    if not raw:
        continue

    # Find the duplicate DB candidate IDs in this scrape
    confirmed = list(
        raw.matches.filter(is_confirmed=True, is_nota=False, candidate__isnull=False)
           .select_related('candidate', 'candidate__party')
    )
    db_id_to_matches = defaultdict(list)
    for m in confirmed:
        db_id_to_matches[m.candidate_id].append(m)
    dup_db_ids = {cid for cid, matches in db_id_to_matches.items() if len(matches) > 1}

    if not dup_db_ids:
        continue

    print(f"\n{'='*72}")
    print(f"AC {ac_num}: {c.name}")
    print(f"{'='*72}")

    # Show ALL DB candidates for this seat
    print("  ALL DB CANDIDATES:")
    all_db = list(Candidate.objects.filter(constituency=c).select_related('party').order_by('-votes'))
    for cand in all_db:
        marker = " ◄ DUPLICATE TARGET" if cand.pk in dup_db_ids else ""
        print(f"    id={cand.pk:6d}  {cand.name!r:45s}  party={cand.party.code if cand.party else '?':12s}  votes={cand.votes}{marker}")

    # Show ALL ECI matches (to see context)
    print(f"\n  ALL ECI MATCH RECORDS (match_status={raw.match_status}):")
    for m in raw.matches.select_related('candidate', 'candidate__party').order_by('-eci_total_votes'):
        if m.is_nota:
            continue
        db_name = m.candidate.name if m.candidate else 'UNMATCHED'
        db_party = m.candidate.party.code if m.candidate and m.candidate.party else '?'
        db_id = m.candidate_id or '-'
        dup_flag = " ◄ DUPE" if m.candidate_id in dup_db_ids else ""
        print(f"    match_id={m.id:6d}  ECI: {m.eci_name!r:40s} ({m.eci_party[:25]!r:27s})  votes={m.eci_total_votes or 0:6d}")
        print(f"    {'':10s}         DB:  {db_name!r:40s} ({db_party:12s}) id={db_id}{dup_flag}")
        print()
