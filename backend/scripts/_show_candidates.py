from core.models import Constituency, Candidate

for ac_num in [14, 15]:
    c = Constituency.objects.get(number=ac_num)
    print(f'=== AC {ac_num} {c.name} — DB Candidates ===')
    for cand in Candidate.objects.filter(constituency=c).select_related('party').order_by('party__alliance__code', 'name'):
        print(f'  id={cand.id} {cand.name!r:40s} party={cand.party.code}')
    print()
