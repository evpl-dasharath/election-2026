import random
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Constituency, Candidate, LiveResult

class Command(BaseCommand):
    help = 'Generate mock live counting data for the 2026 election to test the frontend'

    def handle(self, *args, **options):
        self.stdout.write("Generating mock live data for all constituencies...")
        
        with transaction.atomic():
            constituencies = Constituency.objects.prefetch_related('candidates_2026__party').all()
            
            for const in constituencies:
                candidates = list(const.candidates_2026.all())
                if not candidates:
                    continue
                
                # Randomly assign a status (70% in progress, 20% declared, 10% not started)
                rand_val = random.random()
                if rand_val < 0.1:
                    status = 'NOT_STARTED'
                elif rand_val < 0.3:
                    status = 'RESULT_DECLARED'
                else:
                    status = 'IN_PROGRESS'
                
                # Mock base numbers
                total_electors = random.randint(140000, 220000)
                total_rounds = random.randint(12, 16)
                
                if status == 'NOT_STARTED':
                    rounds_completed = 0
                    votes_polled = random.randint(int(total_electors * 0.65), int(total_electors * 0.85))
                    votes_counted = 0
                elif status == 'RESULT_DECLARED':
                    rounds_completed = total_rounds
                    votes_polled = random.randint(int(total_electors * 0.65), int(total_electors * 0.85))
                    votes_counted = votes_polled
                else:
                    rounds_completed = random.randint(1, total_rounds - 1)
                    votes_polled = random.randint(int(total_electors * 0.65), int(total_electors * 0.85))
                    votes_counted = int(votes_polled * (rounds_completed / total_rounds))
                
                # Update LiveResult
                live, _ = LiveResult.objects.get_or_create(constituency=const)
                live.status = status
                live.total_electors = total_electors
                live.votes_polled = votes_polled
                live.votes_counted = votes_counted
                live.valid_votes = int(votes_counted * 0.99)
                live.rejected_votes = votes_counted - live.valid_votes
                live.rounds_completed = rounds_completed
                live.total_rounds = total_rounds
                live.save()
                
                # Distribute votes if counting has started
                if votes_counted > 0:
                    # Distribute randomly to LDF, UDF, NDA, and remaining to others
                    main_alliances = ['LDF', 'UDF', 'NDA']
                    weights = [random.uniform(0.3, 0.45), random.uniform(0.3, 0.45), random.uniform(0.1, 0.25)]
                    
                    # Normalize weights so they sum to ~0.95 (leaving 5% for OTH)
                    total_w = sum(weights)
                    weights = [w / total_w * 0.95 for w in weights]
                    
                    # Shuffle to randomize who leads
                    random.shuffle(weights)
                    alliance_weights = {
                        main_alliances[0]: weights[0],
                        main_alliances[1]: weights[1],
                        main_alliances[2]: weights[2],
                    }
                    
                    remaining_votes = live.valid_votes
                    for cand in candidates:
                        alliance = cand.party.alliance
                        if alliance in alliance_weights:
                            cand_votes = int(live.valid_votes * alliance_weights[alliance] * random.uniform(0.9, 1.1))
                            cand.votes = min(cand_votes, remaining_votes)
                        else:
                            # Other parties get very few votes
                            cand_votes = random.randint(100, max(500, int(live.valid_votes * 0.01)))
                            cand.votes = min(cand_votes, remaining_votes)
                        
                        remaining_votes -= cand.votes
                        
                    # Recalculate percentages and set status
                    total_cand_votes = sum(c.votes for c in candidates)
                    if total_cand_votes > 0:
                        # Sort to find the leader
                        candidates.sort(key=lambda x: x.votes, reverse=True)
                        for i, cand in enumerate(candidates):
                            cand.vote_percentage = (cand.votes / votes_polled) * 100 if votes_polled > 0 else 0
                            cand.is_leading = False
                            cand.is_winner = False
                            
                            if i == 0: # Leader
                                if status == 'RESULT_DECLARED':
                                    cand.is_winner = True
                                else:
                                    cand.is_leading = True
                            
                            cand.save()

        self.stdout.write(self.style.SUCCESS("Successfully generated mock live data!"))
