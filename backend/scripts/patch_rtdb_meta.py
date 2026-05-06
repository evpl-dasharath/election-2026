"""
Patch RTDB /meta with total_votes_polled by reading the running local Django API.
Does NOT need DB access — uses HTTP to localhost:8001 and firebase-admin directly.
"""
import json, sys, os
import requests
import firebase_admin
from firebase_admin import credentials, db as rtdb_db

RTDB_URL   = 'https://kl-2026-default-rtdb.asia-southeast1.firebasedatabase.app/'
CRED_PATH  = os.path.join(os.path.dirname(__file__), 'firebase-service-account.json')
API_URL    = 'http://localhost:8001/api/summary/'

# 1. Fetch updated summary from local API
print(f"Fetching {API_URL}...")
try:
    resp = requests.get(API_URL, timeout=5)
    resp.raise_for_status()
    api_data = resp.json()
except Exception as e:
    print(f"ERROR calling local API: {e}")
    print("Is the Django server running on port 8001?")
    sys.exit(1)

total_votes_polled  = api_data.get('total_votes_polled', 0)
total_votes_counted = api_data.get('total_votes_counted', 0)
print(f"  total_votes_counted = {total_votes_counted:,}")
print(f"  total_votes_polled  = {total_votes_polled:,}")

if total_votes_polled == 0:
    print("WARNING: total_votes_polled is 0 — DB may not have votes_polled data yet.")

# 2. Init Firebase (without Django)
if not firebase_admin._apps:
    cred = credentials.Certificate(CRED_PATH)
    firebase_admin.initialize_app(cred, {'databaseURL': RTDB_URL})

# 3. Read current /meta and patch it
meta_ref = rtdb_db.reference('/meta')
current  = meta_ref.get() or {}
current['total_votes_polled']  = total_votes_polled
current['total_votes_counted'] = total_votes_counted
meta_ref.set(current)

print(f"\nRTDB /meta patched successfully.")
print(f"  votes_polled:  {total_votes_polled:,}")
print(f"  votes_counted: {total_votes_counted:,}")
