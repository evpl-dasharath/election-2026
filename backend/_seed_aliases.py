from core.models import Constituency, Candidate, CandidateAlias

def seed_aliases():
    # AC 81
    c81 = Constituency.objects.get(number=81)
    aliases_81 = [
        ('K N UNNIKRISHNAN', 'K. N. Unnikrishnan'),
        ('THOMAS PAUL KOMAROTH', 'Thomas Paul'),
        ('DEEPAK JOY', 'Deepak Joy'),
        ('ANJALI .P. V', 'Anjali .P. V'),
    ]
    print('AC 81 aliases:')
    for eci_name, db_name in aliases_81:
        try:
            cand = Candidate.objects.get(constituency=c81, name=db_name)
            obj, created = CandidateAlias.objects.get_or_create(
                constituency=c81, eci_name=eci_name,
                defaults={'candidate': cand}
            )
            print(f'  {"created" if created else "exists"}: {eci_name!r} -> {db_name!r}')
        except Candidate.DoesNotExist:
            print(f'  NOT FOUND in DB: {db_name!r}')

    # AC 109
    c109 = Constituency.objects.get(number=109)
    aliases_109 = [
        ('K. AJIMON', 'Ajimon'),
        ('M.S. ARUN KUMAR', 'M. S. Arun Kumar'),
        ('ADV. MUTHARA RAJ', 'Adv. Muthara Raj'),
    ]
    print('AC 109 aliases:')
    for eci_name, db_name in aliases_109:
        try:
            cand = Candidate.objects.get(constituency=c109, name=db_name)
            obj, created = CandidateAlias.objects.get_or_create(
                constituency=c109, eci_name=eci_name,
                defaults={'candidate': cand}
            )
            print(f'  {"created" if created else "exists"}: {eci_name!r} -> {db_name!r}')
        except Candidate.DoesNotExist:
            print(f'  NOT FOUND in DB: {db_name!r}')

if __name__ == '__main__':
    seed_aliases()
