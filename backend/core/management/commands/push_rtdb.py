import time
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Constituency, Candidate, LiveResult
from firebase_rtdb import push_constituency, push_meta
from core.eci_scraper import scrape_constituency

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Continuously scrape ECI data and push changes to Firebase RTDB'

    def add_arguments(self, parser):
        parser.add_argument(
            '--single',
            type=int,
            help='Run once for a single constituency ID (for testing)',
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run exactly one full loop across all constituencies, then exit',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting RTDB Push Service..."))
        
        single_ac = options.get('single')
        run_once = options.get('once')
        
        if single_ac:
            self.stdout.write(f"Running single scrape for AC {single_ac}")
            self.scrape_and_push(single_ac)
            self.update_meta()
            return
            
        while True:
            self.stdout.write(f"\n--- Starting full scrape cycle at {timezone.now()} ---")
            
            # Get all constituencies
            constituencies = Constituency.objects.all().order_by('ac_number')
            
            for c in constituencies:
                try:
                    self.scrape_and_push(c.ac_number)
                except Exception as e:
                    logger.error(f"Failed to process AC {c.ac_number}: {e}")
                    # Continue to next
                    
                # Small delay between scrapes to be nice to ECI/Mock server
                time.sleep(0.5)
                
            self.update_meta()
            
            if run_once:
                self.stdout.write("Run once completed. Exiting.")
                break
                
            self.stdout.write("Cycle complete. Waiting 120 seconds...")
            try:
                time.sleep(120)
            except KeyboardInterrupt:
                self.stdout.write("\nInterrupted by user. Exiting.")
                break

    def scrape_and_push(self, ac_number):
        """Scrapes ECI and pushes to RTDB if changed."""
        try:
            # 1. Fetch from source (mock for now, or real ECI)
            # Use test mode for now (Bihar) as per other scraper code
            result = scrape_constituency(ac_number, base_url="https://results.eci.gov.in/ResultAcGenNov2025", state_code="S04")
            if not result.get("success"):
                logger.warning(f"[AC {ac_number}] Failed to scrape: {result.get('error')}")
                return
            
            # 3. Format for RTDB
            rtdb_data = {
                "status": "RESULT_DECLARED" if result.get("is_final") else "IN_PROGRESS",
                "rounds_completed": result.get("rounds_completed", 0),
                "total_rounds": result.get("total_rounds", 0),
                "last_updated": timezone.now().isoformat(),
                "candidates": []
            }
            
            # Take top candidates (maybe limit to top 5 or so to save space, or all)
            for cand in result.get("candidates", []):
                rtdb_data["candidates"].append({
                    "name": cand.get("name"),
                    "party": cand.get("party"),
                    "votes": cand.get("total_votes", 0)
                })
                
            # 4. Push to RTDB (will only push if changed internally)
            pushed = push_constituency(ac_number, rtdb_data)
            if pushed:
                self.stdout.write(self.style.SUCCESS(f"[AC {ac_number}] Changed -> pushed"))
            else:
                self.stdout.write(f"[AC {ac_number}] No change -> skipped")
                
        except Exception as e:
            logger.error(f"[AC {ac_number}] Error in scrape_and_push: {e}")
            raise

    def update_meta(self):
        """Calculates global summary and pushes to /meta."""
        # Calculate summary based on the latest scraped data in the DB
        # This requires the scraper to also save to DB, which we should do
        # Or calculate it directly here based on some logic.
        
        # Simple placeholder for now - you'll want to implement actual counting logic
        # based on who is leading where.
        summary = {
            "udf": 0,
            "ldf": 0,
            "nda": 0,
            "oth": 0,
            "total_declared": 0,
            "total_counting": 0,
            "timestamp": timezone.now().isoformat()
        }
        
        push_meta(summary)
        self.stdout.write(self.style.SUCCESS("Meta updated"))
