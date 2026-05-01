"""
Seed PartyAllianceYear table with election-year-specific alliance data.

This is the single source of truth for which party belonged to which alliance
in a given election. It also normalises party code variants/aliases that appear
in source CSVs (e.g. RMPOI -> UDF, same as RMPI).

Usage:
    python manage.py seed_party_alliances
    python manage.py seed_party_alliances --clear   # wipe and re-seed
"""

from django.core.management.base import BaseCommand
from core.models import PartyAllianceYear


# ---------------------------------------------------------------------------
# 2021 Kerala Legislative Assembly election
# Source: Wikipedia / ECI official alliance declarations
# Format: (party_code_in_csv, canonical_code, alliance, color_hex)
# If canonical_code == party_code_in_csv just put ''
# ---------------------------------------------------------------------------
LA_2021 = [
    # LDF -------------------------------------------------------------------
    ('CPI(M)',   '',        'LDF', '#ED1E26'),   # Communist Party of India (Marxist)
    ('CPIM',    'CPI(M)',  'LDF', '#ED1E26'),   # CPI(M) without parens - CSV alias
    ('CPI',      '',        'LDF', '#FF4444'),   # Communist Party of India
    ('KEC(M)',   '',        'LDF', '#8B4513'),   # Kerala Congress (M) - Jose K. Mani faction
    ('KC(M)',   'KEC(M)',  'LDF', '#8B4513'),   # alias used in some CSVs
    ('JD(S)',    '',        'LDF', '#006400'),   # Janata Dal (Secular) - LDF faction
    ('NCP',      '',        'LDF', '#00BFFF'),   # Nationalist Congress Party
    ('NCP(M)',  'NCP',     'LDF', '#00BFFF'),   # alias
    ('LJD',      '',        'LDF', '#DAA520'),   # Loktantrik Janata Dal
    ('INL',      '',        'LDF', '#2E8B57'),   # Indian National League
    ('CON(S)',   '',        'LDF', '#87CEEB'),   # Congress (S)
    ('CONG(S)', 'CON(S)',  'LDF', '#87CEEB'),   # alias
    ('C(S)',    'CON(S)',  'LDF', '#87CEEB'),   # short-form alias in 2021 CSV
    ('KEC(B)',   '',        'LDF', '#A0522D'),   # Kerala Congress (B) - R. Balakrishna Pillai
    ('KC(B)',   'KEC(B)',  'LDF', '#A0522D'),   # alias
    ('JKC',      '',        'LDF', '#B8860B'),   # Janadhipathya Kerala Congress

    # UDF -------------------------------------------------------------------
    ('INC',      '',        'UDF', '#19AAED'),   # Indian National Congress
    ('IUML',     '',        'UDF', '#0F8A3C'),   # Indian Union Muslim League
    ('KEC',      '',        'UDF', '#1E90FF'),   # Kerala Congress (P. J. Joseph)
    ('KC',      'KEC',     'UDF', '#1E90FF'),   # alias
    ('RSP',      '',        'UDF', '#FF6347'),   # Revolutionary Socialist Party - A. A. Aziz faction
    ('NCK',      '',        'UDF', '#4682B4'),   # Nationalist Congress Kerala (Mani C. Kappan)
    ('KEC(J)',   '',        'UDF', '#5F9EA0'),   # Kerala Congress (Jacob)
    ('KC(J)',   'KEC(J)',  'UDF', '#5F9EA0'),   # alias
    ('CMP',      '',        'UDF', '#6495ED'),   # Congress (M) Party - C. P. John
    ('RMPI',     '',        'UDF', '#DC143C'),   # Revolutionary Marxist Party of India - N. Venu
    ('RMPOI',  'RMPI',    'UDF', '#DC143C'),   # typo/variant in 2021 CSV (e.g. K.K.REMA, Vadakara)
    ('RMP',    'RMPI',    'UDF', '#DC143C'),   # shorter alias

    # NDA -------------------------------------------------------------------
    ('BJP',      '',        'NDA', '#FF9933'),   # Bharatiya Janata Party
    ('BDJS',     '',        'NDA', '#FFD700'),   # Bharat Dharma Jana Sena
    ('AIADMK',   '',        'NDA', '#D4AC0D'),   # All India Anna Dravida Munnetra Kazhagam
    ('ADMK',   'AIADMK',  'NDA', '#D4AC0D'),   # ADMK short alias in 2021 CSV
    ('KKC',      '',        'NDA', '#CD853F'),   # Kerala Kanavu Congress
    ('JRP',      '',        'NDA', '#B8860B'),   # Jana Rashtriya Party - C. K. Janu
    ('AITC',     '',        'NDA', '#1B8A00'),   # All India Trinamool Congress (contested under NDA)
    ('JD(U)',    '',        'NDA', '#008000'),   # Janata Dal (United) - NDA ally
    ('SHS',      '',        'NDA', '#FF6600'),   # Shiv Sena - NDA ally

    # OTH -------------------------------------------------------------------
    ('IND',      '',        'OTH', '#808080'),
    ('SDPI',     '',        'OTH', '#4B0082'),
    ('WPI',      '',        'OTH', '#800080'),
    ('WPOI',   'WPI',     'OTH', '#800080'),   # WPI alias in 2021 CSV
    ('BSP',      '',        'OTH', '#00008B'),
    ('SUCI',     '',        'OTH', '#B22222'),
    ('AAP',      '',        'OTH', '#0066CC'),
    ('NOTA',     '',        'OTH', '#A9A9A9'),
    ('RJD',      '',        'OTH', '#336699'),   # Rashtriya Janata Dal - no Kerala front
    # Small fringe / unrecognised parties in 2021 CSV - all OTH
    ('ABHM',     '',        'OTH', '#808080'),
    ('ADHRMPI',  '',        'OTH', '#808080'),
    ('BHUDRP',   '',        'OTH', '#808080'),
    ('CMPKSC',   '',        'OTH', '#808080'),
    ('DHRMP',    '',        'OTH', '#808080'),
    ('DSJP',     '',        'OTH', '#808080'),
    ('ICSP',     '',        'OTH', '#808080'),
    ('KJPS',     '',        'OTH', '#808080'),
    ('KLJP',     '',        'OTH', '#808080'),
    ('MCPI',     '',        'OTH', '#808080'),
    ('NALAP',    '',        'OTH', '#808080'),
    ('NSC',      '',        'OTH', '#808080'),
    ('NWLBRP',   '',        'OTH', '#808080'),
    ('RPI(A)',   '',        'OTH', '#808080'),
    ('SDC',      '',        'OTH', '#808080'),
    ('SMFB',     '',        'OTH', '#808080'),
    ('SWARAJ',   '',        'OTH', '#808080'),
    ('SWJP',     '',        'OTH', '#808080'),
]


