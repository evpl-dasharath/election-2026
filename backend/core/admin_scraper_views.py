# backend/core/admin_scraper_views.py
"""
Custom Django Admin Views — ECI Scraper Dashboard
===================================================
Mounted at:
  /admin/scrape/              → Dashboard (scrape controls)
  /admin/scrape/run/          → POST: trigger scrape for one or all ACs
  /admin/scrape/match/<id>/   → Match ECI names to DB candidates
  /admin/scrape/commit/<id>/  → POST: write matched results to Candidate table

Wire up in backend/config/urls.py:
  from core.admin_scraper_views import scraper_urls
  urlpatterns += scraper_urls
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import path
from django.http import JsonResponse
from django.utils import timezone

import threading

from .models import Constituency, Candidate, LiveResult, ECIScrapeRaw, ECICandidateMatch
from .eci_scraper import scrape_constituency, BIHAR_TEST_BASE_URL, BIHAR_STATE_CODE, ECI_BASE_URL, KERALA_STATE_CODE


# ─── ECI PARTY NAME → DB Party.code MAP ─────────────────────────────────────
# ECI uses full names, abbreviations, or mixed forms on the results page.
# Map every known variant to the canonical Party.code used in the DB.

ECI_PARTY_MAP = {
    # ── LDF ──────────────────────────────────────────────────────────────────
    'CPI(M)':                              'CPI_M',
    'Communist Party of India  (Marxist)': 'CPI_M',
    'Communist Party of India (Marxist)':  'CPI_M',
    'CPIM':                                'CPI_M',
    'CPI(M)-LDF':                          'CPI_M',
    'CPI':                                 'CPI',
    'Communist Party of India':            'CPI',
    'Kerala Congress (B)':                 'KC_B',
    'KC(B)':                               'KC_B',
    'Kerala Congress (M)':                 'KC_M',
    'KC(M)':                               'KC_M',
    'INL':                                 'INL',
    'Indian National League':              'INL',
    'NCP':                                 'NCP',
    'Nationalist Congress Party':          'NCP',
    'JKC':                                 'JKC',
    'Congress (Secular)':                  'CON_S',
    'Indian Socialist Janata Dal':         'ISJD',
    'RJD':                                 'RJD',
    'Rashtriya Janata Dal':                'RJD',
    'LJD':                                 'LJD',
    # ── UDF ──────────────────────────────────────────────────────────────────
    'INC':                                 'INC',
    'Indian National Congress':            'INC',
    'Congress':                            'INC',
    'IUML':                                'IUML',
    'Indian Union Muslim League':          'IUML',
    'KEC':                                 'KEC',
    'Kerala Congress':                     'KEC',
    'KC(J)':                               'KC_J',
    'Kerala Congress (J)':                 'KC_J',
    'RSP':                                 'RSP',
    'Revolutionary Socialist Party':       'RSP',
    'CMP':                                 'CMP',
    'Congress of Malayala People':         'CMP',
    'RMPI':                                'RMPI',
    'AITC':                                'AITC',
    'All India Trinamool Congress':        'AITC',
    'DCK':                                 'KDP',
    'KDP':                                 'KDP',
    'Kerala Democratic Party':             'KDP',
    'AIFB':                                'AIFB',
    'All India Forward Bloc':              'AIFB',
    # ── NDA ──────────────────────────────────────────────────────────────────
    'BJP':                                 'BJP',
    'Bharatiya Janata Party':              'BJP',
    'BDJS':                                'BDJS',
    'Bharath Dharma Jana Sena':            'BDJS',
    'TTP':                                 'TTP',
    'Twenty20':                            'TTP',
    'Twenty20 Party':                      'TTP',
    'Twenty 20 Party':                     'TTP',
    'Twenty20Party':                       'TTP',
    'AIADMK':                              'AIADMK',
    'All India Anna Dravida Munnetra Kazhagam': 'AIADMK',
    'JRS':                                 'JRS',
    'KKC':                                 'KKC',
    # ── Others ───────────────────────────────────────────────────────────────
    'AAP':                                 'AAP',
    'Aam Aadmi Party':                     'AAP',
    'BSP':                                 'BSP',
    'Bahujan Samaj Party':                 'BSP',
    'SDPI':                                'SDPI',
    'Social Democratic Party of India':    'SDPI',
    'SUCI':                                'SUCI',
    'SUCI(C)':                             'SUCI',
    'Socialist Unity Centre of India':     'SUCI',
    'Socialist Unity Centre Of India':     'SUCI',
    'Socialist Unity Centre Of India (COMMUNIST)': 'SUCI',
    'SUCI(Communist)':                     'SUCI',
    'WPOI':                                'WPOI',
    'Welfare Party of India':              'WPOI',
    'CPIML Liberation':                    'CPI_ML_L',
    'CPI(ML) Liberation':                  'CPI_ML_L',
    'CPI(ML)L':                            'CPI_ML_L',
    'CPIML Red Star':                      'CPI_ML_RS',
    'CPI(ML) Red Star':                    'CPI_ML_RS',
    'Communist Party of India (Marxist-Leninist) Red Star': 'CPI_ML_RS',
    'API':                                 'API',
    'Ambedkarite Party of India':          'API',
    # ── Independents & alliance-backed ───────────────────────────────────────
    'IND':                                 'IND',
    'Independent':                         'IND',
    'None of the Above':                   'IND',
    'NOTA':                                'IND',
    'IND(LDF)':                            'IND_LDF',
    'IND(UDF)':                            'IND_UDF',
    'IND(NDA)':                            'IND_NDA',
}


def _resolve_eci_party_code(eci_party_str: str) -> str | None:
    """
    Translate an ECI party string (as scraped from the results page)
    to the canonical Party.code used in our DB.
    Returns None if unmapped.
    """
    raw = eci_party_str.strip()
    # Direct lookup
    code = ECI_PARTY_MAP.get(raw)
    if code:
        return code
    # Case-insensitive fallback
    raw_lower = raw.lower()
    for key, val in ECI_PARTY_MAP.items():
        if key.lower() == raw_lower:
            return val
    return None


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _save_scrape_to_db(ac_number, scrape_result):
    """
    Save a successful scrape result into ECIScrapeRaw + ECICandidateMatch.
    Attempts auto-matching by normalising candidate names.
    Returns the ECIScrapeRaw instance.
    """
    try:
        constituency = Constituency.objects.get(number=ac_number)
    except Constituency.DoesNotExist:
        return None

    # Create raw scrape record
    raw = ECIScrapeRaw.objects.create(
        constituency=constituency,
        rounds_completed=scrape_result["rounds_completed"],
        total_rounds=scrape_result["total_rounds"],
        is_final=scrape_result["is_final"],
        eci_last_updated=scrape_result.get("eci_last_updated", ""),
        raw_candidates=scrape_result["candidates"],
        match_status="PENDING",
    )

    # Build a lookup of existing candidates for this constituency
    # Key: normalised name → Candidate object (also keep list for party-aware search)
    all_db_candidates = list(
        Candidate.objects.filter(constituency=constituency).select_related('party')
    )
    db_candidates = {_normalise(c.name): c for c in all_db_candidates}

    matched_count = 0
    from core.models import CandidateAlias

    for cand in scrape_result["candidates"]:
        db_candidate = None
        is_nota = cand["is_nota"]

        if not is_nota:
            # ── 1. Saved alias (manually confirmed in a previous scrape) ─────
            alias = CandidateAlias.objects.filter(constituency=constituency, eci_name=cand["name"]).first()
            if alias:
                db_candidate = alias.candidate
            else:
                norm_name = _normalise(cand["name"])
                eci_party_code = _resolve_eci_party_code(cand.get("party", ""))

                # ── 2. Exact normalised name match ───────────────────────────
                db_candidate = db_candidates.get(norm_name)

                # ── 3. Fuzzy: first-word prefix, party-filtered first ────────
                if not db_candidate:
                    first_word = norm_name.split()[0] if norm_name else ""
                    if len(first_word) > 3:
                        # Priority A: candidates whose party code also matches
                        if eci_party_code:
                            for db_cand in all_db_candidates:
                                db_norm = _normalise(db_cand.name)
                                party_code = db_cand.party.code if db_cand.party else None
                                if db_norm.startswith(first_word) and party_code == eci_party_code:
                                    db_candidate = db_cand
                                    break

                        # Priority B: fallback — any name prefix match (no party filter)
                        # ONLY use this when party is unknown — prevents cross-party mismatches
                        # e.g. RAJAN. J. PALLAN (INC) should NOT match Rajan. M (IND)
                        if not db_candidate and not eci_party_code:
                            for db_norm, db_cand in db_candidates.items():
                                if db_norm.startswith(first_word):
                                    db_candidate = db_cand
                                    break

                # ── 4. Last resort: match purely by party code (one candidate)
                #    Useful when ECI name is very different (e.g. aliases/typos)
                if not db_candidate and eci_party_code:
                    party_matches = [
                        c for c in all_db_candidates
                        if c.party and c.party.code == eci_party_code
                    ]
                    if len(party_matches) == 1:
                        db_candidate = party_matches[0]

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
            is_confirmed=bool(db_candidate),  # auto-confirmed if matched
            is_nota=is_nota,
        )

    # Update match_status
    total_real = sum(1 for c in scrape_result["candidates"] if not c["is_nota"])
    if matched_count == total_real:
        raw.match_status = "MATCHED"
        raw.save()
        
        # Auto-commit
        from core.api.scraper_views import _execute_commit
        _execute_commit(raw)
    elif matched_count > 0:
        raw.match_status = "PARTIAL"
        raw.save()
    else:
        raw.save()

    return raw


def _normalise(name):
    """Lowercase, strip extra spaces — for fuzzy name comparison."""
    return " ".join(name.lower().strip().split())


# ─── VIEWS ───────────────────────────────────────────────────────────────────

@staff_member_required
def scraper_dashboard(request):
    """
    Main scraper dashboard.
    Shows all constituencies with their latest scrape status.
    """
    constituencies = Constituency.objects.select_related("district").order_by("number")

    # Annotate with latest scrape info
    for c in constituencies:
        latest = c.eci_raw_results.first()  # ordered by -scraped_at
        c.latest_scrape = latest

    # Summary stats
    total = constituencies.count()
    scraped = ECIScrapeRaw.objects.values("constituency").distinct().count()
    pending = ECIScrapeRaw.objects.filter(match_status="PENDING").count()
    committed = ECIScrapeRaw.objects.filter(match_status="MATCHED").count()

    # Determine if we're in test mode
    use_test_mode = request.session.get("eci_test_mode", True)

    context = {
        "title": "ECI Results Scraper",
        "constituencies": constituencies,
        "total": total,
        "scraped": scraped,
        "pending_match": pending,
        "committed": committed,
        "use_test_mode": use_test_mode,
        "opts": {"app_label": "core"},  # for admin breadcrumbs
    }
    return render(request, "admin/eci_scraper/dashboard.html", context)


@staff_member_required
@require_POST
def scraper_run(request):
    """
    Trigger a scrape. POST params:
      ac_number: int or 'all'
      test_mode: '1' or '0'
    """
    ac_param = request.POST.get("ac_number", "")
    test_mode = request.POST.get("test_mode", "1") == "1"

    # Save mode preference in session
    request.session["eci_test_mode"] = test_mode

    base_url = BIHAR_TEST_BASE_URL if test_mode else ECI_BASE_URL
    state_code = BIHAR_STATE_CODE if test_mode else KERALA_STATE_CODE

    if ac_param == "all":
        # Run all in a background thread so admin doesn't time out
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
        messages.success(request, "Scraping all constituencies in background. Refresh in a few minutes.")

    else:
        if not ac_param:
            messages.success(request, f"Mode switched to {'Bihar Test' if test_mode else 'Kerala Live'}.")
            return redirect("eci_scraper_dashboard")

        try:
            ac_number = int(ac_param)
        except (ValueError, TypeError):
            messages.error(request, f"Invalid AC number: {ac_param}")
            return redirect("eci_scraper_dashboard")

        result = scrape_constituency(ac_number, base_url=base_url, state_code=state_code)

        if not result["success"]:
            messages.error(request, f"Scrape failed for AC {ac_number}: {result['error']}")
            return redirect("eci_scraper_dashboard")

        raw = _save_scrape_to_db(ac_number, result)
        if raw:
            status_label = {
                "MATCHED": "✅ All candidates auto-matched",
                "PARTIAL": "⚠️ Some candidates need manual matching",
                "PENDING": "⏳ Needs manual matching",
            }.get(raw.match_status, "")
            messages.success(
                request,
                f"Scraped AC {ac_number} ({result['constituency_name']}) — "
                f"Round {result['rounds_completed']}/{result['total_rounds']} — {status_label}"
            )
            # If partial/pending, redirect to match view
            if raw.match_status != "MATCHED":
                return redirect("eci_scraper_match", scrape_id=raw.id)
        else:
            messages.error(request, f"AC {ac_number} not found in database. Import constituencies first.")

    return redirect("eci_scraper_dashboard")


@staff_member_required
def scraper_match(request, scrape_id):
    """
    Name-matching view for a single scrape.
    Shows ECI names side-by-side with DB candidates for manual confirmation.
    """
    raw = get_object_or_404(ECIScrapeRaw, id=scrape_id)
    constituency = raw.constituency

    # All candidates in DB for this constituency
    db_candidates = Candidate.objects.filter(constituency=constituency).select_related("party")

    # All match records for this scrape
    matches = raw.matches.select_related("candidate", "candidate__party").order_by("-eci_total_votes")

    context = {
        "title": f"Match Results — {constituency.name}",
        "raw": raw,
        "constituency": constituency,
        "matches": matches,
        "db_candidates": db_candidates,
        "opts": {"app_label": "core"},
    }
    return render(request, "admin/eci_scraper/match.html", context)


@staff_member_required
@require_POST
def scraper_save_matches(request, scrape_id):
    """
    Save manually selected matches. POST params:
      match_{match_id}: candidate_id (or 'nota' or 'skip')
    """
    raw = get_object_or_404(ECIScrapeRaw, id=scrape_id)

    updated = 0
    for key, value in request.POST.items():
        if not key.startswith("match_"):
            continue
        try:
            match_id = int(key.replace("match_", ""))
            match = ECICandidateMatch.objects.get(id=match_id, scrape=raw)
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

    # Recompute match status
    all_matches = raw.matches.filter(is_nota=False)
    confirmed = all_matches.filter(is_confirmed=True).count()
    total = all_matches.count()

    if confirmed == total:
        raw.match_status = "MATCHED"
    elif confirmed > 0:
        raw.match_status = "PARTIAL"
    raw.save()

    messages.success(request, f"Saved {updated} matches for {raw.constituency.name}.")

    if raw.match_status == "MATCHED":
        return redirect("eci_scraper_commit", scrape_id=raw.id)

    return redirect("eci_scraper_match", scrape_id=raw.id)


@staff_member_required
def scraper_commit(request, scrape_id):
    """
    Preview + confirm writing matched results to Candidate / LiveResult tables.
    GET:  show preview of what will change
    POST: execute the commit
    """
    raw = get_object_or_404(ECIScrapeRaw, id=scrape_id)
    matches = raw.matches.filter(is_confirmed=True, is_nota=False).select_related("candidate", "candidate__party")

    if request.method == "POST":
        committed = 0
        live, _ = LiveResult.objects.get_or_create(constituency=raw.constituency)
        
        for match in matches:
            if not match.candidate:
                continue
            c = match.candidate
            c.votes = match.eci_total_votes
            
            # Use votes_polled as denominator if available, otherwise fallback to ECI's percentage
            if live.votes_polled and live.votes_polled > 0:
                c.vote_percentage = (c.votes / live.votes_polled) * 100
            else:
                c.vote_percentage = match.eci_vote_percentage
                
            c.is_leading = match.eci_is_leading
            c.is_winner = raw.is_final and match.eci_is_leading
            c.save()
            committed += 1

        live.rounds_completed = raw.rounds_completed
        live.status = "RESULT_DECLARED" if raw.is_final else "IN_PROGRESS"
        
        # Calculate total counted votes
        total_counted = sum(match.eci_total_votes for match in matches if match.candidate)
        live.votes_counted = total_counted
        live.valid_votes = total_counted
        live.save()

        raw.match_status = "MATCHED"
        raw.save()

        # Push to RTDB
        from firebase_rtdb import push_constituency, update_rtdb_meta
        rtdb_candidates = [
            {
                "name": c.name,
                "party": c.party.code if c.party else "",
                "votes": c.votes
            }
            for c in Candidate.objects.filter(constituency=raw.constituency).select_related("party").order_by('-votes')
        ]
        rtdb_data = {
            "status": live.status,
            "rounds_completed": live.rounds_completed,
            "total_rounds": raw.total_rounds,
            "last_updated": timezone.now().isoformat(),
            "candidates": rtdb_candidates,
            "votes_counted": live.votes_counted,
            "valid_votes": live.valid_votes,
            "total_electors": live.total_electors,
            "votes_polled": live.votes_polled,
            "rejected_votes": live.rejected_votes
        }
        push_constituency(raw.constituency.number, rtdb_data)
        update_rtdb_meta()

        messages.success(
            request,
            f"✅ Committed {committed} candidate results for {raw.constituency.name}. "
            f"Round {raw.rounds_completed}/{raw.total_rounds}."
        )
        return redirect("eci_scraper_dashboard")

    context = {
        "title": f"Commit Results — {raw.constituency.name}",
        "raw": raw,
        "matches": matches,
        "opts": {"app_label": "core"},
    }
    return render(request, "admin/eci_scraper/commit.html", context)


@staff_member_required
@require_POST
def scraper_stop(request):
    """Signals the background scrape thread to stop."""
    from django.core.cache import cache
    cache.set("stop_scrape", True, 3600)
    messages.success(request, "⏹ Scrape stop requested.")
    return redirect("eci_scraper_dashboard")


# ─── URL CONF ─────────────────────────────────────────────────────────────────

scraper_urls = [
    path("admin/scrape/",                              scraper_dashboard,    name="eci_scraper_dashboard"),
    path("admin/scrape/run/",                          scraper_run,          name="eci_scraper_run"),
    path("admin/scrape/stop/",                         scraper_stop,         name="eci_scraper_stop"),
    path("admin/scrape/match/<int:scrape_id>/",        scraper_match,        name="eci_scraper_match"),
    path("admin/scrape/match/<int:scrape_id>/save/",   scraper_save_matches, name="eci_scraper_save_matches"),
    path("admin/scrape/commit/<int:scrape_id>/",       scraper_commit,       name="eci_scraper_commit"),
]

