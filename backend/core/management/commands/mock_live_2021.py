import random
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Constituency, Candidate, LiveResult, HistoricalResult2021

class Command(BaseCommand):
    help = 'Generate mock live counting data for 2026 that mimics the 2021 results'

    def handle(self, *args, **options):
        self.stdout.write("Clearing existing live data...")
        
        with transaction.atomic():
            # Clear existing live results
            LiveResult.objects.all().delete()
            Candidate.objects.update(votes=0, vote_percentage=0, is_leading=False, is_winner=False)
            
            constituencies = Constituency.objects.prefetch_related('candidates_2026__party').all()
            
            for const in constituencies:
                candidates = list(const.candidates_2026.all())
                if not candidates:
                    continue
                
                # Fetch 2021 results to mimic
                cands_2021 = list(HistoricalResult2021.objects.filter(constituency=const).order_by('-total_votes'))
                if not cands_2021:
                    continue
                
                total_electors = random.randint(140000, 220000)
                turnout = random.uniform(0.70, 0.78)
                votes_polled = int(total_electors * turnout)
                valid_votes = int(votes_polled * 0.99)
                
                live, _ = LiveResult.objects.get_or_create(constituency=const)
                live.status = 'RESULT_DECLARED'
                live.total_electors = total_electors
                live.votes_polled = votes_polled
                live.votes_counted = votes_polled
                live.valid_votes = valid_votes
                live.rejected_votes = votes_polled - valid_votes
                live.rounds_completed = 14
                live.total_rounds = 14
                live.save()
                
                # We need to map 2021 candidates to 2026 candidates.
                # First try exact party match. If not, try alliance match.
                remaining_votes = valid_votes
                
                for c21 in cands_2021:
                    target_cand = None
                    # Try exact party match
                    target_cand = next((c for c in candidates if c.party.code == c21.party_code), None)
                    
                    if not target_cand and c21.party and c21.party.alliance:
                        # Try alliance match
                        c21_alliance = c21.party.alliance.code
                        target_cand = next((c for c in candidates if c.party.alliance and c.party.alliance.code == c21_alliance and c.votes == 0), None)
                        
                    if target_cand and target_cand.votes == 0:
                        pct = float(c21.vote_percentage) / 100.0
                        noise = random.uniform(0.97, 1.03)
                        votes_to_assign = int(valid_votes * pct * noise)
                        votes_to_assign = min(votes_to_assign, remaining_votes)
                        
                        target_cand.votes = votes_to_assign
                        remaining_votes -= votes_to_assign
                        
                # Distribute remaining to random other candidates
                unassigned = [c for c in candidates if c.votes == 0]
                if unassigned and remaining_votes > 0:
                    for c in unassigned:
                        v = int(remaining_votes / len(unassigned) * random.uniform(0.8, 1.2))
                        c.votes = min(v, remaining_votes)
                        remaining_votes -= c.votes
                
                # Set winner
                total_cand_votes = sum(c.votes for c in candidates)
                if total_cand_votes > 0:
                    candidates.sort(key=lambda x: x.votes, reverse=True)
                    for i, cand in enumerate(candidates):
                        cand.vote_percentage = (cand.votes / votes_polled) * 100 if votes_polled > 0 else 0
                        cand.is_leading = False
                        cand.is_winner = False
                        
                        if i == 0:
                            cand.is_winner = True
                            
                        cand.save()

        self.stdout.write(self.style.SUCCESS("Successfully generated mock 2026 data mirroring 2021!"))
