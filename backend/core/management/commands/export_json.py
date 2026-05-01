"""
Export election data to optimized JSON files for Firebase hosting
Usage: python manage.py export_json --output /path/to/frontend/src/data/
"""

import json
import os
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db.models import Sum, Count, Q
from core.models import (
    District, Constituency, Party, Candidate, LiveResult,
    HistoricalResult2021, ConstituencyMeta2021, ParliamentResult, DataSnapshot
)


class Command(BaseCommand):
    help = 'Export election data to JSON files for static hosting'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='./frontend/public/data/',
            help='Output directory for JSON files'
        )

    def handle(self, *args, **options):
        output_dir = options['output']
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'results'), exist_ok=True)
        
        timestamp = timezone.now().isoformat()
        
        # 1. META.JSON - State-level summary
        self.stdout.write("Exporting meta.json...")
        meta_data = self.export_meta(timestamp)
        with open(os.path.join(output_dir, 'meta.json'), 'w') as f:
            json.dump(meta_data, f, indent=2)
        
        # 2. CONSTITUENCIES.JSON - List of all constituencies
        self.stdout.write("Exporting constituencies.json...")
        constituencies_data = self.export_constituencies()
        with open(os.path.join(output_dir, 'constituencies.json'), 'w') as f:
            json.dump(constituencies_data, f, indent=2)
        
        # 3. RESULTS/{ID}.JSON - Individual constituency details
        self.stdout.write("Exporting individual constituency results...")
        count = self.export_individual_results(output_dir)
        
        # 4. HISTORICAL.JSON - 2021 LA + 2019/2024 LS comparison
        self.stdout.write("Exporting historical.json...")
        historical_data = self.export_historical()
        with open(os.path.join(output_dir, 'historical.json'), 'w') as f:
            json.dump(historical_data, f, indent=2)
        
        # 5. PARTIES.JSON - Party master data
        self.stdout.write("Exporting parties.json...")
        parties_data = self.export_parties()
        with open(os.path.join(output_dir, 'parties.json'), 'w') as f:
            json.dump(parties_data, f, indent=2)
        
        # Update snapshots
        DataSnapshot.objects.update_or_create(
            snapshot_type='all',
            defaults={
                'last_exported': timezone.now(),
                'file_path': output_dir,
                'record_count': count
            }
        )
        
        self.stdout.write(self.style.SUCCESS(
            f"\n[OK] Export complete:"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  - meta.json: state summary"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  - constituencies.json: {len(constituencies_data)} constituencies"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  - results/*.json: {count} individual constituency files"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  - historical.json: 2021 LA + 2019/2024 LS data"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  - parties.json: party master data"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  - Output: {output_dir}"
        ))

    def export_meta(self, timestamp):
        """State-level summary with live aggregates"""
        live_results = LiveResult.objects.all()
        candidates = Candidate.objects.all()
        
        # Count seats by alliance
        alliance_seats = {
            'UDF': {'won': 0, 'leading': 0, 'trailing': 0},
            'LDF': {'won': 0, 'leading': 0, 'trailing': 0},
            'NDA': {'won': 0, 'leading': 0, 'trailing': 0},
            'OTH': {'won': 0, 'leading': 0, 'trailing': 0},
        }
        
        for constituency in Constituency.objects.all():
            top_candidates = constituency.candidates_2026.order_by('-votes')[:2]
            if top_candidates:
                leader = top_candidates[0]
                alliance = leader.party.alliance
                
                result = LiveResult.objects.filter(constituency=constituency).first()
                if result and result.status == 'RESULT_DECLARED':
                    alliance_seats[alliance]['won'] += 1
                elif result and result.status == 'IN_PROGRESS' and leader.votes > 0:
                    alliance_seats[alliance]['leading'] += 1
        
        return {
            'timestamp': timestamp,
            'total_constituencies': 140,
            'results_declared': live_results.filter(status='RESULT_DECLARED').count(),
            'counting_in_progress': live_results.filter(status='IN_PROGRESS').count(),
            'alliance_summary': alliance_seats,
            'total_votes_counted': candidates.aggregate(Sum('votes'))['votes__sum'] or 0,
        }

    # District → region mapping (mirrors frontend DISTRICT_REGION constant)
    DISTRICT_REGION = {
        'Kasaragod': 'north', 'Kannur': 'north', 'Wayanad': 'north', 'Kozhikode': 'north',
        'Malappuram': 'central_north', 'Palakkad': 'central_north', 'Thrissur': 'central_north',
        'Ernakulam': 'south_central', 'Idukki': 'south_central',
        'Kottayam': 'south_central', 'Alappuzha': 'south_central',
        'Pathanamthitta': 'south', 'Kollam': 'south', 'Thiruvananthapuram': 'south',
    }

    def export_constituencies(self):
        """List of all constituencies with basic info and current status"""
        constituencies = []
        
        for const in Constituency.objects.select_related('district').all():
            # Get top 2 candidates by votes
            top2 = list(const.candidates_2026.order_by('-votes')[:2])
            leader = top2[0] if top2 else None
            runner_up = top2[1] if len(top2) > 1 else None
            live = LiveResult.objects.filter(constituency=const).first()
            district_name = const.district.name
            
            constituencies.append({
                'id': const.id,
                'number': const.number,
                'name': const.name,
                'district': district_name,
                'region': self.DISTRICT_REGION.get(district_name, 'south'),
                'reserved': const.get_reserved_category_display(),
                'status': live.status if live else 'NOT_STARTED',
                'leader': {
                    'name': leader.name,
                    'party': leader.party.code,
                    'alliance': leader.party.alliance,
                    'votes': leader.votes,
                    'percentage': float(leader.vote_percentage),
                } if leader else None,
                'runner_up': {
                    'name': runner_up.name,
                    'party': runner_up.party.code,
                    'alliance': runner_up.party.alliance,
                    'votes': runner_up.votes,
                    'percentage': float(runner_up.vote_percentage),
                } if runner_up else None,
            })
        
        return constituencies


    def export_individual_results(self, output_dir):
        """Export detailed results for each constituency"""
        count = 0
        results_dir = os.path.join(output_dir, 'results')
        
        for const in Constituency.objects.all():
            # Live result metadata (fetched first — needed for is_leading computation)
            live = LiveResult.objects.filter(constituency=const).first()

            # Current 2026 results
            candidates = []
            for idx, cand in enumerate(const.candidates_2026.order_by('-votes')):
                candidates.append({
                    'name': cand.name,
                    'party': cand.party.code,
                    'alliance': cand.party.alliance,
                    'votes': cand.votes,
                    'percentage': float(cand.vote_percentage),
                    'is_winner': cand.is_winner,
                    # is_leading is dynamic: whoever has most votes while IN_PROGRESS
                    'is_leading': (
                        idx == 0
                        and cand.votes > 0
                        and not cand.is_winner
                        and (live.status == 'IN_PROGRESS' if live else False)
                    ),
                })

            
            # 2021 results for this constituency
            results_2021 = []
            for res in const.results_2021.all()[:5]:  # Top 5 candidates
                results_2021.append({
                    'candidate': res.candidate_name,
                    'party': res.party_code,
                    'votes': res.total_votes,
                    'percentage': float(res.vote_percentage),
                    'is_winner': res.is_winner,
                })
            
            data = {
                'constituency': {
                    'id': const.id,
                    'number': const.number,
                    'name': const.name,
                    'district': const.district.name,
                },
                'live_result': {
                    'status': live.status if live else 'NOT_STARTED',
                    'total_electors': live.total_electors if live else 0,
                    'votes_polled': live.votes_polled if live else 0,
                    'votes_counted': live.votes_counted if live else 0,
                    'valid_votes': live.valid_votes if live else 0,
                    'rounds_completed': live.rounds_completed if live else 0,
                    'total_rounds': live.total_rounds if live else 0,
                    'last_updated': live.last_updated.isoformat() if live else None,
                } if live else None,
                'candidates_2026': candidates,
                'results_2021': results_2021,
            }
            
            filename = f"{const.number:03d}.json"
            with open(os.path.join(results_dir, filename), 'w') as f:
                json.dump(data, f, indent=2)
            
            count += 1
        
        return count

    def export_historical(self):
        """Export historical comparison data (2021 LA + 2019/2024 LS)"""
        historical = {}
        
        for const in Constituency.objects.all():
            # 2021 LA results
            results_2021 = const.results_2021.order_by('-total_votes')[:5]
            meta_2021 = ConstituencyMeta2021.objects.filter(constituency=const).first()
            
            # 2019 LS results
            ls_2019 = ParliamentResult.objects.filter(year=2019, constituency=const).first()
            
            # 2024 LS results
            ls_2024 = ParliamentResult.objects.filter(year=2024, constituency=const).first()
            
            historical[str(const.number)] = {
                'constituency': const.name,
                'la_2021': {
                    'winner': meta_2021.winner_name if meta_2021 else None,
                    'party': meta_2021.winner_party if meta_2021 else None,
                    'margin': meta_2021.margin if meta_2021 else None,
                    'top_5': [
                        {
                            'candidate': r.candidate_name,
                            'party': r.party_code,
                            'votes': r.total_votes,
                            'percentage': float(r.vote_percentage),
                        } for r in results_2021
                    ],
                },
                'ls_2019': {
                    'parliament_seat': ls_2019.parliament_constituency if ls_2019 else None,
                    'udf_votes': ls_2019.udf_votes if ls_2019 else 0,
                    'ldf_votes': ls_2019.ldf_votes if ls_2019 else 0,
                    'nda_votes': ls_2019.nda_votes if ls_2019 else 0,
                    'leader': ls_2019.lead_alliance if ls_2019 else None,
                } if ls_2019 else None,
                'ls_2024': {
                    'parliament_seat': ls_2024.parliament_constituency if ls_2024 else None,
                    'udf_votes': ls_2024.udf_votes if ls_2024 else 0,
                    'ldf_votes': ls_2024.ldf_votes if ls_2024 else 0,
                    'nda_votes': ls_2024.nda_votes if ls_2024 else 0,
                    'leader': ls_2024.lead_alliance if ls_2024 else None,
                } if ls_2024 else None,
            }
        
        return historical

    def export_parties(self):
        """Export party master data"""
        parties = []
        for party in Party.objects.all():
            parties.append({
                'code': party.code,
                'name': party.full_name,
                'alliance': party.alliance,
                'color_code': party.color_code,
            })
        return parties
