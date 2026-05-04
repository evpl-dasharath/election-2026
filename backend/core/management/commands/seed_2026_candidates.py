"""
Seed 2026 election candidates from kla2026_candidates.csv.
Also creates IND_LDF / IND_UDF / IND_NDA party entries for alliance-backed independents.

Usage:
    python manage.py seed_2026_candidates --csv ../data/kla2026_candidates.csv
    python manage.py seed_2026_candidates --csv ../data/kla2026_candidates.csv --clear
"""
import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Alliance, Party, PartyAllianceYear, Constituency, Candidate, LiveResult

# Map CSV party strings -> canonical Party.code
PARTY_MAP = {
    # LDF
    'CPI(M)':                          'CPI_M',
    'CPI':                             'CPI',
    'Kerala Congress (B)':             'KC_B',
    'Kerala Congress (M)':             'KC_M',
    'INL':                             'INL',
    'NCP':                             'NCP',
    'JKC':                             'JKC',
    'Congress (Secular)':              'CON_S',
    'Indian Socialist Janata Dal':     'ISJD',
    'RJD':                             'RJD',
    'LJD':                             'LJD',
    # UDF
    'INC':                             'INC',
    'IUML':                            'IUML',
    'KEC':                             'KEC',
    'KC(J)':                           'KC_J',
    'Kerala Congress (J)':             'KC_J',
    'RSP':                             'RSP',
    'CMP':                             'CMP',
    'RMPI':                            'RMPI',
    'AITC':                            'AITC',
    'DCK':                             'KDP',
    'KDP':                             'KDP',
    'AIFB':                            'AIFB',
    # NDA
    'BJP':                             'BJP',
    'BDJS':                            'BDJS',
    'TTP':                             'TTP',
    'Twenty20':                        'TTP',
    'Twenty20 Party':                  'TTP',
    'AIADMK':                          'AIADMK',
    'JRS':                             'JRS',
    'KKC':                             'KKC',
    # others
    'AAP':                             'AAP',
    'BSP':                             'BSP',
    'SDPI':                            'SDPI',
    'SUCI':                            'SUCI',
    'WPOI':                            'WPOI',
    'CPIML Liberation':                'CPI_ML_L',
    'CPIML Red Star':                  'CPI_ML_RS',
    # Alliance-backed independents -> special party codes
    'Independent (CPI(M) support)':    'IND_LDF',
    'Independent (CPI support)':       'IND_LDF',
    'Independent (INL support)':       'IND_LDF',
    'Independent (INL Support)':       'IND_LDF',
    'Independent (INC Support)':       'IND_UDF',
    'Independent (IUML Support)':      'IND_UDF',
    'Independent (RSP support)':       'IND_UDF',
    'BJP (Independent)':               'IND_NDA',
    'Independent (BJP support)':       'IND_NDA',
}

ALLIANCE_BACKED_IND = {
    'IND_LDF': ('LDF', 'Independent (LDF)', '#CC2222'),
    'IND_UDF': ('UDF', 'Independent (UDF)', '#1277C0'),
    'IND_NDA': ('NDA', 'Independent (NDA)', '#D97706'),
}

# CSV constituencyName -> DB constituency number (spelling differs from ECI canonical)
# NOTE: DB numbers match ECI canonical numbering.
# ECI AC14 = KUTHUPARAMBA, ECI AC15 = MATTANUR (corrected 2026-05-04)
NAME_OVERRIDES = {
    'Udma':              3,    # UDMA
    'Thrikaripur':       5,    # THRIKARIPUR
    'Azhikode':          10,   # AZHIKODE
    'Irikkur':           9,    # IRIKKUR
    'Taliparamba':       8,    # TALIPARAMBA
    'Dharmadom':         12,   # DHARMADOM
    'Mattanur':          15,   # MATTANUR (ECI AC 15)
    'Kuthuparamba':      14,   # KUTHUPARAMBA (ECI AC 14)
    'Vatakara':          20,   # VADAKARA
    'Kuttiady':          21,   # KUTTIADI
    'Kottakkal':         46,   # KOTTAKKAL
    'Vallikkunnu':       42,   # VALLIKKUNNU
    'Thanur':            44,   # TANUR
    'Mankada':           39,   # MANKADA
    'Vengara':           41,   # VENGARA
    'Guruvayur':         58,   # GURUVAYOOR
    'Wadakkanchery':     56,   # CHELAKKARA (Wadakkanchery is alternate)
    'Karunagapally':     116,  # KARUNAGAPALLY
    'Kozhikode North':   27,   # KOZHIKODE NORTH
    'Kozhikode South':   28,   # KOZHIKODE SOUTH
    'Sulthan Bathery':   18,   # SULTHAN BATHERY (ECI AC 18)
    'Kochi':             80,   # KOCHI
    'Thripunithura':     81,   # THRIPPUNITHURA
    'Vypeen':            73,   # VYPIN
    'Haripad':           107,  # HARIPAD
    'Mavelikkara':       109,  # MAVELIKARA
    'Puthuppally':       94,   # KADUTHURUTHY
    'Chathannoor':       126,  # CHATHANNOOR
    'Payyanur':          6,    # PAYYANNUR
    'Kazhakoottam':      132,  # KAZHAKOOTAM
    'Kazhakkoottam':     132,  # KAZHAKOOTAM
}


