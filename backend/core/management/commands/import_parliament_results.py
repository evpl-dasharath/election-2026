"""
Import Parliament election results (2019/2024) at AC level from CSV
Usage: python manage.py import_parliament_results 2024 /path/to/2024_Parliment.csv
"""

import csv
from django.core.management.base import BaseCommand
from core.models import Constituency, ParliamentResult


class Command(BaseCommand):
    help = 'Import Parliament election results at AC level from CSV'

    def add_arguments(self, parser):
        parser.add_argument('year', type=int, choices=[2019, 2024], help='Election year')
        parser.add_argument('csv_file', type=str, help='Path to Parliament CSV file')

    def handle(self, *args, **options):
        year = options['year']
        csv_file = options['csv_file']
        
        imported = 0
        skipped = 0
        
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Match by constituency number (reliable across CSVs)
                ac_number = int(row['No.'])
                ls_constituency = row['Constituency']
                
                try:
                    constituency = Constituency.objects.get(number=ac_number)
                except Constituency.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f"Constituency #{ac_number} not found, skipping"
                    ))
                    skipped += 1
                    continue
                
                # Clean vote strings (remove commas)
                udf_votes = int(row['UDF'].replace(',', ''))
                ldf_votes = int(row['LDF'].replace(',', ''))
                nda_votes = int(row['NDA'].replace(',', ''))
                
                # Determine lead and margin
                lead_alliance = row['Lead'].strip()
                runnerup_alliance = row['Runner-up'].strip()
                margin = int(row['Margin'].replace(',', ''))
                
                # Fix corrupted alliance codes by computing from votes
                valid_alliances = {'UDF', 'LDF', 'NDA'}
                if lead_alliance not in valid_alliances:
                    votes = {'UDF': udf_votes, 'LDF': ldf_votes, 'NDA': nda_votes}
                    sorted_v = sorted(votes.items(), key=lambda x: -x[1])
                    lead_alliance = sorted_v[0][0]
                    runnerup_alliance = sorted_v[1][0]
                
                if runnerup_alliance not in valid_alliances:
                    votes = {'UDF': udf_votes, 'LDF': ldf_votes, 'NDA': nda_votes}
                    sorted_v = sorted(votes.items(), key=lambda x: -x[1])
                    runnerup_alliance = sorted_v[1][0]
                
                import re
                # Clean footnote markers like [30] from constituency name
                ls_constituency_clean = re.sub(r'\[\d+\]', '', ls_constituency).strip()
                
                result, created = ParliamentResult.objects.update_or_create(
                    year=year,
                    constituency=constituency,
                    defaults={
                        'parliament_constituency': ls_constituency_clean,
                        'udf_votes': udf_votes,
                        'ldf_votes': ldf_votes,
                        'nda_votes': nda_votes,
                        'lead_alliance': lead_alliance,
                        'runnerup_alliance': runnerup_alliance,
                        'margin': margin,
                    }
                )
                
                imported += 1
                action = "Created" if created else "Updated"
                # ASCII-safe output for Windows console
                safe_name = constituency.name.encode('ascii', 'replace').decode()
                safe_ls = ls_constituency_clean.encode('ascii', 'replace').decode()
                safe_lead = lead_alliance.encode('ascii', 'replace').decode()
                self.stdout.write(self.style.SUCCESS(
                    f"{action}: {year} - {safe_name} ({safe_ls}) - {safe_lead} leads"
                ))
        
        self.stdout.write(self.style.SUCCESS(
            f"\nImport complete: {imported} imported, {skipped} skipped"
        ))
