"""
Seed master data: districts, constituencies, and parties.
Reads constituency names from election_candidates.csv, district mapping from 2021.csv,
and parliament constituency from 2024_Parliment.csv.
Usage: python manage.py seed_master_data --data-dir ../data/
"""

import csv
import re
from django.core.management.base import BaseCommand
from core.models import District, Constituency, Party


# Kerala districts, north to south order
DISTRICT_ORDER = {
    'Kasaragod': 1,
    'Kannur': 2,
    'Wayanad': 3,
    'Kozhikode': 4,
    'Malappuram': 5,
    'Palakkad': 6,
    'Thrissur': 7,
    'Ernakulam': 8,
    'Idukki': 9,
    'Kottayam': 10,
    'Alappuzha': 11,
    'Pathanamthitta': 12,
    'Kollam': 13,
    'Thiruvananthapuram': 14,
}

# Major parties with alliance and colors — based on 2021 Kerala assembly alliance data
PARTIES = [
    # LDF (Left Democratic Front)
    ('CPI(M)',  'Communist Party of India (Marxist)',           'LDF', '#ED1E26'),
    ('CPI',     'Communist Party of India',                    'LDF', '#FF4444'),
    ('KEC(M)',  'Kerala Congress (M)',                         'LDF', '#8B4513'),
    ('JD(S)',   'Janata Dal (Secular)',                        'LDF', '#006400'),
    ('NCP',     'Nationalist Congress Party',                  'LDF', '#00BFFF'),
    ('NCP(M)',  'Nationalist Congress Party (M)',              'LDF', '#009FE3'),
    ('LJD',     'Loktantrik Janata Dal',                       'LDF', '#DAA520'),
    ('INL',     'Indian National League',                     'LDF', '#2E8B57'),
    ('CON(S)',  'Congress (S)',                                'LDF', '#87CEEB'),
    ('KEC(B)',  'Kerala Congress (B)',                         'LDF', '#A0522D'),
    ('JKC',     'Janadhipathya Kerala Congress',              'LDF', '#B8860B'),

    # UDF (United Democratic Front)
    ('INC',     'Indian National Congress',                    'UDF', '#19AAED'),
    ('IUML',    'Indian Union Muslim League',                  'UDF', '#0F8A3C'),
    ('KEC',     'Kerala Congress',                            'UDF', '#1E90FF'),
    ('RSP',     'Revolutionary Socialist Party',               'UDF', '#FF6347'),
    ('NCK',     'Nationalist Congress Kerala',                 'UDF', '#4682B4'),
    ('KEC(J)',  'Kerala Congress (Jacob)',                     'UDF', '#5F9EA0'),
    ('CMP',     'Congress (M) Party',                         'UDF', '#6495ED'),
    ('RMPI',    'Revolutionary Marxist Party of India',        'UDF', '#DC143C'),

    # NDA (National Democratic Alliance)
    ('BJP',     'Bharatiya Janata Party',                      'NDA', '#FF9933'),
    ('BDJS',    'Bharat Dharma Jana Sena',                     'NDA', '#FFD700'),
    ('AIADMK',  'All India Anna Dravida Munnetra Kazhagam',    'NDA', '#D4AC0D'),
    ('KKC',     'Kerala Kanavu Congress',                      'NDA', '#CD853F'),
    ('JRP',     'Jana Rashtriya Party',                        'NDA', '#B8860B'),

    # Others / Independents
    ('IND',     'Independent',                                'OTH', '#808080'),
    ('NOTA',    'None of the Above',                          'OTH', '#A9A9A9'),
    ('SDPI',    'Social Democratic Party of India',           'OTH', '#006400'),
    ('AAP',     'Aam Aadmi Party',                            'OTH', '#0066CC'),
    ('WPI',     'Welfare Party of India',                     'OTH', '#4B0082'),
    ('BSP',     'Bahujan Samaj Party',                        'OTH', '#00008B'),
    ('SUCI',    'Socialist Unity Centre of India',            'OTH', '#B22222'),
    ('SJD(S)',  'Social Justice (Democratic) Party',          'OTH', '#696969'),
]


