from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Party, Candidate, HistoricalResult2021, HistoricalResult2016, PartyAllianceYear

class Command(BaseCommand):
    help = 'Fix duplicate parties and standardize Independent codes'

    def handle(self, *args, **options):
        # Maps of (Canonical Code, Full Name) -> [Duplicate Codes]
        MERGE_MAP = {
            # Standardize major duplicates
            ('CONG(S)', 'Congress (Secular)'): ['Congress (Secular)', 'CONG(S)'],
            ('KC(M)', 'Kerala Congress (M)'): ['KEC(M)', 'Kerala Congress (M)', 'KC(M)'],
            ('KC(B)', 'Kerala Congress (B)'): ['KEC(B)', 'Kerala Congress (B)', 'KC(B)'],
            ('KC(J)', 'Kerala Congress (Jacob)'): ['KEC(J)', 'Kerala Congress (Jacob)', 'KC(J)'],
            ('RPI(A)', 'RPI(A)'): ['RPI (A)', 'RPI(A)'],
            
            # Standardize Independents
            ('IND (CPI)', 'Independent (CPI Support)'): ['Independent (CPI sup'],
            ('IND (CPI(M))', 'Independent (CPI(M) Support)'): ['Independent (CPI(M) '],
            ('IND (INL)', 'Independent (INL Support)'): ['Independent (INL sup', 'Independent (INL Sup'],
            ('IND (INC)', 'Independent (INC Support)'): ['Independent (INC Sup'],
            ('IND (IUML)', 'Independent (IUML Support)'): ['Independent (IUML Su'],
            ('IND (RSP)', 'Independent (RSP Support)'): ['Independent (RSP sup'],
            ('IND (BJP)', 'Independent (BJP Support)'): ['BJP (Independent)'],
        }

        with transaction.atomic():
            for (target_code, target_name), duplicates in MERGE_MAP.items():
                self.stdout.write(f"\nProcessing target: {target_code} ({target_name})")
                
                # Find all party objects matching the duplicates
                parties = Party.objects.filter(code__in=duplicates)
                if not parties.exists():
                    self.stdout.write(f"  No duplicate parties found for {target_code}")
                    continue

                # Ensure target canonical party exists
                target_party = Party.objects.filter(code=target_code).first()
                if not target_party:
                    # If the target doesn't exist by exact code, pick the first duplicate to BECOME the target
                    target_party = parties.first()
                    self.stdout.write(f"  Renaming {target_party.code} to {target_code}")
                    target_party.code = target_code
                    target_party.full_name = target_name
                    target_party.save()
                else:
                    # Target exists, ensure its name is standardized
                    if target_party.full_name != target_name:
                        target_party.full_name = target_name
                        target_party.save()
                
                # Update references and delete other duplicates
                for dup in parties:
                    if dup.id == target_party.id:
                        continue # Skip the target itself
                    
                    self.stdout.write(f"  Merging duplicate {dup.code} (ID: {dup.id}) into {target_code}...")
                    
                    # 1. Update 2026 Candidates
                    cands = Candidate.objects.filter(party=dup)
                    cands_count = cands.count()
                    cands.update(party=target_party)
                    if cands_count > 0:
                        self.stdout.write(f"    -> Updated {cands_count} candidates")

                    # 2. Update 2021 Results
                    res21 = HistoricalResult2021.objects.filter(party_code=dup.code)
                    res21_count = res21.count()
                    res21.update(party_code=target_code)
                    if res21_count > 0:
                        self.stdout.write(f"    -> Updated {res21_count} 2021 results")

                    # 3. Update 2016 Results
                    res16_w = HistoricalResult2016.objects.filter(winner_party=dup.code)
                    res16_w_count = res16_w.count()
                    res16_w.update(winner_party=target_code)
                    
                    res16_r = HistoricalResult2016.objects.filter(runnerup_party=dup.code)
                    res16_r_count = res16_r.count()
                    res16_r.update(runnerup_party=target_code)
                    
                    if res16_w_count > 0 or res16_r_count > 0:
                        self.stdout.write(f"    -> Updated {res16_w_count} winner and {res16_r_count} runner-up 2016 results")

                    # 4. Update PartyAllianceYear mappings
                    pay = PartyAllianceYear.objects.filter(canonical_code=dup.code)
                    pay_count = pay.count()
                    pay.update(canonical_code=target_code)
                    if pay_count > 0:
                        self.stdout.write(f"    -> Updated {pay_count} PAY mappings")

                    # 5. Handle PAY rows where party_code was the duplicate code
                    # If we renamed KEC(M) to KC(M), what happens to PAY records where party_code='KEC(M)'?
                    # The canonical code is now KC(M). So the PAY record 'KEC(M)' -> 'KC(M)' should be kept.
                    # If it was 'KEC(M)' -> 'KEC(M)', the update above made it 'KEC(M)' -> 'KC(M)', which is correct!
                    # What if PAY record is 'KC(M)' -> 'KC(M)'? That's also fine, we handle canonical cleanup below.

                    self.stdout.write(f"  Deleting duplicate party {dup.code}")
                    dup.delete()

            # Final cleanup: if a PartyAllianceYear has canonical_code == party_code, we can clear canonical_code
            for pay in PartyAllianceYear.objects.exclude(canonical_code=''):
                if pay.party_code == pay.canonical_code:
                    pay.canonical_code = ''
                    pay.save()

        self.stdout.write(self.style.SUCCESS('\nSuccessfully fixed duplicate parties!'))
