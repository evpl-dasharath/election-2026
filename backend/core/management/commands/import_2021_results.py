"""
Import 2021 LA election results from CSV (complete candidate-level data)
Usage: python manage.py import_2021_results /path/to/election_candidates.csv
"""

import csv
from django.core.management.base import BaseCommand
from core.models import Constituency, HistoricalResult2021, ConstituencyMeta2021


class Command(BaseCommand):
    help = 'Import 2021 LA election results from CSV (complete candidate data)'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to election_candidates.csv file')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        
        # Clear existing data
        HistoricalResult2021.objects.all().delete()
        ConstituencyMeta2021.objects.all().delete()
        
        imported = 0
        skipped = 0
        current_constituency = None
        constituency_meta = {}
        
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                constituency_no = int(row['constituency_no'])
                
                # Get constituency
                try:
                    constituency = Constituency.objects.get(number=constituency_no)
                except Constituency.DoesNotExist:
                    if constituency_no != current_constituency:
                        self.stdout.write(self.style.WARNING(
                            f"Constituency {constituency_no} not found, skipping"
                        ))
                    current_constituency = constituency_no
                    skipped += 1
                    continue
                
                # Store constituency metadata (only once per constituency)
                if constituency_no not in constituency_meta:
                    constituency_meta[constituency_no] = {
                        'constituency': constituency,
                        'total_electors': int(row['total_electors'])
                    }
                
                # Skip NOTA rows (we'll handle them separately if needed)
                if row['party'] == 'NOTA':
                    continue
                
                # Parse candidate data
                serial_no = int(row['serial_no']) if row['serial_no'] else None
                age = int(row['age']) if row['age'] else None
                is_winner = row['winner'].strip().upper() == 'TRUE'
                
                # Create candidate record
                result = HistoricalResult2021.objects.create(
                    constituency=constituency,
                    serial_no=serial_no,
                    candidate_name=row['candidate_name'],
                    sex=row['sex'],
                    age=age,
                    category=row['category'],
                    party_code=row['party'],
                    party_symbol=row['symbol'],
                    general_votes=int(row['general_votes']),
                    postal_votes=int(row['postal_votes']),
                    total_votes=int(row['total_votes']),
                    vote_percentage=float(row['vote_pct']),
                    is_winner=is_winner
                )
                
                imported += 1
                if is_winner:
                    self.stdout.write(self.style.SUCCESS(
                        f"[WIN] {constituency.name} - {result.candidate_name} ({result.party_code})"
                    ))
        
        # Create constituency metadata records
        for const_no, meta in constituency_meta.items():
            # Get winner and calculate margin
            results = HistoricalResult2021.objects.filter(
                constituency=meta['constituency']
            ).order_by('-total_votes')[:2]
            
            if results.count() >= 2:
                winner = results[0]
                margin = results[0].total_votes - results[1].total_votes
                
                ConstituencyMeta2021.objects.create(
                    constituency=meta['constituency'],
                    total_electors=meta['total_electors'],
                    winner_name=winner.candidate_name,
                    winner_party=winner.party_code,
                    margin=margin
                )
        
        self.stdout.write(self.style.SUCCESS(
            f"\nImport complete:"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  - {imported} candidate records imported"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  - {len(constituency_meta)} constituency metadata records created"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  - {skipped} rows skipped"
        ))

