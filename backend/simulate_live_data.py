#!/usr/bin/env python
"""
simulate_live_data.py
=====================
Simulates Kerala election results trickling in over 60 minutes.

Run from the /backend directory:
    python simulate_live_data.py

What it does:
  - All 140 constituencies start counting within the first 15 minutes
  - Each constituency has 18-24 counting rounds
  - Votes accumulate round-by-round with realistic noise
  - Results are declared between minute 45 and minute 58
  - Winner is determined by highest final vote share
"""

import os
import sys
import random
import time
from datetime import datetime

# ── Django setup ─────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Load .env manually (manage.py does this automatically; standalone scripts don't)
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

from django.db import transaction
from core.models import Constituency, Candidate, LiveResult

# ── Config ────────────────────────────────────────────────────────────────────
TOTAL_SECONDS   = 3600        # 1 hour
MAX_START       = 900         # all counting begins within first 15 min
MIN_DECLARE     = 2700        # earliest result: 45 min
MAX_DECLARE     = 3480        # latest result:   58 min
MIN_ROUNDS      = 18
MAX_ROUNDS      = 24
SEED            = 42

random.seed(SEED)


# ── Vote generation ───────────────────────────────────────────────────────────
def generate_votes(candidates):
    """
    Generate a realistic final vote distribution.
    Returns (final_votes dict, total_electors, total_valid, winner_id).
    """
    n = len(candidates)
    if n == 0:
        return {}, 0, 0, None

    total_electors = random.randint(160_000, 260_000)
    turnout        = random.uniform(0.64, 0.78)
    total_valid    = int(total_electors * turnout)

    # Give random "power scores" to each candidate, then heavily boost 2
    scores = [random.uniform(0.5, 1.5) for _ in range(n)]
    # Pick winner and runner-up indices
    w, r = random.sample(range(n), 2)
    scores[w] *= random.uniform(3.0, 5.5)   # winner
    scores[r] *= random.uniform(1.8, 3.2)   # runner-up

    total = sum(scores)
    shares = [s / total for s in scores]

    final_votes = {c.id: int(total_valid * sh) for c, sh in zip(candidates, shares)}
    winner_id   = candidates[shares.index(max(shares))].id

    return final_votes, total_electors, total_valid, winner_id


def partial_votes(final, pct):
    """Return partial count at `pct` completion with slight noise."""
    noise = random.uniform(0.93, 1.07)
    return max(0, int(final * pct * noise))


# ── Event processing ──────────────────────────────────────────────────────────
def process_start(const_id, s):
    LiveResult.objects.update_or_create(
        constituency_id=const_id,
        defaults={
            'status':          'IN_PROGRESS',
            'total_electors':  s['total_electors'],
            'votes_polled':    int(s['total_valid'] * random.uniform(0.96, 1.00)),
            'votes_counted':   0,
            'valid_votes':     s['total_valid'],
            'rounds_completed': 0,
            'total_rounds':    s['total_rounds'],
        }
    )
    Candidate.objects.filter(constituency_id=const_id).update(
        votes=0, is_winner=False, vote_percentage=0
    )
    print(f"  ▶  [{now()}] {s['name']:30s}  counting started"
          f"  ({s['total_rounds']} rounds)")
    # Apply round 1 immediately so votes show right away in the UI
    process_round(const_id, s, 1)


def process_round(const_id, s, round_num):
    pct        = round_num / s['total_rounds']
    candidates = list(Candidate.objects.filter(constituency_id=const_id))

    cur_votes = {}
    for c in candidates:
        fv         = s['final_votes'].get(c.id, 0)
        cv         = partial_votes(fv, pct)
        cur_votes[c.id] = cv
        c.votes    = cv
        c.vote_percentage = round(cv / s['total_valid'] * 100, 2) if s['total_valid'] else 0

    Candidate.objects.bulk_update(candidates, ['votes', 'vote_percentage'])
    LiveResult.objects.filter(constituency_id=const_id).update(
        rounds_completed=round_num,
        votes_counted=int(s['total_valid'] * pct),
    )

    # Print every 5 rounds or at the end
    if round_num % 5 == 0 or round_num == s['total_rounds']:
        leader    = sorted_cands[0]
        margin    = cur_votes[sorted_cands[0].id] - cur_votes[sorted_cands[1].id] if len(sorted_cands) > 1 else 0
        print(f"  ⟳  [{now()}] {s['name']:30s}  R{round_num:2d}/{s['total_rounds']}"
              f"  {pct*100:3.0f}%  leader +{margin:,}")


