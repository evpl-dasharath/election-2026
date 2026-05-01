import django, os, sys
sys.path.insert(0, '.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()
from core.models import HistoricalResult2021, PartyAllianceYear

# Get all unique party codes in the 2021 data
parties_in_data = set(HistoricalResult2021.objects.values_list('party_code', flat=True).distinct())

# Get all party codes we have mapped for 2021 LA
mapped = set(PartyAllianceYear.objects.filter(election_year=2021, election_type='LA').values_list('party_code', flat=True))

unmapped = parties_in_data - mapped
print(f'Total unique party codes in 2021 data: {len(parties_in_data)}')
print(f'Total mapped in PartyAllianceYear: {len(mapped)}')
print(f'UNMAPPED (going to OTH fallback): {sorted(unmapped)}')
print()
print('All parties in 2021 data:')
for p in sorted(parties_in_data):
    alliance = PartyAllianceYear.objects.filter(party_code=p, election_year=2021, election_type='LA').values_list('alliance', flat=True).first()
    label = alliance if alliance else 'OTH (fallback - MISSING)'
    print(f'  {p:20s} -> {label}')
