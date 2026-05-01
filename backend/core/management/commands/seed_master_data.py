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

# Major parties with alliance and colors — based on 2026 Kerala assembly alliance data
PARTIES = [
    # LDF (Left Democratic Front) ──────────────────────────────────────────
    ('CPI(M)',  'Communist Party of India (Marxist)',           'LDF', '#ED1E26'),
    ('CPIM',   'CPI(M)',                                       'LDF', '#ED1E26'),
    ('CPI',    'Communist Party of India',                     'LDF', '#FF4444'),
    ('KC(M)',  'Kerala Congress (M)',                          'LDF', '#8B4513'),
    ('KEC(M)', 'Kerala Congress (M)',                          'LDF', '#8B4513'),
    ('NCP(SP)','Nationalist Congress Party – Sharadchandra Pawar', 'LDF', '#00BFFF'),
    ('RJD',    'Rashtriya Janata Dal',                         'LDF', '#336699'),
    ('JD(S)-LDF','Indian Socialist Janata Dal',                'LDF', '#006400'),
    ('INL',    'Indian National League',                       'LDF', '#2E8B57'),
    ('CON(S)', 'Congress (Secular)',                           'LDF', '#87CEEB'),
    ('KEC(B)', 'Kerala Congress (B)',                          'LDF', '#A0522D'),
    ('KC(B)',  'Kerala Congress (B)',                          'LDF', '#A0522D'),
    ('JKC',    'Janadhipathya Kerala Congress',                'LDF', '#B8860B'),
    ('NCP',    'Nationalist Congress Party',                   'LDF', '#00BFFF'),
    ('LJD',    'Loktantrik Janata Dal',                        'LDF', '#5C6BC0'),
    ('RSP(L)', 'Revolutionary Socialist Party (Leninist)',     'LDF', '#B22222'),

    # UDF (United Democratic Front) ────────────────────────────────────────
    ('INC',    'Indian National Congress',                     'UDF', '#19AAED'),
    ('IUML',   'Indian Union Muslim League',                   'UDF', '#0F8A3C'),
    ('KEC',    'Kerala Congress',                              'UDF', '#1E90FF'),
    ('RSP',    'Revolutionary Socialist Party',                'UDF', '#FF6347'),
    ('NCK',    'Nationalist Congress Kerala',                  'UDF', '#4682B4'),
    ('KC(J)',  'Kerala Congress (Jacob)',                      'UDF', '#5F9EA0'),
    ('KEC(J)', 'Kerala Congress (Jacob)',                      'UDF', '#5F9EA0'),
    ('CMP',    'Communist Marxist Party',                      'UDF', '#6495ED'),
    ('RMPI',   'Revolutionary Marxist Party of India',         'UDF', '#DC143C'),
    ('AITC',   'All India Trinamool Congress',                 'UDF', '#1B8A00'),

    # NDA (National Democratic Alliance) ───────────────────────────────────
    ('BJP',    'Bharatiya Janata Party',                       'NDA', '#FF9933'),
    ('BDJS',   'Bharat Dharma Jana Sena',                      'NDA', '#FFD700'),
    ('TTP',    'Twenty20 Party',                               'NDA', '#FF4500'),
    ('KC(T)',  'Kerala Congress (Thomas)',                      'NDA', '#CD853F'),
    ('AIADMK', 'All India Anna Dravida Munnetra Kazhagam',     'NDA', '#D4AC0D'),
    ('KKC',    'Kerala Kanavu Congress',                       'NDA', '#CD853F'),
    ('JRP',    'Janadhipathya Rashtriya Party',                'NDA', '#37474F'),

    # OTH — with meaningful colors ─────────────────────────────────────────
    ('IND',    'Independent',                                  'OTH', '#6B7280'),
    ('NOTA',   'None of the Above',                            'OTH', '#9CA3AF'),
    ('SDPI',   'Social Democratic Party of India',             'OTH', '#1B5E20'),
    ('AAP',    'Aam Aadmi Party',                              'OTH', '#0066CC'),
    ('WPI',    'Welfare Party of India',                       'OTH', '#4A148C'),
    ('BSP',    'Bahujan Samaj Party',                          'OTH', '#1565C0'),
    ('SUCI',   'Socialist Unity Centre of India',              'OTH', '#B71C1C'),
    ('CPIML Liberation','CPI(ML) Liberation',                  'OTH', '#CC0000'),
    ('CPIML Red Star','CPI(ML) Red Star',                      'OTH', '#D50000'),
    ('SHS',    'Shiv Sena',                                    'OTH', '#F57F17'),
    ('ADMK',   'AIADMK',                                       'OTH', '#D4AC0D'),
    ('JD(U)',  'Janata Dal (United)',                           'OTH', '#1A6B1A'),
    ('SP (I)', 'Samajwadi Party (India)',                       'OTH', '#E53935'),
    ('CMPKSC', 'Communist Marxist Party (C.P.John)',            'OTH', '#6A1B9A'),
    ('API',    'Ambedkarite Party of India',                   'OTH', '#37474F'),
    ('RPI(A)', 'Republican Party of India (Athawale)',          'OTH', '#0288D1'),
    ('MCPI',   'Marxist Communist Party of India',             'OTH', '#880E4F'),
    ('NSC',    'National Secular Congress',                    'OTH', '#2E7D32'),
    ('WPOI',   'Welfare Party of India (alias)',               'OTH', '#6A1B9A'),
    ('RMPOI',  'RMP alias',                                    'OTH', '#C62828'),
    ('SJD',    'Social Justice Party',                         'OTH', '#424242'),
    ('ABHM',   'ABHM',                                         'OTH', '#4527A0'),
    ('ADHRMPI','ADHRMPI',                                      'OTH', '#558B2F'),
    ('AIHCP',  'AIHCP',                                        'OTH', '#00838F'),
    ('Anna DHRM','Anna DHRM',                                  'OTH', '#6D4C41'),
    ('BDP',    'Bahujan Dravida Party',                        'OTH', '#0277BD'),
    ('BHUDRP', 'BHUDRP',                                       'OTH', '#827717'),
    ('BJKP',   'Bharatheeya Jawan Kisan Party',                'OTH', '#FF6F00'),
    ('DHRMP',  'Democratic Human Rights Movement Party',       'OTH', '#283593'),
    ('DSJP',   'DSJP',                                         'OTH', '#1B5E20'),
    ('EPI',    'Equality Party of India',                      'OTH', '#880E4F'),
    ('ICSP',   'ICSP',                                         'OTH', '#4E342E'),
    ('IGP',    'Indian Gandhiyan Party',                       'OTH', '#BF360C'),
    ('KJPS',   'KJPS',                                         'OTH', '#006064'),
    ('KLJP',   'KLJP',                                         'OTH', '#1A237E'),
    ('NALAP',  'NALAP',                                        'OTH', '#3E2723'),
    ('NWLBRP', 'NWLBRP',                                       'OTH', '#78909C'),
    ('RJP',    'Rashtravadi Janata Party',                     'OTH', '#B71C1C'),
    ('SDC',    'SDC',                                          'OTH', '#004D40'),
    ('SMFB',   'SMFB',                                         'OTH', '#4A148C'),
    ('SRP',    'Socialist Republican Party (Kerala)',           'OTH', '#E65100'),
    ('SWARAJ', 'SWARAJ',                                       'OTH', '#0D47A1'),
    ('SWJP',   'SWJP',                                         'OTH', '#1B5E20'),
    ('TFIP',   'The Future India Party',                       'OTH', '#880E4F'),
    ('AIHCP',  'AIHCP',                                        'OTH', '#00838F'),
    ('RJP',    'Rashtravadi Janata Party',                     'OTH', '#B71C1C'),
    ('EPI',    'Equality Party of India',                      'OTH', '#880E4F'),
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
