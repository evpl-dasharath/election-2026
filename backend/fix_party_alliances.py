#!/usr/bin/env python
"""
fix_party_alliances.py
======================
Corrects Party.alliance values that are wrong or missing.
Run from /backend:
    python fix_party_alliances.py

After running, restart the dev server so serializers pick up the changes.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(_env):
    with open(_env) as _f:
        for _l in _f:
            _l = _l.strip()
            if _l and not _l.startswith('#') and '=' in _l:
                _k, _, _v = _l.partition('=')
                os.environ.setdefault(_k.strip(), _v.strip())

import django; django.setup()
from core.models import Party

# ── Correction map ────────────────────────────────────────────────────────────
# Format: 'PARTY_CODE': ('CORRECT_ALLIANCE', 'reason')
CORRECTIONS = {
    # LDF — communist / left parties clearly in LDF
    'CPIM':             ('LDF', 'CPI(M) duplicate code — definitely LDF'),
    'CPIML Liberation': ('LDF', 'CPI(ML) Liberation is LDF-aligned in Kerala'),
    'CPIML Red Star':   ('LDF', 'CPI(ML) Red Star is LDF-aligned in Kerala'),
    'LJD':              ('LDF', 'Loktantrik Janta Dal (K P Mohanan) was LDF in 2021'),
    'C(S)':             ('LDF', 'Congress(Secular) Kadannappalli faction — LDF in 2026'),
    'CONG(S)':          ('LDF', 'Congress(Secular) — LDF'),  # confirm, already LDF
    'RSP':              ('UDF', 'RSP (plain) is UDF-aligned in Kerala 2026'),
    'RSP(L)':           ('LDF', 'RSP(L) Leninist faction is LDF-aligned'),

    # NDA
    'SHS':              ('NDA', 'Shiv Sena — NDA'),
    'JD(U)':            ('NDA', 'JD(U) — NDA nationally, and in Kerala'),
    'ADMK':             ('NDA', 'ADMK was NDA ally in 2021 Kerala'),
}

print('=' * 55)
print('  Party Alliance Fix')
print('=' * 55)

updated = 0
skipped = []
for code, (correct_alliance, reason) in CORRECTIONS.items():
    try:
        p = Party.objects.get(code=code)
        old = p.alliance
        if old != correct_alliance:
            p.alliance = correct_alliance
            p.save()
            print(f'  ✓  {code:22s}  {old:5s} → {correct_alliance}  ({reason})')
            updated += 1
        else:
            print(f'  –  {code:22s}  already {correct_alliance}')
    except Party.DoesNotExist:
        skipped.append(code)

if skipped:
    print()
    print('  ⚠  Not found in DB (no candidates, safe to ignore):')
    for c in skipped:
        print(f'       {c}')

print()
print(f'  {updated} records updated.')
print('=' * 55)
