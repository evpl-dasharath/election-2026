import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Constituency, Candidate, ECIScrapeRaw, ECICandidateMatch, LiveResult

for ac_num in [67, 13]:
    try:
        c = Constituency.objects.get(number=ac_num)
        print(f'\n{"="*60}')
        print(f'AC {ac_num}: {c.name}')
        print(f'{"="*60}')
        cands = Candidate.objects.filter(constituency=c).select_related('party')
        print(f'DB Candidates ({cands.count()}):')
        for cand in cands:
            print(f'  {cand.name!r:40s} | party={cand.party.code if cand.party else "?"} | votes={cand.votes}')

        # LiveResult
        lr = LiveResult.objects.filter(constituency=c).first()
        if lr:
            print(f'\nLiveResult: status={lr.status} | leading={lr.leading_candidate}')

        # Check latest scrape
        raw = ECIScrapeRaw.objects.filter(constituency=c).order_by('-scraped_at').first()
        if raw:
            print(f'\nLatest scrape: match_status={raw.match_status} at {raw.scraped_at}')
            print(f'Raw ECI candidates:')
            for rc in raw.raw_candidates:
                print(f'  {rc["name"]!r:40s} | party={rc.get("party","?")} | votes={rc.get("votes",0)}')
            print(f'\nMatch records:')
            for m in raw.matches.select_related('candidate', 'candidate__party').all():
                cname = m.candidate.name if m.candidate else 'UNMATCHED'
                party = m.candidate.party.code if m.candidate and m.candidate.party else '?'
                print(f'  ECI={m.eci_name!r:40s} -> DB={cname!r} ({party}) | confirmed={m.is_confirmed} | nota={m.is_nota}')
        else:
            print('\nNo scrape records found')
    except Constituency.DoesNotExist:
        print(f'AC {ac_num} not found in DB')
    except Exception as e:
        import traceback
        traceback.print_exc()

# Also scan ALL constituencies for PARTIAL match status (might reveal more affected seats)
print('\n\n' + '='*60)
print('ALL PARTIAL/PENDING scrapes (potential missing candidates):')
print('='*60)
partials = ECIScrapeRaw.objects.filter(
    match_status__in=['PARTIAL', 'PENDING']
).select_related('constituency').order_by('constituency__number')

# Get only latest per constituency
seen = set()
for raw in partials:
    cid = raw.constituency_id
    if cid in seen:
        continue
    seen.add(cid)
    c = raw.constituency
    unmatched = raw.matches.filter(candidate__isnull=True, is_nota=False).count()
    total = raw.matches.filter(is_nota=False).count()
    matched = raw.matches.filter(candidate__isnull=False, is_nota=False).count()
    # List unmatched ECI names
    unmatched_names = list(raw.matches.filter(candidate__isnull=True, is_nota=False).values_list('eci_name', 'eci_party'))
    print(f'  AC {c.number:3d} {c.name:30s} | {matched}/{total} matched | unmatched: {unmatched_names}')
