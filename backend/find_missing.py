import os
import django
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Constituency, Candidate, Party, LiveResult

ldf_parties = Party.objects.filter(alliance__code='LDF')
ldf_c = Candidate.objects.filter(party__in=ldf_parties).values_list('constituency_id', flat=True)

all_c = set(Constituency.objects.values_list('id', flat=True))
contested = set(ldf_c)
missing = all_c - contested

print('Missing LDF contested constituencies count:', len(missing))
for cid in missing:
    c = Constituency.objects.get(id=cid)
    print(f"Missing LDF in: {c.number} - {c.name}")
    for cand in c.candidates_2026.all():
        pc = cand.party.code if cand.party else cand.name
        print(f"  - {pc}: {cand.name} (Votes: {cand.votes})")
