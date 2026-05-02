# backend/core/api/scraper_views.py
"""
REST API endpoints for the ECI Scraper.
These let the React frontend trigger scrapes, view results,
and commit matched data — all via JSON.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny  # Dev only — switch to IsAdminUser for prod
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
import os

# Playwright sync_api uses asyncio under the hood, which sets a running event loop 
# on the thread. Django detects this and blocks ORM operations by throwing 
# SynchronousOnlyOperation. We bypass this since our views are actually synchronous.
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

import threading

from core.models import Constituency, Candidate, LiveResult, ECIScrapeRaw, ECICandidateMatch
from core.eci_scraper import (
    scrape_constituency,
    BIHAR_TEST_BASE_URL, BIHAR_STATE_CODE,
    ECI_BASE_URL, KERALA_STATE_CODE,
)


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _normalise(name):
    return " ".join(name.lower().strip().split())


def _save_scrape_to_db(ac_number, scrape_result):
    """Save scrape result and auto-match candidates. Returns ECIScrapeRaw or None."""
    try:
        constituency = Constituency.objects.get(number=ac_number)
    except Constituency.DoesNotExist:
        return None

    raw = ECIScrapeRaw.objects.create(
        constituency=constituency,
        rounds_completed=scrape_result["rounds_completed"],
        total_rounds=scrape_result["total_rounds"],
        is_final=scrape_result["is_final"],
        eci_last_updated=scrape_result.get("eci_last_updated", ""),
        raw_candidates=scrape_result["candidates"],
        match_status="PENDING",
    )

    db_candidates = {
        _normalise(c.name): c
        for c in Candidate.objects.filter(constituency=constituency)
    }

    matched_count = 0
    from core.models import CandidateAlias

    for cand in scrape_result["candidates"]:
        db_candidate = None
        is_nota = cand["is_nota"]

        if not is_nota:
            alias = CandidateAlias.objects.filter(constituency=constituency, eci_name=cand["name"]).first()
            if alias:
                db_candidate = alias.candidate
            else:
                norm_name = _normalise(cand["name"])
                db_candidate = db_candidates.get(norm_name)
                if not db_candidate:
                    first_word = norm_name.split()[0] if norm_name else ""
                    for db_norm, db_cand in db_candidates.items():
                        if db_norm.startswith(first_word) and len(first_word) > 3:
                            db_candidate = db_cand
                            break
            if db_candidate:
                matched_count += 1

        ECICandidateMatch.objects.create(
            scrape=raw,
            constituency=constituency,
            eci_name=cand["name"],
            eci_party=cand["party"],
            eci_total_votes=cand["total_votes"],
            eci_vote_percentage=cand["vote_percentage"],
            eci_is_leading=cand["is_leading"],
            candidate=db_candidate,
            is_confirmed=bool(db_candidate),
            is_nota=is_nota,
        )

    total_real = sum(1 for c in scrape_result["candidates"] if not c["is_nota"])
    if matched_count == total_real:
        raw.match_status = "MATCHED"
        raw.save()
        _execute_commit(raw)
    elif matched_count > 0:
        raw.match_status = "PARTIAL"
        raw.save()
    else:
        raw.save()

    return raw

def _execute_commit(raw):
    """Programmatically commit a scrape result."""
    matches = raw.matches.filter(is_confirmed=True, is_nota=False).select_related("candidate")
    for match in matches:
        if not match.candidate:
            continue
        c = match.candidate
        c.votes = match.eci_total_votes
        c.vote_percentage = match.eci_vote_percentage
        c.is_winner = raw.is_final and match.eci_is_leading
        c.save()

    live, _ = LiveResult.objects.get_or_create(constituency=raw.constituency)
    live.rounds_completed = raw.rounds_completed
    live.status = "RESULT_DECLARED" if raw.is_final else "IN_PROGRESS"
    live.save()

    raw.match_status = "MATCHED"
    raw.save()


def _serialize_scrape(raw):
    """Serialize an ECIScrapeRaw + matches to JSON."""
    matches = raw.matches.select_related("candidate", "candidate__party").order_by("-eci_total_votes")
    return {
        "id": raw.id,
        "constituency_number": raw.constituency.number,
        "constituency_name": raw.constituency.name,
        "scraped_at": raw.scraped_at.isoformat() if raw.scraped_at else None,
        "rounds_completed": raw.rounds_completed,
        "total_rounds": raw.total_rounds,
        "is_final": raw.is_final,
        "eci_last_updated": raw.eci_last_updated,
        "match_status": raw.match_status,
        "matches": [
            {
                "id": m.id,
                "eci_name": m.eci_name,
                "eci_party": m.eci_party,
                "eci_total_votes": m.eci_total_votes,
                "eci_vote_percentage": m.eci_vote_percentage,
                "eci_is_leading": m.eci_is_leading,
                "is_nota": m.is_nota,
                "is_confirmed": m.is_confirmed,
                "candidate_id": m.candidate_id,
                "candidate_name": m.candidate.name if m.candidate else None,
                "candidate_party": m.candidate.party.code if m.candidate else None,
            }
            for m in matches
        ],
    }


# ─── VIEWS ───────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([AllowAny])
def scraper_status(request):
    """
    GET /api/scraper/status/
    Returns per-constituency scrape status + global stats.
    """
    constituencies = Constituency.objects.select_related("district").order_by("number")

    rows = []
    for c in constituencies:
        latest = c.eci_raw_results.first()
        rows.append({
            "number": c.number,
            "name": c.name,
            "district": c.district.name,
            "latest_scrape": {
                "id": latest.id,
                "scraped_at": latest.scraped_at.isoformat(),
                "rounds_completed": latest.rounds_completed,
                "total_rounds": latest.total_rounds,
                "is_final": latest.is_final,
                "match_status": latest.match_status,
            } if latest else None,
        })

    return Response({
        "total": constituencies.count(),
        "scraped": ECIScrapeRaw.objects.values("constituency").distinct().count(),
        "pending_match": ECIScrapeRaw.objects.filter(match_status="PENDING").count(),
        "committed": ECIScrapeRaw.objects.filter(match_status="MATCHED").count(),
        "constituencies": rows,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def scraper_run(request):
    """
    POST /api/scraper/run/
    Body: { "ac_number": 1 | "all", "test_mode": true/false }
    For a single AC: runs synchronously, returns result.
    For "all": spawns background thread, returns immediately.
    """
    ac_param = request.data.get("ac_number", "")
    test_mode = request.data.get("test_mode", True)

    base_url = BIHAR_TEST_BASE_URL if test_mode else ECI_BASE_URL
    state_code = BIHAR_STATE_CODE if test_mode else KERALA_STATE_CODE

    if str(ac_param) == "all":
        def run_all():
            from django.core.cache import cache
            import time
            cache.set("stop_scrape", False, 3600)
            
            all_acs = list(Constituency.objects.values_list("number", flat=True).order_by("number"))
            
            # Using 6 browsers
            NUM_THREADS = 6
            chunks = [all_acs[i::NUM_THREADS] for i in range(NUM_THREADS)]
            
            def worker_thread(chunk):
                from core.eci_scraper import _cleanup_playwright
                from django.db import connection
                try:
                    for ac_num in chunk:
                        if cache.get("stop_scrape"):
                            break
                        result = scrape_constituency(ac_num, base_url=base_url, state_code=state_code)
                        if result["success"]:
                            _save_scrape_to_db(ac_num, result)
                        time.sleep(1.0)
                finally:
                    _cleanup_playwright()
                    connection.close()

            threads = []
            for chunk in chunks:
                if chunk:
                    t = threading.Thread(target=worker_thread, args=(chunk,), daemon=True)
                    t.start()
                    threads.append(t)
            
            # Since this is a daemon thread launched by the view, it can safely join its children
            for t in threads:
                t.join()

        thread = threading.Thread(target=run_all, daemon=True)
        thread.start()
        return Response({
            "status": "started",
            "message": "Scraping all constituencies in background. Poll /api/scraper/status/ for progress.",
        })

    # Single AC
    try:
        ac_number = int(ac_param)
    except (ValueError, TypeError):
        return Response({"error": f"Invalid AC number: {ac_param}"}, status=status.HTTP_400_BAD_REQUEST)

    result = scrape_constituency(ac_number, base_url=base_url, state_code=state_code)

    if not result["success"]:
        return Response({
            "error": result["error"],
            "source_url": result.get("source_url", ""),
        }, status=status.HTTP_502_BAD_GATEWAY)

    raw = _save_scrape_to_db(ac_number, result)
    if not raw:
        return Response({"error": f"AC {ac_number} not found in database"}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        "status": "scraped",
        "scrape": _serialize_scrape(raw),
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def scraper_stop(request):
    """
    POST /api/scraper/stop/
    Signals the background scrape thread to stop.
    """
    from django.core.cache import cache
    cache.set("stop_scrape", True, 3600)
    return Response({"status": "stopped", "message": "Scrape stopping..."})


@api_view(["GET"])
@permission_classes([AllowAny])
def scraper_scrape_detail(request, scrape_id):
    """
    GET /api/scraper/scrape/<id>/
    Returns full scrape detail with candidate matches.
    """
    try:
        raw = ECIScrapeRaw.objects.get(id=scrape_id)
    except ECIScrapeRaw.DoesNotExist:
        return Response({"error": "Scrape not found"}, status=status.HTTP_404_NOT_FOUND)

    # Also return DB candidates for matching UI
    db_candidates = Candidate.objects.filter(
        constituency=raw.constituency
    ).select_related("party").order_by("name")

    return Response({
        "scrape": _serialize_scrape(raw),
        "db_candidates": [
            {"id": c.id, "name": c.name, "party": c.party.code}
            for c in db_candidates
        ],
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def scraper_save_matches(request, scrape_id):
    """
    POST /api/scraper/scrape/<id>/save-matches/
    Body: { "matches": { "<match_id>": <candidate_id|"nota"|"skip">, ... } }
    """
    try:
        raw = ECIScrapeRaw.objects.get(id=scrape_id)
    except ECIScrapeRaw.DoesNotExist:
        return Response({"error": "Scrape not found"}, status=status.HTTP_404_NOT_FOUND)

    match_map = request.data.get("matches", {})
    updated = 0

    for match_id_str, value in match_map.items():
        try:
            match = ECICandidateMatch.objects.get(id=int(match_id_str), scrape=raw)
        except (ValueError, ECICandidateMatch.DoesNotExist):
            continue

        if value == "skip" or value == "":
            match.candidate = None
            match.is_confirmed = False
        elif value == "nota":
            match.is_nota = True
            match.candidate = None
            match.is_confirmed = True
        else:
            try:
                candidate = Candidate.objects.get(id=int(value))
                match.candidate = candidate
                match.is_confirmed = True
                updated += 1
                
                # Save alias for future auto-matching
                from core.models import CandidateAlias
                CandidateAlias.objects.get_or_create(
                    constituency=raw.constituency,
                    eci_name=match.eci_name,
                    defaults={'candidate': candidate}
                )
            except (ValueError, Candidate.DoesNotExist):
                continue
        match.save()

    # Recompute status
    all_matches = raw.matches.filter(is_nota=False)
    confirmed = all_matches.filter(is_confirmed=True).count()
    total = all_matches.count()
    if confirmed == total:
        raw.match_status = "MATCHED"
    elif confirmed > 0:
        raw.match_status = "PARTIAL"
    raw.save()

    return Response({
        "status": "saved",
        "updated": updated,
        "match_status": raw.match_status,
        "scrape": _serialize_scrape(raw),
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def scraper_commit(request, scrape_id):
    """
    POST /api/scraper/commit/<id>/
    Write matched results into Candidate + LiveResult tables.
    """
    try:
        raw = ECIScrapeRaw.objects.get(id=scrape_id)
    except ECIScrapeRaw.DoesNotExist:
        return Response({"error": "Scrape not found"}, status=status.HTTP_404_NOT_FOUND)

    matches = raw.matches.filter(is_confirmed=True, is_nota=False).select_related("candidate", "candidate__party")

    committed = 0
    for match in matches:
        if not match.candidate:
            continue
        c = match.candidate
        c.votes = match.eci_total_votes
        c.vote_percentage = match.eci_vote_percentage
        c.is_winner = raw.is_final and match.eci_is_leading
        c.save()
        committed += 1

    live, _ = LiveResult.objects.get_or_create(constituency=raw.constituency)
    live.rounds_completed = raw.rounds_completed
    live.status = "RESULT_DECLARED" if raw.is_final else "IN_PROGRESS"
    live.save()

    raw.match_status = "MATCHED"
    raw.save()

    return Response({
        "status": "committed",
        "committed": committed,
        "constituency": raw.constituency.name,
        "rounds": f"{raw.rounds_completed}/{raw.total_rounds}",
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def scraper_deploy(request):
    """
    POST /api/scraper/deploy/
    Exports JSON, builds frontend, and deploys to Firebase.
    """
    import subprocess
    import sys
    
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    root_dir = os.path.dirname(backend_dir)
    frontend_dir = os.path.join(root_dir, 'frontend')

    # On Windows, firebase.cmd lives in the user's npm global bin dir.
    # We resolve it via APPDATA so it works for any user without hardcoding.
    if sys.platform == 'win32':
        appdata = os.environ.get('APPDATA', '')
        firebase_cmd = os.path.join(appdata, 'npm', 'firebase.cmd')
        npm_cmd = 'npm.cmd'
    else:
        firebase_cmd = 'firebase'
        npm_cmd = 'npm'

    try:
        # 1. Export JSON — must go to public/data/ so Vite includes it in the dist
        export_res = subprocess.run(
            ["python", "manage.py", "export_json", "--output", "../frontend/public/data/"],
            cwd=backend_dir, check=True, capture_output=True, text=True,
            env={**os.environ, 'PYTHONUTF8': '1'}
        )
        
        # 2. Build Frontend
        subprocess.run(
            [npm_cmd, 'run', 'build'],
            cwd=frontend_dir, check=True, capture_output=True, text=True
        )
        
        # 3. Deploy to Firebase using full path to avoid PATH lookup issues
        deploy_res = subprocess.run(
            [firebase_cmd, 'deploy', '--only', 'hosting'],
            cwd=root_dir, check=True, capture_output=True, text=True
        )

        return Response({
            "status": "deployed", 
            "message": "Successfully exported, built, and deployed to Firebase.",
            "details": deploy_res.stdout
        })
    except subprocess.CalledProcessError as e:
        return Response({
            "error": "Deployment failed.",
            "details": e.stderr or e.stdout
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

