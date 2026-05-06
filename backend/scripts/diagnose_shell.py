from core.models import Constituency, Candidate, ECIScrapeRaw, ECICandidateMatch, LiveResult

for ac_num in [67, 13]:
    try:
        c = Constituency.objects.get(number=ac_num)
        print(f'\n{"="*60}')
        print(f'AC {ac_num}: {c.name}')
        print(f'{"="*60}')

        # LiveResult
        lr = LiveResult.objects.filter(constituency=c).first()
        if lr:
            print(f'LiveResult: status={lr.status}')

        # Check ALL scrapes (latest first)
        raws = ECIScrapeRaw.objects.filter(constituency=c).order_by('-scraped_at')
        print(f'Total scrape records: {raws.count()}')
        
        raw = raws.first()
        if raw:
            print(f'\nLatest scrape: match_status={raw.match_status} at {raw.scraped_at}')
            print(f'Raw ECI candidates ({len(raw.raw_candidates)}):')
            for rc in raw.raw_candidates:
                print(f'  name={rc["name"]!r:40s} | party={rc.get("party","?")} | votes={rc.get("votes",0)}')
            print(f'\nMatch records ({raw.matches.count()}):')
            for m in raw.matches.select_related('candidate', 'candidate__party').all():
                cname = m.candidate.name if m.candidate else 'UNMATCHED'
                party = m.candidate.party.code if m.candidate and m.candidate.party else '?'
                print(f'  ECI={m.eci_name!r:40s} eci_party={m.eci_party!r} -> DB={cname!r} ({party}) confirmed={m.is_confirmed} nota={m.is_nota}')
        else:
            print('\nNo scrape records found')
    except Exception as e:
        import traceback
        traceback.print_exc()

# Scan ALL constituencies for PARTIAL/PENDING match status
print('\n\n' + '='*60)
print('ALL PARTIAL/PENDING scrapes:')
print('='*60)
from django.db.models import Q
partials = ECIScrapeRaw.objects.filter(
    match_status__in=['PARTIAL', 'PENDING']
).select_related('constituency').order_by('constituency__number')

seen = set()
for raw in partials:
    cid = raw.constituency_id
    if cid in seen:
        continue
    seen.add(cid)
    c = raw.constituency
    total = raw.matches.filter(is_nota=False).count()
    matched = raw.matches.filter(candidate__isnull=False, is_nota=False).count()
    unmatched_items = list(raw.matches.filter(candidate__isnull=True, is_nota=False).values_list('eci_name', 'eci_party'))
    print(f'  AC {c.number:3d} {c.name:30s} | {matched}/{total} matched | unmatched: {unmatched_items}')
