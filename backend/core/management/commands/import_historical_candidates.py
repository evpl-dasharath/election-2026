"""
Import historical LA election results (2006 or 2011) from CSV.

CSV columns (same format as 2021):
    constituency_no, constituency_name, total_electors, serial_no,
    candidate_name, sex, age, category, party, symbol,
    general_votes, postal_votes, total_votes, vote_pct, winner

Usage:
    python manage.py import_historical_candidates 2006 ../../data/2006_candidates.csv
    python manage.py import_historical_candidates 2011 ../../data/2011_candidates.csv
    python manage.py import_historical_candidates 2006 ../../data/2006_candidates.csv --clear
"""

import csv
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Constituency, HistoricalResult2006, HistoricalResult2011

YEAR_MODEL_MAP = {
    2006: HistoricalResult2006,
    2011: HistoricalResult2011,
}


class Command(BaseCommand):
    help = 'Import 2006 or 2011 LA election results from a candidate-level CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            'year', type=int, choices=[2006, 2011],
            help='Election year to import (2006 or 2011)'
        )
        parser.add_argument(
            'csv_file', type=str,
            help='Path to the candidates CSV file'
        )
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete all existing records for this year before importing'
        )

    def handle(self, *args, **options):
        year = options['year']
        csv_path = options['csv_file']
        Model = YEAR_MODEL_MAP[year]

        if options['clear']:
            deleted, _ = Model.objects.all().delete()
            self.stdout.write(self.style.WARNING(
                f'Cleared {deleted} existing {year} result records.'
            ))

        # Build constituency lookup by number
        constituencies = {c.number: c for c in Constituency.objects.all()}

        imported = 0
        skipped = 0
        warned_constituencies = set()

        try:
            f = open(csv_path, encoding='utf-8-sig')
        except FileNotFoundError:
            raise CommandError(f'File not found: {csv_path}')

        with f, transaction.atomic():
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):  # start=2 accounts for header
                # --- constituency ---
                raw_no = row.get('constituency_no', '').strip()
                if not raw_no:
                    skipped += 1
                    continue
                try:
                    const_no = int(raw_no)
                except ValueError:
                    skipped += 1
                    continue

                constituency = constituencies.get(const_no)
                if not constituency:
                    if const_no not in warned_constituencies:
                        self.stdout.write(self.style.WARNING(
                            f'  Row {row_num}: Constituency #{const_no} not found in DB — skipping all rows for it'
                        ))
                        warned_constituencies.add(const_no)
                    skipped += 1
                    continue

                # --- party ---
                party_code = row.get('party', '').strip() or 'IND'
                if party_code == 'NOTA':
                    skipped += 1
                    continue

                # --- numeric fields ---
                def safe_int(val, default=0):
                    try:
                        return int(str(val).strip()) if str(val).strip() else default
                    except (ValueError, TypeError):
                        return default

                def safe_float(val, default=0.0):
                    try:
                        return float(str(val).strip()) if str(val).strip() else default
                    except (ValueError, TypeError):
                        return default

                serial_no = safe_int(row.get('serial_no'), None)
                age = safe_int(row.get('age'), None)
                general_votes = safe_int(row.get('general_votes'))
                postal_votes = safe_int(row.get('postal_votes'))
                total_votes = safe_int(row.get('total_votes'))
                vote_pct = safe_float(row.get('vote_pct'))
                total_electors = safe_int(row.get('total_electors'))

                is_winner_raw = row.get('winner', '').strip().upper()
                is_winner = is_winner_raw == 'TRUE'

                Model.objects.create(
                    constituency=constituency,
                    serial_no=serial_no if serial_no is not None else None,
                    candidate_name=row.get('candidate_name', '').strip(),
                    sex=row.get('sex', '').strip(),
                    age=age if age is not None else None,
                    category=row.get('category', '').strip(),
                    party_code=party_code,
                    party_symbol=row.get('symbol', '').strip(),
                    general_votes=general_votes,
                    postal_votes=postal_votes,
                    total_votes=total_votes,
                    vote_percentage=vote_pct,
                    total_electors=total_electors,
                    is_winner=is_winner,
                )
                imported += 1

                if is_winner:
                    self.stdout.write(self.style.SUCCESS(
                        f'  [WIN] {constituency.name} — '
                        f'{row.get("candidate_name", "").strip()} ({party_code})'
                    ))

        self.stdout.write('\n' + '-' * 50)
        self.stdout.write(self.style.SUCCESS(
            f'{year} import complete!'
        ))
        self.stdout.write(f'  Records imported : {imported}')
        self.stdout.write(f'  Rows skipped     : {skipped}')
