#!/usr/bin/env python
"""
clear_db.py
===========
Resets all live election data while keeping the constituency/candidate
structure fully intact.

Run from the /backend directory:
    python clear_db.py

What gets cleared:
  - All Candidate votes reset to 0
  - is_leading, is_winner reset to False
  - All LiveResult records deleted
  - All DataSnapshot records deleted

What is PRESERVED:
  - Constituency records
  - Candidate records (name, party, constituency links)
  - Party records
  - All historical data (2021, 2019, 2016 results)
"""

import os
import sys

# ── Django setup ──────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Load .env (manage.py does this automatically; standalone scripts don't)
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

from core.models import Candidate, LiveResult

# ── Reset ─────────────────────────────────────────────────────────────────────
print('=' * 50)
print('  Kerala Elections 2026 — DB Reset')
print('=' * 50)

from core.models import (
    Candidate, LiveResult, DataSnapshot,
    ECIScrapeRaw, ECICandidateMatch, CandidateAlias,
)

# ── Live result data ──────────────────────────────────────────
n = Candidate.objects.update(votes=0, vote_percentage=0, is_leading=False, is_winner=False)
print(f'  OK  Reset {n} candidates (votes -> 0, flags -> False)')

lr, _ = LiveResult.objects.all().delete()
print(f'  OK  Deleted {lr} LiveResult records')

ds, _ = DataSnapshot.objects.all().delete()
print(f'  OK  Deleted {ds} DataSnapshot records')

# ── Scraper session data ──────────────────────────────────────
matches, _ = ECICandidateMatch.objects.all().delete()
print(f'  OK  Deleted {matches} ECICandidateMatch records')

raws, _ = ECIScrapeRaw.objects.all().delete()
print(f'  OK  Deleted {raws} ECIScrapeRaw records')

aliases, _ = CandidateAlias.objects.all().delete()
print(f'  OK  Deleted {aliases} CandidateAlias records')

print('=' * 50)
print('  Database is clean. Ready for a fresh run.')
print('=' * 50)

# ── Firebase RTDB wipe ────────────────────────────────────────
print()
print('  Clearing Firebase RTDB...')
try:
    from firebase_rtdb import init_firebase, push_meta
    from firebase_admin import db as rtdb_db

    if init_firebase():
        rtdb_db.reference('/live').set({})
        rtdb_db.reference('/meta').set({})
        print('  OK  RTDB /live and /meta cleared')
    else:
        print('  WARN  Firebase not initialized — skipping RTDB clear')
except Exception as e:
    print(f'  WARN  Could not clear RTDB: {e}')

print()
