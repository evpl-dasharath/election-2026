import os
import sys

# ── Django setup ─────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Load .env manually
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _, _v = _line.partition('=')
                os.environ.setdefault(_k.strip(), _v.strip())

import django
django.setup()

from django.utils import timezone
from core.models import Constituency
from firebase_rtdb import push_constituency, update_rtdb_meta

def main():
    print("Syncing DB to RTDB...")
    constituencies = Constituency.objects.all().order_by('number')
    for const in constituencies:
        result = const.live_results.first()
        if not result:
            continue
            
        candidates = list(const.candidates_2026.all())
        candidates.sort(key=lambda x: x.votes, reverse=True)
        
        rtdb_data = {
            "status": result.status,
            "rounds_completed": result.rounds_completed,
            "total_rounds": result.total_rounds,
            "total_electors": result.total_electors,
            "votes_polled": result.votes_polled,
            "last_updated": timezone.now().isoformat(),
            "candidates": [
                {
                    "name": c.name,
                    "party": c.party.code if c.party else "",
                    "votes": c.votes
                }
                for c in candidates
            ]
        }
        
        pushed = push_constituency(const.number, rtdb_data)
        if pushed:
            print(f"[AC {const.number}] Pushed to RTDB")
            
    print("Updating RTDB Meta...")
    update_rtdb_meta()
    print("Done!")

if __name__ == '__main__':
    main()
