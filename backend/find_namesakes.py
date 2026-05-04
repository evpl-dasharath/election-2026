from core.models import Candidate, Constituency
queries = [
    (36, 'Kumar'), (36, 'Kumaradas'), (36, 'Kumarads'),
    (24, 'Fathima'), (24, 'Nasri'),
    (27, 'Raveendran'), (27, 'Raveendranathan'), (27, 'Jayanth'),
]
for ac_num, search in queries:
    c = Constituency.objects.get(number=ac_num)
    matches = Candidate.objects.filter(constituency=c, name__icontains=search).select_related('party')
    for m in matches:
        print(f'AC {ac_num} {c.name}: id={m.pk} name={m.name!r} party={m.party.code if m.party else "?"} votes={m.votes}')
