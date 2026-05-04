import os
import json
import logging
import firebase_admin
from firebase_admin import credentials, db
from django.conf import settings

logger = logging.getLogger(__name__)

# Cache file path
CACHE_FILE = os.path.join(settings.BASE_DIR, 'rtdb_cache.json')

# Initialize Firebase App
def init_firebase():
    if not firebase_admin._apps:
        cred_path = os.path.join(settings.BASE_DIR, 'firebase-service-account.json')
        if not os.path.exists(cred_path):
            logger.error(f"Firebase credentials not found at {cred_path}")
            return False
        
        try:
            cred = credentials.Certificate(cred_path)
            # Use the correct database URL from your Firebase project
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://kl-2026-default-rtdb.asia-southeast1.firebasedatabase.app/'
            })
            logger.info("Firebase Admin initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin: {e}")
            return False
    return True

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading RTDB cache: {e}")
    return {"meta": {}, "live": {}}

def save_cache(cache_data):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving RTDB cache: {e}")

def has_constituency_changed(ac_number, new_data, cache):
    str_ac = str(ac_number)
    if str_ac not in cache["live"]:
        return True
    
    cached_data = cache["live"][str_ac]
    
    # Check top-level fields
    for field in ['status', 'rounds_completed', 'total_rounds']:
        if new_data.get(field) != cached_data.get(field):
            return True
            
    # Check candidates (assuming list order or comparing by name/party)
    new_candidates = new_data.get('candidates', [])
    cached_candidates = cached_data.get('candidates', [])
    
    if len(new_candidates) != len(cached_candidates):
        return True
        
    for i in range(len(new_candidates)):
        nc = new_candidates[i]
        cc = cached_candidates[i]
        if nc.get('votes') != cc.get('votes') or nc.get('name') != cc.get('name'):
            return True
            
    return False

def push_constituency(ac_number, data):
    if not init_firebase():
        return False
        
    cache = load_cache()
    
    if not has_constituency_changed(ac_number, data, cache):
        logger.debug(f"[AC {ac_number}] No change -> skipped")
        return False # Indicated it was skipped, not an error
        
    try:
        ref = db.reference(f'/live/{ac_number}')
        ref.set(data)
        logger.info(f"[AC {ac_number}] Changed -> pushed")
        
        # Update cache
        cache["live"][str(ac_number)] = data
        save_cache(cache)
        return True
    except Exception as e:
        logger.error(f"[AC {ac_number}] Push failed: {e}")
        return False

def push_meta(summary_data):
    if not init_firebase():
        return False
        
    cache = load_cache()
    
    # Simple dict equality check for meta
    # if summary_data == cache.get("meta", {}):
    #     logger.debug("Meta: No change -> skipped")
    #     return False
        
    try:
        ref = db.reference('/meta')
        ref.set(summary_data)
        logger.info("Meta updated -> pushed")
        
        cache["meta"] = summary_data
        save_cache(cache)
        return True
    except Exception as e:
        logger.error(f"Meta Push failed: {e}")
        return False

def update_rtdb_meta():
    """
    Computes the state summary directly from the DB and pushes to RTDB /meta.
    Matches the exact structure expected by the frontend useStateSummary hook.
    """
    from django.db.models import Sum
    from django.utils import timezone
    from core.models import Constituency, Candidate, LiveResult

    live_results = LiveResult.objects.all()
    candidates = Candidate.objects.select_related('party', 'party__alliance')

    alliance_seats = {
        'UDF': {'won': 0, 'leading': 0, 'trailing': 0},
        'LDF': {'won': 0, 'leading': 0, 'trailing': 0},
        'NDA': {'won': 0, 'leading': 0, 'trailing': 0},
        'OTH': {'won': 0, 'leading': 0, 'trailing': 0},
    }
    ind_summary = {'won': 0, 'leading': 0}

    for constituency in Constituency.objects.all():
        top_candidates = constituency.candidates_2026.select_related('party', 'party__alliance').order_by('-votes')[:2]
        if top_candidates:
            leader = top_candidates[0]
            alliance = leader.party.alliance.code if leader.party and leader.party.alliance else 'OTH'
            party_code = leader.party.code if leader.party else 'IND'

            result = constituency.live_results.first()
            if result and result.status == 'RESULT_DECLARED':
                if alliance in alliance_seats:
                    alliance_seats[alliance]['won'] += 1
                else:
                    alliance_seats['OTH']['won'] += 1
                if party_code == 'IND':
                    ind_summary['won'] += 1
            elif result and result.status == 'IN_PROGRESS' and leader.votes > 0:
                if alliance in alliance_seats:
                    alliance_seats[alliance]['leading'] += 1
                else:
                    alliance_seats['OTH']['leading'] += 1
                if party_code == 'IND':
                    ind_summary['leading'] += 1

    total_votes_counted = candidates.aggregate(Sum('votes'))['votes__sum'] or 0

    # Aggregate votes per alliance
    for c in candidates:
        alliance = c.party.alliance.code if c.party and c.party.alliance else 'OTH'
        bucket = alliance if alliance in alliance_seats else 'OTH'
        alliance_seats[bucket]['votes'] = alliance_seats[bucket].get('votes', 0) + c.votes

    # Calculate vote share
    for al in alliance_seats:
        votes = alliance_seats[al].get('votes', 0)
        alliance_seats[al]['vote_share'] = (votes / total_votes_counted * 100) if total_votes_counted > 0 else 0
        alliance_seats[al].pop('votes', None)

    summary = {
        'timestamp': timezone.now().isoformat(),
        'total_constituencies': 140,
        'results_declared': live_results.filter(status='RESULT_DECLARED').count(),
        'counting_in_progress': live_results.filter(status='IN_PROGRESS').count(),
        'not_started': live_results.filter(status='NOT_STARTED').count(),
        'alliance_summary': alliance_seats,
        'ind_summary': ind_summary,
        'total_votes_counted': total_votes_counted,
        'total_votes_polled': live_results.aggregate(Sum('votes_polled'))['votes_polled__sum'] or 0,
    }
    push_meta(summary)