class Command(BaseCommand):
    help = 'Seed 2026 candidates from kla2026_candidates.csv'

    def add_arguments(self, parser):
        parser.add_argument('--csv', type=str, default='../data/kla2026_candidates.csv')
        parser.add_argument('--clear', action='store_true')

    def handle(self, *args, **options):
        if options['clear']:
            n = Candidate.objects.count()
            Candidate.objects.all().delete()
            LiveResult.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {n} candidates and all live results'))

        # 1. Ensure IND_LDF / IND_UDF / IND_NDA parties exist
        self.stdout.write('Ensuring alliance-backed IND parties...')
        alliance_cache = {a.code: a for a in Alliance.objects.all()}
        ind_party_cache = {}
        for code, (al_code, name, color) in ALLIANCE_BACKED_IND.items():
            al = alliance_cache[al_code]
            party, created = Party.objects.update_or_create(
                code=code,
                defaults={'full_name': name, 'alliance': al, 'color_code': color}
            )
            # Ensure PartyAllianceYear for 2026
            PartyAllianceYear.objects.update_or_create(
                party=party, election_year=2026, election_type='LA',
                defaults={'alliance': al, 'color_code': color}
            )
            ind_party_cache[code] = party
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created {code}'))

        # 2. Build lookup caches
        party_cache = {p.code: p for p in Party.objects.select_related('alliance').all()}
        const_by_name = {}  # uppercase name -> Constituency
        for c in Constituency.objects.all():
            const_by_name[c.name.upper()] = c
        # also index by title-case for direct match
        const_by_titlename = {c.name.title(): c for c in Constituency.objects.all()}

        def find_constituency(csv_name: str):
            name = csv_name.strip()
            # Direct uppercase match
            up = name.upper()
            if up in const_by_name:
                return const_by_name[up]
            # Override map (handles alternate spellings)
            if name in NAME_OVERRIDES:
                return Constituency.objects.get(number=NAME_OVERRIDES[name])
            # Try replacing common suffix variants
            variants = [
                up.replace('PPALLY', 'PPALLY'),
                up + 'AM',
                up.rstrip('A') + 'AM',
            ]
            for v in variants:
                if v in const_by_name:
                    return const_by_name[v]
            # Prefix match (min 7 chars)
            if len(up) >= 7:
                for k, v in const_by_name.items():
                    if k.startswith(up[:7]) or up.startswith(k[:7]):
                        return v
            return None

        def resolve_party(csv_party: str, alliance: str):
            """Resolve CSV party name to a Party object."""
            raw = csv_party.strip()
            # Empty string or unknown independents -> plain IND
            if not raw or raw.lower() in ('independent', 'ind'):
                al_upper = alliance.upper()
                if al_upper == 'LDF':
                    return party_cache.get('IND_LDF', party_cache['IND'])
                if al_upper == 'UDF':
                    return party_cache.get('IND_UDF', party_cache['IND'])
                if al_upper == 'NDA':
                    return party_cache.get('IND_NDA', party_cache['IND'])
                return party_cache['IND']
            # Direct map
            code = PARTY_MAP.get(raw)
            if code and code in party_cache:
                return party_cache[code]
            # Plain independent keyword -> alliance-specific IND
            if 'independent' in raw.lower():
                al_upper = alliance.upper()
                if al_upper == 'LDF':
                    return party_cache.get('IND_LDF', party_cache['IND'])
                if al_upper == 'UDF':
                    return party_cache.get('IND_UDF', party_cache['IND'])
                if al_upper == 'NDA':
                    return party_cache.get('IND_NDA', party_cache['IND'])
                return party_cache['IND']
            # Try exact code match
            if raw in party_cache:
                return party_cache[raw]
            # Fallback: create stub OTH
            oth = alliance_cache['OTH']
            stub_code = raw[:20]
            stub, _ = Party.objects.get_or_create(
                code=stub_code,
                defaults={'full_name': raw, 'alliance': oth, 'color_code': '#808080'}
            )
            party_cache[stub.code] = stub
            self.stdout.write(self.style.WARNING(f'  Stub party: {raw!r}'))
            return stub

        # 3. Read CSV and create candidates
        self.stdout.write(f'\nReading {options["csv"]}...')
        created = skipped = 0
        unknown_consts = set()

        with open(options['csv'], encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))

        with transaction.atomic():
            for row in rows:
                const_name = row.get('constituencyName', '').strip()
                csv_party = row.get('party', '').strip()
                csv_alliance = row.get('alliance', '').strip()
                candidate_name = row.get('candidateName', '').strip()

                if not candidate_name or not const_name:
                    skipped += 1
                    continue

                constituency = find_constituency(const_name)
                if not constituency:
                    if const_name not in unknown_consts:
                        self.stdout.write(self.style.WARNING(f'  Unknown constituency: {const_name!r}'))
                        unknown_consts.add(const_name)
                    skipped += 1
                    continue

                party = resolve_party(csv_party, csv_alliance)

                age_str = row.get('candidateAge', '').strip()
                try:
                    age = int(age_str) if age_str else None
                except ValueError:
                    age = None

                Candidate.objects.create(
                    name=candidate_name,
                    party=party,
                    constituency=constituency,
                    votes=0,
                    vote_percentage=0,
                )
                created += 1

        # 4. Create LiveResult stubs for each constituency
        self.stdout.write('\nCreating LiveResult stubs...')
        lr_created = 0
        for c in Constituency.objects.all():
            _, was_created = LiveResult.objects.get_or_create(
                constituency=c,
                defaults={
                    'status': 'NOT_STARTED',
                    'total_electors': 0,
                }
            )
            if was_created:
                lr_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nDone: {created} candidates seeded, {skipped} skipped\n'
            f'  LiveResult stubs: {lr_created} created\n'
            f'  Unknown constituencies: {sorted(unknown_consts)}'
        ))