# ---------------------------------------------------------------------------
# 2016 Kerala Legislative Assembly election
# ---------------------------------------------------------------------------
LA_2016 = [
    # LDF -------------------------------------------------------------------
    ('CPI(M)',   '',        'LDF', '#ED1E26'),
    ('CPI',      '',        'LDF', '#FF4444'),
    ('NCP',      '',        'LDF', '#00BFFF'),
    ('JD(S)',    '',        'LDF', '#006400'),   # JD(S) was LDF in 2016 too
    ('KEC(B)',   '',        'LDF', '#A0522D'),
    ('KC(B)',   'KEC(B)',  'LDF', '#A0522D'),
    ('INL',      '',        'LDF', '#2E8B57'),
    ('CON(S)',   '',        'LDF', '#87CEEB'),
    ('CONG(S)', 'CON(S)',  'LDF', '#87CEEB'),
    ('JKC',      '',        'LDF', '#B8860B'),
    ('RSP(B)',   '',        'LDF', '#FF8C00'),   # RSP (Bolshevik) was LDF in 2016

    # UDF -------------------------------------------------------------------
    ('INC',      '',        'UDF', '#19AAED'),
    ('IUML',     '',        'UDF', '#0F8A3C'),
    ('KEC',      '',        'UDF', '#1E90FF'),
    ('KC',      'KEC',     'UDF', '#1E90FF'),
    ('RSP',      '',        'UDF', '#FF6347'),
    ('RMPI',     '',        'UDF', '#DC143C'),
    ('RMPOI',  'RMPI',    'UDF', '#DC143C'),
    ('RMP',    'RMPI',    'UDF', '#DC143C'),
    ('KC(M)',   'KEC(M)',  'UDF', '#1E90FF'),   # KEC(M) was UDF in 2016
    ('KEC(M)',   '',        'UDF', '#1E90FF'),
    ('KEC(J)',   '',        'UDF', '#5F9EA0'),
    ('KC(J)',   'KEC(J)',  'UDF', '#5F9EA0'),
    ('CMP',      '',        'UDF', '#6495ED'),

    # NDA -------------------------------------------------------------------
    ('BJP',      '',        'NDA', '#FF9933'),
    ('BDJS',     '',        'NDA', '#FFD700'),

    # OTH -------------------------------------------------------------------
    ('IND',      '',        'OTH', '#808080'),
    ('SDPI',     '',        'OTH', '#4B0082'),
    ('NOTA',     '',        'OTH', '#A9A9A9'),
]


DATASETS = {
    (2021, 'LA'): LA_2021,
    (2016, 'LA'): LA_2016,
}


class Command(BaseCommand):
    help = 'Seed PartyAllianceYear table with election-year-specific alliance data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all existing PartyAllianceYear records before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            count = PartyAllianceYear.objects.count()
            PartyAllianceYear.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing records'))

        total_created = 0
        total_updated = 0

        for (year, etype), entries in DATASETS.items():
            self.stdout.write(f'\nSeeding {year} {etype} ({len(entries)} entries)...')
            created = updated = 0
            for party_code, canonical, alliance, color in entries:
                _, was_created = PartyAllianceYear.objects.update_or_create(
                    party_code=party_code,
                    election_year=year,
                    election_type=etype,
                    defaults={
                        'canonical_code': canonical,
                        'alliance': alliance,
                        'color_code': color,
                    }
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            self.stdout.write(
                self.style.SUCCESS(f'  {created} created, {updated} updated')
            )
            total_created += created
            total_updated += updated

        self.stdout.write(self.style.SUCCESS(
            f'\nDone -- {total_created} created, {total_updated} updated across all elections'
        ))