def process_declare(const_id, s):
    candidates = list(Candidate.objects.filter(constituency_id=const_id))
    for c in candidates:
        fv              = s['final_votes'].get(c.id, 0)
        c.votes         = fv
        c.vote_percentage = round(fv / s['total_valid'] * 100, 2) if s['total_valid'] else 0
        c.is_winner = (c.id == s['winner_id'])
    Candidate.objects.bulk_update(
        candidates, ['votes', 'vote_percentage', 'is_winner']
    )
    LiveResult.objects.filter(constituency_id=const_id).update(
        status='RESULT_DECLARED',
        rounds_completed=s['total_rounds'],
        votes_counted=s['total_valid'],
    )
    winner_name = next((c.name for c in candidates if c.id == s['winner_id']), '?')
    winner_votes = s['final_votes'].get(s['winner_id'], 0)
    print(f"  ✓  [{now()}] {s['name']:30s}  DECLARED  {winner_name} ({winner_votes:,})")


def now():
    return datetime.now().strftime('%H:%M:%S')


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("  Kerala Elections 2026 — Live Data Simulator")
    print(f"  Duration: {TOTAL_SECONDS // 60} minutes  |  Seed: {SEED}")
    print("=" * 65)

    constituencies = list(Constituency.objects.all().order_by('number'))
    if not constituencies:
        print("ERROR: No constituencies found. Aborting.")
        return

    # ── Pre-generate vote targets and event timeline ──────────────────
    state  = {}
    events = []

    for const in constituencies:
        candidates = list(const.candidates_2026.select_related('party').all())
        if not candidates:
            print(f"  SKIP {const.name} — no candidates found")
            continue

        final_votes, total_electors, total_valid, winner_id = generate_votes(candidates)
        total_rounds  = random.randint(MIN_ROUNDS, MAX_ROUNDS)
        start_offset  = random.randint(0, MAX_START)
        declare_offset = random.randint(MIN_DECLARE, MAX_DECLARE)
        round_interval = (declare_offset - start_offset) / total_rounds

        state[const.id] = {
            'name':          const.name,
            'final_votes':   final_votes,
            'total_electors': total_electors,
            'total_valid':   total_valid,
            'winner_id':     winner_id,
            'total_rounds':  total_rounds,
        }

        events.append({'ts': start_offset,         'cid': const.id, 'action': 'start'})
        for r in range(1, total_rounds + 1):
            events.append({'ts': int(start_offset + r * round_interval),
                           'cid': const.id, 'action': 'round', 'r': r})
        events.append({'ts': declare_offset + 45,  'cid': const.id, 'action': 'declare'})

    events.sort(key=lambda e: e['ts'])

    print(f"  {len(constituencies)} constituencies  |  {len(events)} events queued")
    print(f"  Starting at {now()}")
    print("-" * 65)

    declared = 0
    script_start = time.time()

    for event in events:
        # Wait until this event's scheduled time
        wait = (script_start + event['ts']) - time.time()
        if wait > 0:
            time.sleep(wait)

        cid    = event['cid']
        action = event['action']
        s      = state[cid]

        with transaction.atomic():
            if action == 'start':
                process_start(cid, s)
            elif action == 'round':
                process_round(cid, s, event['r'])
            elif action == 'declare':
                process_declare(cid, s)
                declared += 1
                elapsed = (time.time() - script_start) / 60
                print(f"         → {declared}/140 declared  ({elapsed:.1f} min elapsed)")

    print("-" * 65)
    print(f"  Simulation complete at {now()}  |  {declared} results declared")
    print("=" * 65)


if __name__ == '__main__':
    main()
