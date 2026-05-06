"""
Fix all duplicate ECI→DB match assignments.
Uses FRESH match IDs from get_fresh_ids.py output.

Fixes:
  AC 5  THRIKARIPUR: 'MUSTHAFA V P S/O MUHAMMED' (match 52325) -> Musthafa V P (id=6054)
  AC 6  PAYYANUR:    'V. KUNHIKRISHNAN'           (match 52330) -> V. Kunjikrishnan (id=5517)
  AC 13 THALASSERY:  'RAJAN V P'                 (match 53365) -> V. P. Rajan (id=6103)
  AC 23 KOYILANDY:   'PRAVEEN KUMAR S/O SANKARAN NAIR' (match 53503) -> Praveen Kumar (id=6090)
  AC 24 PERAMBRA:    'FATHIMA NASRI. V'           (match 53487) -> Fathima Nasri.V (id=5960)
  AC 27 KZD NORTH:   'JAYANTH S S/O SADANANDAN'  (match 53484) -> Jayanth S (id=5979)
  AC 27 KZD NORTH:   'RAVEENDRAN S/O ARUMUGHAN'  (match 53488) -> Raveendran (id=6123)
  AC 27 KZD NORTH:   'RAVEENDRAN S/O THEYYATHIRA'(match 53490) -> Raveendran (id=6124)
  AC 36 WANDOOR:     'KUMARADAS'                 (match 53562) -> E. P. Kumaradas (id=5687)
  AC 37 MANJERI:     'V.M. MUSTHAFA'             (match 53519) -> V. M. Mustafa (id=5335)
  AC 42 VALLIKKUNNU: 'ADV. MUSTHAFA'             (match 53621) -> Adv. C. P. Musthafa (id=5340)
  AC 45 TIRUR:       'ABDURAHIMAN S/O KUNJAVA'   (match 53646) -> V. Abdurahman (id=5343)
  AC 47 THAVANUR:    'DR. K T JALEEL'            (match 53706) -> Dr. K. T. Jaleel (id=5345)
"""
from django.db import transaction
from core.models import (
    Constituency, Candidate, ECIScrapeRaw, ECICandidateMatch,
    CandidateAlias, LiveResult
)
from core.api.scraper_views import _execute_commit

FIXES = {
    52325: 6054,   # AC 5  THRIKARIPUR: MUSTHAFA V P S/O MUHAMMED -> Musthafa V P
    52330: 5517,   # AC 6  PAYYANUR: V. KUNHIKRISHNAN -> V. Kunjikrishnan (IND_UDF)
    53365: 6103,   # AC 13 THALASSERY: RAJAN V P -> V. P. Rajan
    53503: 6090,   # AC 23 KOYILANDY: PRAVEEN KUMAR S/O SANKARAN NAIR -> Praveen Kumar
    53487: 5960,   # AC 24 PERAMBRA: FATHIMA NASRI. V -> Fathima Nasri.V
    53484: 5979,   # AC 27 KZD NORTH: JAYANTH S S/O SADANANDAN -> Jayanth S
    53488: 6123,   # AC 27 KZD NORTH: RAVEENDRAN S/O ARUMUGHAN -> Raveendran (id=6123)
    53490: 6124,   # AC 27 KZD NORTH: RAVEENDRAN S/O THEYYATHIRA -> Raveendran (id=6124)
    53562: 5687,   # AC 36 WANDOOR: KUMARADAS -> E. P. Kumaradas (IND_NDA)
    53519: 5335,   # AC 37 MANJERI: V.M. MUSTHAFA -> V. M. Mustafa (IND_LDF)
    53621: 5340,   # AC 42 VALLIKKUNNU: ADV. MUSTHAFA -> Adv. C. P. Musthafa (IND_LDF)
    53646: 5343,   # AC 45 TIRUR: ABDURAHIMAN S/O KUNJAVA -> V. Abdurahman (IND)
    53706: 5345,   # AC 47 THAVANUR: DR. K T JALEEL -> Dr. K. T. Jaleel (IND_LDF)
}

print(f"Applying {len(FIXES)} match corrections...\n")

affected_scrape_ids = set()
errors = []

with transaction.atomic():
    for match_id, correct_cand_id in FIXES.items():
        try:
            match = ECICandidateMatch.objects.select_related(
                'scrape', 'scrape__constituency',
                'candidate', 'candidate__party'
            ).get(id=match_id)
        except ECICandidateMatch.DoesNotExist:
            msg = f"match_id={match_id} NOT FOUND"
            print(f"  ⚠ {msg}")
            errors.append(msg)
            continue

        try:
            new_cand = Candidate.objects.select_related('party').get(id=correct_cand_id)
        except Candidate.DoesNotExist:
            msg = f"DB candidate id={correct_cand_id} NOT FOUND (for match_id={match_id})"
            print(f"  ⚠ {msg}")
            errors.append(msg)
            continue

        constituency = match.scrape.constituency
        old_cand = match.candidate
        old_name = old_cand.name if old_cand else 'None'
        old_party = old_cand.party.code if old_cand and old_cand.party else '?'

        # Update the match record
        match.candidate = new_cand
        match.is_confirmed = True
        match.save()

        # Create/update alias for future auto-matching
        alias, created = CandidateAlias.objects.update_or_create(
            constituency=constituency,
            eci_name=match.eci_name,
            defaults={'candidate': new_cand}
        )

        new_party = new_cand.party.code if new_cand.party else '?'
        print(
            f"  ✅ AC {constituency.number:3d} {constituency.name:20s}  "
            f"ECI: {match.eci_name!r}  votes={match.eci_total_votes or 0}"
        )
        print(
            f"     OLD: {old_name!r} ({old_party})  →  "
            f"NEW: {new_cand.name!r} ({new_party})"
        )
        print(f"     Alias {'created' if created else 'updated'}")
        print()

        affected_scrape_ids.add(match.scrape_id)

print(f"Updated {len(FIXES) - len(errors)} match records.\n")

# Re-commit each affected scrape
print(f"Re-committing {len(affected_scrape_ids)} affected scrapes to DB + Firebase...\n")
committed = 0
for scrape_id in sorted(affected_scrape_ids):
    raw = ECIScrapeRaw.objects.select_related('constituency').get(id=scrape_id)
    c = raw.constituency
    try:
        _execute_commit(raw)
        print(f"  ✅ AC {c.number:3d} {c.name}")
        committed += 1
    except Exception as e:
        print(f"  ⚠ AC {c.number:3d} {c.name}  error: {e}")

print(f"\nRe-committed {committed}/{len(affected_scrape_ids)} scrapes.\n")

if errors:
    print(f"\n⚠ {len(errors)} errors:")
    for e in errors:
        print(f"  - {e}")

print("\n=== VERIFICATION — Final candidate votes for fixed seats ===\n")
AFFECTED_ACS = [5, 6, 13, 23, 24, 27, 36, 37, 42, 45, 47]
for ac_num in AFFECTED_ACS:
    c = Constituency.objects.get(number=ac_num)
    print(f"AC {ac_num}: {c.name}")
    for cand in Candidate.objects.filter(constituency=c).select_related('party').order_by('-votes'):
        print(f"  {cand.name!r:45s}  {cand.party.code if cand.party else '?':12s}  votes={cand.votes}")
    print()
