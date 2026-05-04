import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Constituency, Candidate, LiveResult, ECIScrapeRaw, ECICandidateMatch, CandidateAlias

for ac_num in [14, 15]:
    c = Constituency.objects.get(number=ac_num)
    print(f'=== AC {ac_num} {c.name} ===')

    # Show current candidate votes
    print('  DB Candidates (top 10 by votes):')
    for cand in Candidate.objects.filter(constituency=c).select_related('party').order_by('-votes')[:10]:
        print(f'    {cand.name} ({cand.party.code}) votes={cand.votes} leading={cand.is_leading}')

    # Show live result
    try:
        lr = LiveResult.objects.get(constituency=c)
        print(f'  LiveResult status={lr.status} rounds={lr.rounds_completed}/{lr.total_rounds}')
    except LiveResult.DoesNotExist:
        print('  No LiveResult')

    # Show aliases
    aliases = CandidateAlias.objects.filter(constituency=c)
    print(f'  Aliases ({aliases.count()}):')
    for a in aliases:
        print(f'    ECI:{a.eci_name!r} -> DB:{a.candidate.name!r} (AC {a.candidate.constituency.number})')

    # Show scrapes
    raws = ECIScrapeRaw.objects.filter(constituency=c).order_by('-scraped_at')
    print(f'  Scrapes ({raws.count()}):')
    for raw in raws[:3]:
        print(f'    id={raw.id} status={raw.match_status} scraped={raw.scraped_at}')
        matches = ECICandidateMatch.objects.filter(scrape=raw).select_related('candidate','candidate__constituency','candidate__party')
        for m in matches:
            cand_info = f'{m.candidate.name} (AC {m.candidate.constituency.number})' if m.candidate else 'UNMATCHED'
            print(f'      ECI:{m.eci_name!r}({m.eci_party}) -> {cand_info} confirmed={m.is_confirmed}')
    print()
