"""
Fix the MATTANUR (AC14) / KUTHUPARAMBA (AC15) cross-mismatch.

Steps:
1. Delete bad CandidateAlias entries for both constituencies
2. Delete all ECIScrapeRaw + ECICandidateMatch records for both (cascades)
3. Reset all candidate votes/leading/winner for both
4. Reset LiveResult for both back to NOT_STARTED
5. Clear RTDB nodes for both
"""
from core.models import (
    Constituency, Candidate, LiveResult,
    ECIScrapeRaw, CandidateAlias
)

ACS = [14, 15]

for ac_num in ACS:
    c = Constituency.objects.get(number=ac_num)
    print(f'=== Cleaning AC {ac_num} {c.name} ===')

    # 1. Nuke all aliases (they may be wrong)
    n_alias, _ = CandidateAlias.objects.filter(constituency=c).delete()
    print(f'  Deleted {n_alias} CandidateAlias entries')

    # 2. Delete all raw scrapes (cascades to ECICandidateMatch)
    n_raw, _ = ECIScrapeRaw.objects.filter(constituency=c).delete()
    print(f'  Deleted {n_raw} ECIScrapeRaw records (+ their matches)')

    # 3. Reset candidate votes
    n_cands = Candidate.objects.filter(constituency=c).update(
        votes=0, vote_percentage=0, is_leading=False, is_winner=False
    )
    print(f'  Reset {n_cands} candidates to votes=0')

    # 4. Reset LiveResult
    n_lr = LiveResult.objects.filter(constituency=c).update(
        status='NOT_STARTED',
        rounds_completed=0,
        total_rounds=0,
    )
    print(f'  Reset {n_lr} LiveResult(s) to NOT_STARTED')

    # 5. Clear RTDB node
    try:
        from firebase_rtdb import init_firebase
        from firebase_admin import db as rtdb_db
        if init_firebase():
            rtdb_db.reference(f'/live/{ac_num}').delete()
            print(f'  Cleared RTDB /live/{ac_num}')
    except Exception as e:
        print(f'  RTDB clear skipped: {e}')

    print()

print('Done. Both constituencies are clean — re-scrape them via the admin panel.')
