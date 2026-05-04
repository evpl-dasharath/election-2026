"""
Fix bad matches for AC 67 (THRISSUR) and AC 13 (THALASSERY).

Bad matches found:
- AC 67: ECI 'RAJAN. J. PALLAN' (INC) matched to 'Rajan. M' (IND) -- wrong
- AC 13: ECI 'SAJU K P' (INC) matched to 'Saju V P' (IND) -- wrong
         ECI 'RAJAN V P' (IND) matched to 'Rajan O P' (IND) -- duplicate (may be valid but unusual)

Fix:
1. Delete ALL existing ECIScrapeRaw + ECICandidateMatch + CandidateAlias for these ACs
2. Reset candidate votes to 0
3. Re-commit the latest scrape with correct matching
"""
from core.models import (
    Constituency, Candidate, ECIScrapeRaw, ECICandidateMatch,
    CandidateAlias, LiveResult
)
from core.admin_scraper_views import _save_scrape_to_db, _normalise, _resolve_eci_party_code

for ac_num in [67, 13]:
    c = Constituency.objects.get(number=ac_num)
    print(f'\n{"="*60}')
    print(f'Fixing AC {ac_num}: {c.name}')
    print(f'{"="*60}')

    # 1. Collect the latest raw scrape data before deleting
    latest_raw = ECIScrapeRaw.objects.filter(constituency=c).order_by('-scraped_at').first()
    if not latest_raw:
        print('  No scrape records — skipping')
        continue

    # Save the ECI data we need to re-process
    saved_scrape_data = {
        'rounds_completed': latest_raw.rounds_completed,
        'total_rounds': latest_raw.total_rounds,
        'is_final': latest_raw.is_final,
        'eci_last_updated': latest_raw.eci_last_updated,
        'candidates': latest_raw.raw_candidates,
        'success': True,
        'constituency_name': c.name,
    }
    print(f'  Saved ECI data: {len(saved_scrape_data["candidates"])} candidates')

    # 2. Delete all aliases for this constituency
    alias_count = CandidateAlias.objects.filter(constituency=c).count()
    CandidateAlias.objects.filter(constituency=c).delete()
    print(f'  Deleted {alias_count} aliases')

    # 3. Delete all ECIScrapeRaw (cascades to ECICandidateMatch)
    raw_count = ECIScrapeRaw.objects.filter(constituency=c).count()
    ECIScrapeRaw.objects.filter(constituency=c).delete()
    print(f'  Deleted {raw_count} scrape records (+ their matches)')

    # 4. Reset all candidate votes to 0
    Candidate.objects.filter(constituency=c).update(votes=0, vote_percentage=0, is_leading=False, is_winner=False)
    print(f'  Reset candidate votes to 0')

    # 5. Re-run the matching with the fixed logic
    print(f'  Re-saving scrape with fixed matching...')
    new_raw = _save_scrape_to_db(ac_num, saved_scrape_data)
    if new_raw:
        print(f'  New match_status: {new_raw.match_status}')
        print(f'  Matches:')
        for m in new_raw.matches.select_related('candidate', 'candidate__party').all():
            cname = m.candidate.name if m.candidate else 'UNMATCHED'
            party = m.candidate.party.code if m.candidate and m.candidate.party else '?'
            print(f'    ECI={m.eci_name!r:40s} -> DB={cname!r} ({party}) confirmed={m.is_confirmed}')
    else:
        print(f'  ERROR: Failed to re-save scrape')

print('\n\nDone. Checking final candidate votes:')
for ac_num in [67, 13]:
    c = Constituency.objects.get(number=ac_num)
    print(f'\nAC {ac_num}: {c.name}')
    for cand in Candidate.objects.filter(constituency=c).select_related('party').order_by('-votes'):
        print(f'  {cand.name:40s} | {cand.party.code if cand.party else "?":10s} | votes={cand.votes}')
