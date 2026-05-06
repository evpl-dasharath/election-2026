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
from django.test import RequestFactory
from core.api.views import historical_comparison, history_all, state_summary, alliance_detail, party_detail


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
            
        # 4.5. HISTORY_ALL.JSON
        self.stdout.write("Exporting history_all.json...")
        history_all_data = self.export_history_all()
        with open(os.path.join(output_dir, 'history_all.json'), 'w') as f:
            json.dump(history_all_data, f, indent=2)
        
        # 5. PARTIES.JSON - Party master data
        self.stdout.write("Exporting parties.json...")
        parties_data = self.export_parties()
        with open(os.path.join(output_dir, 'parties.json'), 'w') as f:
            json.dump(parties_data, f, indent=2)
        
        # 6. ALLIANCE_{CODE}.JSON - Alliance detail pages
        self.stdout.write("Exporting alliance details...")
        alliance_count = self.export_alliances(output_dir)
        
        # 7. PARTY_{CODE}.JSON - Party detail pages
        self.stdout.write("Exporting party details...")
        party_count = self.export_parties_detail(output_dir)
        
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
            f"  - historical.json & history_all.json: full historical data"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  - parties.json: party master data"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  - alliance_*.json: {alliance_count} alliance details"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  - party_*.json: {party_count} party details"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  - Output: {output_dir}"
        ))

    def export_meta(self, timestamp):
        """State-level summary with live aggregates"""
        factory = RequestFactory()
        request = factory.get('/api/summary/')
        response = state_summary(request)
        
        # Add timestamp to the response data since frontend might use it
        data = response.data
        data['timestamp'] = timestamp
        return data

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
                    'alliance': leader.party.alliance.code,
                    'votes': leader.votes,
                    'percentage': float(leader.vote_percentage),
                } if leader else None,
                'runner_up': {
                    'name': runner_up.name,
                    'party': runner_up.party.code,
                    'alliance': runner_up.party.alliance.code,
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
                    'alliance': cand.party.alliance.code,
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
        factory = RequestFactory()
        
        for const in Constituency.objects.all():
            request = factory.get(f'/api/historical/{const.number}/')
            response = historical_comparison(request, constituency_number=const.number)
            historical[str(const.number)] = response.data
        
        return historical

    def export_history_all(self):
        """Export bulk historical endpoint"""
        factory = RequestFactory()
        request = factory.get('/api/history/all/')
        response = history_all(request)
        return response.data

    def export_parties(self):
        """Export party master data"""
        parties = []
        for party in Party.objects.all():
            parties.append({
                'code': party.code,
                'name': party.full_name,
                'alliance': party.alliance.code if party.alliance else 'OTH',
                'color_code': party.color_code,
            })
        return parties

    def export_alliances(self, output_dir):
        """Export alliance detail endpoints"""
        factory = RequestFactory()
        count = 0
        for code in ['LDF', 'UDF', 'NDA', 'OTH']:
            request = factory.get(f'/api/alliance/{code}/')
            response = alliance_detail(request, alliance_code=code)
            with open(os.path.join(output_dir, f'alliance_{code.lower()}.json'), 'w') as f:
                json.dump(response.data, f, indent=2)
            count += 1
        return count

    def export_parties_detail(self, output_dir):
        """Export party detail endpoints"""
        factory = RequestFactory()
        count = 0
        for party in Party.objects.all():
            request = factory.get(f'/api/party/{party.code}/')
            response = party_detail(request, party_code=party.code)
            with open(os.path.join(output_dir, f'party_{party.code.lower()}.json'), 'w') as f:
                json.dump(response.data, f, indent=2)
            count += 1
        return count
