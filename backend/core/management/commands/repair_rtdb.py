# backend/core/management/commands/repair_rtdb.py
"""
Repair RTDB nodes wiped by a bad ref.set() call.
Re-pushes full candidate + live data for declared constituencies.

Usage:
    python manage.py repair_rtdb               # all RESULT_DECLARED
    python manage.py repair_rtdb --ac 12       # single AC
    python manage.py repair_rtdb --all         # all 140 regardless of status
"""
import os
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Constituency, Candidate, LiveResult, ECICandidateMatch
from firebase_rtdb import push_constituency, update_rtdb_meta


class Command(BaseCommand):
    help = "Re-push full RTDB data for constituencies whose nodes were wiped"

    def add_arguments(self, parser):
        parser.add_argument("--ac", type=int, default=None, help="Single AC number")
        parser.add_argument("--all", action="store_true", help="Repair all 140 constituencies")

    def handle(self, *args, **options):
        single_ac = options["ac"]
        repair_all = options["all"]

        if single_ac:
            ac_numbers = [single_ac]
        elif repair_all:
            ac_numbers = list(
                Constituency.objects.values_list("number", flat=True).order_by("number")
            )
        else:
            # Default: only RESULT_DECLARED seats (the ones the bad push wiped)
            ac_numbers = list(
                LiveResult.objects
                .filter(status="RESULT_DECLARED")
                .values_list("constituency__number", flat=True)
                .order_by("constituency__number")
            )

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\nRepairing {len(ac_numbers)} constituencies ...\n"
        ))

        fixed = 0
        for ac_no in ac_numbers:
            try:
                constituency = Constituency.objects.get(number=ac_no)
            except Constituency.DoesNotExist:
                self.stdout.write(f"  [SKIP] AC {ac_no} not in DB")
                continue

            try:
                live = LiveResult.objects.get(constituency=constituency)
            except LiveResult.DoesNotExist:
                self.stdout.write(f"  [SKIP] AC {ac_no} no LiveResult")
                continue

            # Build candidate list from DB
            candidates_qs = (
                Candidate.objects
                .filter(constituency=constituency)
                .select_related("party")
                .order_by("-votes")
            )
            rtdb_candidates = [
                {
                    "name": c.name,
                    "party": c.party.code if c.party else "",
                    "votes": c.votes,
                }
                for c in candidates_qs
            ]

            # Append NOTA from latest ECICandidateMatch if available
            nota_match = (
                ECICandidateMatch.objects
                .filter(constituency=constituency, is_nota=True)
                .order_by("-scrape__scraped_at")
                .first()
            )
            nota_votes = nota_match.eci_total_votes if nota_match else 0
            if nota_votes > 0:
                rtdb_candidates.append({"name": "NOTA", "party": "NOTA", "votes": nota_votes})

            if not rtdb_candidates:
                self.stdout.write(
                    self.style.WARNING(f"  [WARN] AC {ac_no} {constituency.name} -- no candidates, skipping")
                )
                continue

            # Full push — restores entire node
            rtdb_data = {
                "status":           live.status,
                "rounds_completed": live.rounds_completed,
                "total_rounds":     getattr(live, "total_rounds", 0) or 0,
                "last_updated":     timezone.now().isoformat(),
                "candidates":       rtdb_candidates,
                "votes_counted":    live.votes_counted or 0,
                "valid_votes":      live.valid_votes or 0,
                "total_electors":   live.total_electors or 0,
                "votes_polled":     live.votes_polled or 0,
                "rejected_votes":   live.rejected_votes or 0,
            }

            push_constituency(ac_no, rtdb_data)
            total_v = sum(c["votes"] for c in rtdb_candidates if c.get("name") != "NOTA")
            self.stdout.write(
                self.style.SUCCESS(
                    f"  [OK] AC {ac_no:3d} {constituency.name:<28} "
                    f"status={live.status:<16} cands={len(candidates_qs)} votes={total_v:,}"
                )
            )
            fixed += 1

        self.stdout.write(self.style.SUCCESS(f"\nRepaired {fixed} / {len(ac_numbers)} constituencies"))
        if fixed:
            self.stdout.write("Updating /meta ...")
            update_rtdb_meta()
            self.stdout.write(self.style.SUCCESS("Done."))