class Command(BaseCommand):
    help = 'Seed districts, constituencies, and parties from CSV data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-dir',
            type=str,
            default='../data/',
            help='Path to data directory containing CSV files'
        )

    def handle(self, *args, **options):
        data_dir = options['data_dir']

        # 1. Create districts
        self.stdout.write("Creating 14 districts...")
        for name, order in DISTRICT_ORDER.items():
            district, created = District.objects.update_or_create(
                name=name,
                defaults={'order': order}
            )
            status = "CREATED" if created else "exists"
            self.stdout.write(f"  {status}: {name} (order: {order})")

        # 2. Build district mapping from 2021.csv (by constituency number)
        district_map = {}  # constituency_no -> district_name
        csv_2021 = f"{data_dir}/2021.csv"
        try:
            with open(csv_2021, 'r', encoding='utf-8-sig') as f:
                for row in csv.DictReader(f):
                    district_map[int(row['Number'])] = row['District']
            self.stdout.write(self.style.SUCCESS(
                f"\nLoaded district mapping for {len(district_map)} constituencies from 2021.csv"
            ))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(
                f"\n2021.csv not found at {csv_2021} - cannot map districts!"
            ))
            return

        # 3. Build parliament constituency mapping from 2024 parliament CSV
        parliament_map = {}  # AC number -> parliament constituency name
        parliament_csv = f"{data_dir}/2024_Parliment.csv"
        try:
            with open(parliament_csv, 'r', encoding='utf-8-sig') as f:
                for row in csv.DictReader(f):
                    ac_no = int(row['No.'])
                    pc_name = re.sub(r'\[\d+\]', '', row['Constituency']).strip()
                    parliament_map[ac_no] = pc_name
            self.stdout.write(self.style.SUCCESS(
                f"Loaded parliament constituency mapping for {len(parliament_map)} ACs"
            ))
        except FileNotFoundError:
            self.stdout.write(self.style.WARNING(
                f"Parliament CSV not found at {parliament_csv}, skipping parliament mapping"
            ))

        # 4. Create constituencies from election_candidates.csv (primary source)
        self.stdout.write("\nCreating 140 constituencies from election_candidates.csv...")
        candidates_csv = f"{data_dir}/election_candidates.csv"
        created_count = 0
        seen = set()

        try:
            with open(candidates_csv, 'r', encoding='utf-8-sig') as f:
                for row in csv.DictReader(f):
                    number = int(row['constituency_no'])
                    if number in seen:
                        continue
                    seen.add(number)

                    name = row['constituency_name']
                    district_name = district_map.get(number)
                    if not district_name:
                        self.stdout.write(self.style.WARNING(
                            f"  No district mapping for #{number} {name}, skipping"
                        ))
                        continue

                    district = District.objects.get(name=district_name)
                    pc_name = parliament_map.get(number, '')

                    constituency, created = Constituency.objects.update_or_create(
                        number=number,
                        defaults={
                            'name': name,
                            'district': district,
                            'parliament_constituency': pc_name,
                        }
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(
                            f"  + #{number} {name} ({district_name}) [PC: {pc_name}]"
                        ))

            self.stdout.write(self.style.SUCCESS(
                f"\n{created_count} constituencies created, "
                f"{len(seen) - created_count} already existed"
            ))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(
                f"election_candidates.csv not found at {candidates_csv}"
            ))
            return

        # 5. Create parties
        self.stdout.write("\nCreating parties...")
        party_created = 0
        for code, full_name, alliance, color in PARTIES:
            _, created = Party.objects.update_or_create(
                code=code,
                defaults={
                    'full_name': full_name,
                    'alliance': alliance,
                    'color_code': color,
                }
            )
            if created:
                party_created += 1

        self.stdout.write(self.style.SUCCESS(
            f"{party_created} parties created, {len(PARTIES) - party_created} already existed"
        ))

        # 6. Pick up any additional party codes from the candidates CSV
        extra_parties = set()
        try:
            with open(candidates_csv, 'r', encoding='utf-8-sig') as f:
                for row in csv.DictReader(f):
                    party_code = row['party']
                    if party_code not in ('NOTA',) and not Party.objects.filter(code=party_code).exists():
                        extra_parties.add(party_code)

            for code in sorted(extra_parties):
                Party.objects.update_or_create(
                    code=code,
                    defaults={
                        'full_name': code,
                        'alliance': 'OTH',
                        'color_code': '#808080',
                    }
                )

            if extra_parties:
                self.stdout.write(self.style.SUCCESS(
                    f"{len(extra_parties)} additional party codes from candidates CSV: {sorted(extra_parties)}"
                ))
        except FileNotFoundError:
            pass

        # Summary
        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*50}\n"
            f"SEED COMPLETE\n"
            f"  Districts:      {District.objects.count()}\n"
            f"  Constituencies: {Constituency.objects.count()}\n"
            f"  Parties:        {Party.objects.count()}\n"
            f"{'='*50}"
        ))
