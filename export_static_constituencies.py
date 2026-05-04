"""
export_static_constituencies.py
Regenerates frontend/src/data/constituencies.json from the Django API.
Fetches ONLY static (never-changing) fields — no status/leader/runner_up.
Run this whenever constituency metadata (sitting MP, region, etc.) changes.

Usage:
    python export_static_constituencies.py
    (requires Django server running on port 8001)
"""
import urllib.request, json, os, sys

API_URL = 'http://localhost:8001/api/constituencies/?format=json&limit=200'

# Only these fields belong in the static JSON — all live fields come from RTDB
STATIC_FIELDS = ['id', 'number', 'name', 'district', 'region', 'reserved', 'sitting_party', 'sitting_alliance', 'total_electors', 'votes_polled']

def main():
    print(f'Fetching from {API_URL} ...')
    try:
        with urllib.request.urlopen(API_URL, timeout=10) as resp:
            raw = json.loads(resp.read())
    except Exception as e:
        print(f'ERROR: Could not reach Django API: {e}')
        print('Make sure the backend is running: python manage.py runserver 8001')
        sys.exit(1)

    items = raw.get('results', raw) if isinstance(raw, dict) else raw
    cleaned = [{k: item.get(k) for k in STATIC_FIELDS} for item in items]

    # Validate — must never contain live fields
    for c in cleaned:
        for bad in ('status', 'leader', 'runner_up'):
            if bad in c:
                print(f'ERROR: live field "{bad}" leaked into {c["name"]} — check serializer!')
                sys.exit(1)

    out_path = os.path.join(
        os.path.dirname(__file__),
        'frontend', 'public', 'data', 'constituencies.json'
    )
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    # Validate coverage
    has_region = all(c.get('region') for c in cleaned)
    has_sitting = sum(1 for c in cleaned if c.get('sitting_alliance'))
    print(f'Written {len(cleaned)} constituencies -> {out_path}')
    print(f'  All have region: {has_region}')
    print(f'  Have sitting_alliance: {has_sitting} / {len(cleaned)}')
    print('  Validation: PASSED (no live fields)')

if __name__ == '__main__':
    main()
