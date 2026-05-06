"""
Print fresh match IDs for all duplicate cases so fix script uses current IDs.
"""
from collections import defaultdict
from core.models import ECIScrapeRaw

AFFECTED_ACS = [1, 5, 6, 13, 23, 24, 27, 36, 37, 42, 45, 47]

seen = {}
for raw in ECIScrapeRaw.objects.select_related('constituency').order_by(
    'constituency__number', '-scraped_at'
):
    cid = raw.constituency_id
    if cid not in seen:
        seen[cid] = raw

for raw in seen.values():
    c = raw.constituency
    if c.number not in AFFECTED_ACS:
        continue

    confirmed = list(
        raw.matches.filter(is_confirmed=True, is_nota=False, candidate__isnull=False)
           .select_related('candidate', 'candidate__party')
    )
    db_id_to_matches = defaultdict(list)
    for m in confirmed:
        db_id_to_matches[m.candidate_id].append(m)
    dup_db_ids = {cid for cid, ms in db_id_to_matches.items() if len(ms) > 1}

    if not dup_db_ids:
        continue

    print(f"\nAC {c.number}: {c.name}  [scrape_id={raw.id}]")
    for m in raw.matches.select_related('candidate', 'candidate__party').order_by('-eci_total_votes'):
        if m.is_nota:
            continue
        dupe = " ◄ DUPE" if m.candidate_id in dup_db_ids else ""
        cname = m.candidate.name if m.candidate else "UNMATCHED"
        cid_str = str(m.candidate_id) if m.candidate_id else "-"
        print(f"  match_id={m.id:6d}  ECI:{m.eci_name!r:42s} votes={m.eci_total_votes or 0:6d}  DB id={cid_str} {cname!r}{dupe}")
