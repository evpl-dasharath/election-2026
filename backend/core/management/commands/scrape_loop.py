# backend/core/management/commands/scrape_loop.py
"""
Continuous ECI scrape loop.
Skips constituencies already declared — once RESULT_DECLARED, never scraped again.

Usage:
    python manage.py scrape_loop                       # Kerala live, all 140, loop
    python manage.py scrape_loop --test                # Bihar test, all 140, loop
    python manage.py scrape_loop --ac 1 --test         # Bihar, AC1 only, run once
    python manage.py scrape_loop --ac 1 --test --loop  # Bihar, AC1 only, loop forever
"""

import time
import logging
import threading
import os

from django.core.management.base import BaseCommand
from django.db import connection

from core.eci_scraper import (
    scrape_constituency,
    _cleanup_playwright,
    ECI_BASE_URL, KERALA_STATE_CODE,
    BIHAR_TEST_BASE_URL, BIHAR_STATE_CODE,
)
from core.models import Constituency, LiveResult
from core.api.scraper_views import _save_scrape_to_db

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

logger = logging.getLogger(__name__)
NUM_THREADS = 6


def _get_pending_acs(ac_numbers):
    """Return AC numbers that are NOT yet RESULT_DECLARED."""
    declared = set(
        LiveResult.objects.filter(
            constituency__number__in=ac_numbers,
            status="RESULT_DECLARED"
        ).values_list("constituency__number", flat=True)
    )
    pending = [ac for ac in ac_numbers if ac not in declared]
    return pending, declared


def _worker(chunk, base_url, state_code, results, lock):
    try:
        for ac_num in chunk:
            try:
                result = scrape_constituency(ac_num, base_url=base_url, state_code=state_code)
                if result["success"]:
                    raw = _save_scrape_to_db(ac_num, result)
                    status = raw.match_status if raw else "NO_DB_RECORD"
                else:
                    status = f"SCRAPE_FAILED: {result.get('error', '')}"
                with lock:
                    results[ac_num] = status
            except Exception as e:
                logger.error(f"AC {ac_num} error: {e}")
                with lock:
                    results[ac_num] = f"ERROR: {e}"
    finally:
        _cleanup_playwright()
        connection.close()


def run_single_cycle(ac_numbers, base_url, state_code, stdout):
    chunks = [ac_numbers[i::NUM_THREADS] for i in range(NUM_THREADS)]
    results = {}
    lock = threading.Lock()

    threads = []
    for chunk in chunks:
        if chunk:
            t = threading.Thread(
                target=_worker,
                args=(chunk, base_url, state_code, results, lock),
                daemon=True,
            )
            t.start()
            threads.append(t)

    for t in threads:
        t.join()

    matched = sum(1 for s in results.values() if s == "MATCHED")
    partial = sum(1 for s in results.values() if s == "PARTIAL")
    pending = sum(1 for s in results.values() if s == "PENDING")
    failed  = sum(1 for s in results.values() if "FAILED" in s or "ERROR" in s)
    stdout.write(
        f"  Matched: {matched} | Partial: {partial} | "
        f"Pending: {pending} | Failed: {failed} / {len(ac_numbers)}"
    )
    return results


class Command(BaseCommand):
    help = "Continuous ECI scrape loop — skips already-declared seats"

    def add_arguments(self, parser):
        parser.add_argument("--test", action="store_true", help="Use Bihar test data")
        parser.add_argument("--ac", type=int, default=None, help="Single AC number only")
        parser.add_argument("--loop", action="store_true", help="Loop forever even for single AC")

    def handle(self, *args, **options):
        test_mode  = options["test"]
        single_ac  = options["ac"]
        loop       = options["loop"]

        base_url   = BIHAR_TEST_BASE_URL if test_mode else ECI_BASE_URL
        state_code = BIHAR_STATE_CODE    if test_mode else KERALA_STATE_CODE
        mode_label = "BIHAR TEST"        if test_mode else "KERALA LIVE"

        all_ac_numbers = [single_ac] if single_ac else list(
            Constituency.objects.values_list("number", flat=True).order_by("number")
        )
        label = f"AC {single_ac}" if single_ac else f"All {len(all_ac_numbers)} constituencies"

        self.stdout.write(self.style.SUCCESS(
            f"\n=== Scrape Loop === Mode: {mode_label} | {label} ==="
        ))

        run_forever = loop or not single_ac

        # ── Single run mode
        if not run_forever:
            self.stdout.write(f"Running once for AC {single_ac}...")
            result = scrape_constituency(single_ac, base_url=base_url, state_code=state_code)
            if not result["success"]:
                self.stdout.write(self.style.ERROR(f"Scrape failed: {result.get('error')}"))
                return
            raw = _save_scrape_to_db(single_ac, result)
            if raw:
                self.stdout.write(self.style.SUCCESS(f"Done — match_status: {raw.match_status}"))
            else:
                self.stdout.write(self.style.ERROR(f"AC {single_ac} not found in DB"))
            return

        # ── Loop mode
        self.stdout.write("Press Ctrl+C to stop\n")
        cycle = 0

        try:
            while True:
                cycle += 1
                start = time.time()

                # Check which seats still need scraping
                pending_acs, declared = _get_pending_acs(all_ac_numbers)

                self.stdout.write(self.style.MIGRATE_HEADING(
                    f"\n--- Cycle {cycle} | "
                    f"Pending: {len(pending_acs)} | "
                    f"Declared (skipped): {len(declared)} ---"
                ))

                if not pending_acs:
                    self.stdout.write(self.style.SUCCESS(
                        "All seats declared! Nothing left to scrape."
                    ))
                    break

                run_single_cycle(pending_acs, base_url, state_code, self.stdout)

                elapsed = time.time() - start
                self.stdout.write(self.style.SUCCESS(
                    f"  Cycle {cycle} done in {elapsed:.0f}s"
                ))

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nStopped."))