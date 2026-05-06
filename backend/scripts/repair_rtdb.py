#!/usr/bin/env python3
"""
repair_rtdb.py
===============
Re-pushes full RTDB data for constituencies whose Firebase node was wiped
by a previous partial push (e.g. the old statewise scraper used ref.set
with only {status, last_updated}, deleting all candidates).

Reads candidate + LiveResult data from the DB and does a full push.

Usage:
    python manage.py shell < repair_rtdb.py
    -- or --
    python repair_rtdb.py           # repair ALL RESULT_DECLARED seats
    python repair_rtdb.py --ac 12   # repair one specific AC
"""
import os, sys, argparse, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from core.models import Constituency, Candidate, LiveResult, ECICandidateMatch
from firebase_rtdb import push_constituency, update_rtdb_meta
from django.utils import timezone


def repair(ac_numbers):
    fixed = 0
    for ac_no in ac_numbers:
        try:
            constituency = Constituency.objects.get(number=ac_no)
        except Constituency.DoesNotExist:
            print(f"  [SKIP] AC {ac_no} not in DB")
            continue

        try:
            live = LiveResult.objects.get(constituency=constituency)
        except LiveResult.DoesNotExist:
            print(f"  [SKIP] AC {ac_no} no LiveResult")
            continue

        # Build candidate list from DB (already committed votes)
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

        # Also grab NOTA from the latest ECICandidateMatch if available
        nota_votes = 0
        nota_match = (
            ECICandidateMatch.objects
            .filter(constituency=constituency, is_nota=True)
            .order_by("-scrape__scraped_at")
            .first()
        )
        if nota_match and nota_match.eci_total_votes:
            nota_votes = nota_match.eci_total_votes
            rtdb_candidates.append({"name": "NOTA", "party": "NOTA", "votes": nota_votes})

        if not rtdb_candidates:
            print(f"  [WARN] AC {ac_no} {constituency.name} -- no candidates in DB, skipping")
            continue

        # Full push (restores everything)
        rtdb_data = {
            "status":           live.status,
            "rounds_completed": live.rounds_completed,
            "total_rounds":     live.total_rounds if hasattr(live, "total_rounds") else 0,
            "last_updated":     timezone.now().isoformat(),
            "candidates":       rtdb_candidates,
            "votes_counted":    live.votes_counted,
            "valid_votes":      live.valid_votes or 0,
            "total_electors":   live.total_electors or 0,
            "votes_polled":     live.votes_polled or 0,
            "rejected_votes":   live.rejected_votes or 0,
        }

        push_constituency(ac_no, rtdb_data)
        total_v = sum(c["votes"] for c in rtdb_candidates)
        print(
            f"  [OK] AC {ac_no:3d} {constituency.name:<28} "
            f"status={live.status} cands={len(candidates_qs)} "
            f"total_votes={total_v:,}"
        )
        fixed += 1

    print(f"\n  Repaired {fixed} / {len(ac_numbers)} constituencies")
    if fixed:
        print("  Updating /meta ...")
        update_rtdb_meta()


def main():
    parser = argparse.ArgumentParser(description="Repair wiped RTDB constituency nodes")
    parser.add_argument("--ac", type=int, default=None, help="Single AC number to repair")
    parser.add_argument(
        "--all-declared", action="store_true",
        help="Repair all RESULT_DECLARED constituencies (default if no --ac given)"
    )
    args = parser.parse_args()

    if args.ac:
        ac_numbers = [args.ac]
        print(f"\nRepairing AC {args.ac} ...\n")
    else:
        # Default: repair all RESULT_DECLARED seats
        ac_numbers = list(
            LiveResult.objects
            .filter(status="RESULT_DECLARED")
            .values_list("constituency__number", flat=True)
            .order_by("constituency__number")
        )
        print(f"\nRepairing all {len(ac_numbers)} RESULT_DECLARED seats ...\n")

    repair(ac_numbers)


if __name__ == "__main__":
    main()
