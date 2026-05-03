"""
Build the corrected tally from CSV ground truth.

Strategy:
- For each alliance, count seats where a RECOGNIZED ECI party code appears in the CSV.
- All remaining alliance seats (where the candidate was IND in CSV but actually a small
  alliance party or alliance-backed independent) are tallied as "IND_or_small_party".
- We then reconcile these against the Wikipedia tally's small-party breakdowns.

This produces the AUTHORITATIVE seats_contested numbers for the tally.
"""

import csv
import json
import os
from collections import Counter, defaultdict

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX_DIR  = os.path.dirname(os.path.abspath(__file__))

# ─── Alliance membership per year ────────────────────────────────────────────
# Maps ECI CSV party codes -> (tally_party_id, alliance)
# Only parties with their OWN ECI code are listed here.
# Parties that contested as IND in ECI data are NOT listed.

ALLIANCE_MAP_2011 = {
    # UDF
    'INC':     ('INC',    'UDF'),
    'MUL':     ('IUML',   'UDF'),
    'KEC(M)':  ('KC_M',   'UDF'),
    'SJD':     ('SJD',    'UDF'),
    'JPSS':    ('JSS',    'UDF'),
    'RSP':     ('RSP',    'UDF'),
    'CMPKSC':  ('CMP',    'UDF'),
    'KEC(J)':  ('KC_J',   'UDF'),
    'KEC(B)':  ('KC_B',   'UDF'),
    'KRSP':    ('RSP_BJ', 'UDF'),
    # LDF
    'CPM':     ('CPI_M',  'LDF'),
    'CPI':     ('CPI',    'LDF'),
    'JD(S)':   ('JD_S',   'LDF'),
    'NCP':     ('NCP',    'LDF'),
    'INL':     ('INL',    'LDF'),
    'KC(AMG)': ('KC_AMG', 'LDF'),
    # Note: CON_S (Congress Secular) has no ECI code in 2011; its candidate appears as IND
    # NDA
    'BJP':     ('BJP',    'NDA'),
    'JD(U)':   ('JD_U',   'NDA'),
}

ALLIANCE_MAP_2016 = {
    # UDF
    'INC':     ('INC',    'UDF'),
    'IUML':    ('IUML',   'UDF'),
    'KEC(M)':  ('KC_M',   'UDF'),
    'JD(U)':   ('JD_U',   'UDF'),
    'RSP':     ('RSP',    'UDF'),
    'CMPKSC':  ('CMP',    'UDF'),
    'KEC(J)':  ('KC_J',   'UDF'),
    # LDF
    'CPM':     ('CPI_M',  'LDF'),
    'CPI':     ('CPI',    'LDF'),
    'JD(S)':   ('JD_S',   'LDF'),
    'NCP':     ('NCP',    'LDF'),
    'INL':     ('INL',    'LDF'),
    'KEC(B)':  ('KC_B',   'LDF'),
    'C(S)':    ('CON_S',  'LDF'),
    'NSC':     ('NSC',    'LDF'),
    'KCST':    ('KC_KST', 'LDF'),
    # Note: JKC, JSS, CMA, RSP_L all contested as IND in ECI data
    # Note: KC_T, JRS, JSS_RB (NDA) also contested as IND in ECI data
    # NDA
    'BJP':     ('BJP',    'NDA'),
    'BDJS':    ('BDJS',   'NDA'),
}

ALLIANCE_MAP_2021 = {
    # UDF
    'INC':     ('INC',    'UDF'),
    'IUML':    ('IUML',   'UDF'),
    'KEC':     ('KEC',    'UDF'),
    'RSP':     ('RSP',    'UDF'),
    'KEC(J)':  ('KC_J',   'UDF'),
    'CMPKSC':  ('CMP',    'UDF'),
    'RMPOI':   ('RMPI',   'UDF'),
    # Note: NCK (2 seats) contested as IND in ECI data
    # LDF
    'CPI(M)':  ('CPI_M',  'LDF'),
    'CPI':     ('CPI',    'LDF'),
    'KEC(M)':  ('KC_M',   'LDF'),
    'JD(S)':   ('JD_S',   'LDF'),
    'NCP':     ('NCP',    'LDF'),
    'RJD':     ('RJD',    'LDF'),
    'INL':     ('INL',    'LDF'),
    'C(S)':    ('CON_S',  'LDF'),
    'KEC(B)':  ('KC_B',   'LDF'),
    'JKC':     ('JKC',    'LDF'),
    # NDA
    'BJP':     ('BJP',    'NDA'),
    'BDJS':    ('BDJS',   'NDA'),
    'ADMK':    ('AIADMK', 'NDA'),
    # Note: KKC, JRP contested as IND in ECI data
}


def analyze_year(year, csv_path, party_col, const_col, alliance_map):
    """
    For each constituency, determine which alliance each candidate belongs to.
    Count recognized-party seats and IND seats per alliance.
    """
    # Read CSV
    f = open(csv_path, 'r', encoding='utf-8-sig')
    reader = csv.DictReader(f)
    
    # Build: constituency -> {party_code: candidate_name}
    const_data = defaultdict(dict)  # const_no -> {party: candidate_name}
    const_names = {}
    for row in reader:
        p = row[party_col].strip()
        c = int(row[const_col].strip())
        cand = row.get('candidate_name', row.get('Candidate Name', '')).strip()
        const_names[c] = row.get('constituency_name', row.get('Constituency Name', '')).strip()
        if p and p != 'NOTA':
            const_data[c][p] = cand
    f.close()
    
    # For each constituency, find which alliances have a recognized party
    alliance_party_seats = defaultdict(Counter)  # alliance -> Counter(tally_id -> count)
    alliance_consts = defaultdict(set)           # alliance -> set of const_nos covered
    
    for c, parties in const_data.items():
        for csv_code, cand_name in parties.items():
            if csv_code in alliance_map:
                tally_id, alliance = alliance_map[csv_code]
                alliance_party_seats[alliance][tally_id] += 1
                alliance_consts[alliance].add(c)
    
    # Find constituencies where an alliance has NO recognized party -> those are IND seats
    all_consts = set(const_data.keys())
    
    print(f"\n{'='*80}")
    print(f"  {year} - CSV GROUND TRUTH ANALYSIS")
    print(f"{'='*80}")
    
    results = {}  # alliance -> {party_id: seats, 'IND': seats}
    
    for alliance in ['UDF', 'LDF', 'NDA']:
        covered = alliance_consts.get(alliance, set())
        missing = all_consts - covered
        
        # Among missing, some are IND (alliance-backed) and some are just not contested
        # We need the IND candidates from those constituencies
        ind_in_missing = []
        for c in sorted(missing):
            if 'IND' in const_data[c]:
                ind_in_missing.append((c, const_names[c]))
        
        print(f"\n--- {alliance} ---")
        print(f"  Recognised party seats: {len(covered)}")
        for tally_id in sorted(alliance_party_seats[alliance]):
            count = alliance_party_seats[alliance][tally_id]
            print(f"    {tally_id:<15} = {count}")
        
        print(f"  Constituencies with NO {alliance} recognised party: {len(missing)}")
        print(f"  Of those, {len(ind_in_missing)} have IND candidates (potential alliance-backed):")
        for c, name in ind_in_missing:
            ind_cand = const_data[c].get('IND', '?')
            # There could be multiple IND candidates; we just note the constituency
            print(f"    #{c:3d} {name}")
        
        total_with_ind = len(covered) + len(ind_in_missing)
        print(f"  >> TOTAL (recognised + potential IND): {total_with_ind}")
        
        results[alliance] = {
            'party_seats': dict(alliance_party_seats[alliance]),
            'recognised_total': len(covered),
            'ind_potential': len(ind_in_missing),
            'combined_total': total_with_ind,
            'missing_constituencies': sorted(missing),
            'ind_constituencies': [c for c, _ in ind_in_missing],
        }
    
    return results


def main():
    print("BUILDING CORRECTED TALLY FROM CSV GROUND TRUTH")
    print("=" * 60)
    
    all_results = {}
    
    r2011 = analyze_year(
        2011,
        os.path.join(DATA_DIR, '2011_candidates.csv'),
        'party', 'constituency_no',
        ALLIANCE_MAP_2011,
    )
    all_results['2011'] = r2011
    
    r2016 = analyze_year(
        2016,
        os.path.join(DATA_DIR, '2016_candinates.csv'),
        ' Party Name', 'Constituency No.',
        ALLIANCE_MAP_2016,
    )
    all_results['2016'] = r2016
    
    r2021 = analyze_year(
        2021,
        os.path.join(DATA_DIR, '2021_candinates.csv'),
        'party', 'constituency_no',
        ALLIANCE_MAP_2021,
    )
    all_results['2021'] = r2021
    
    # Final summary
    print(f"\n\n{'='*80}")
    print("  CORRECTED TALLY SUMMARY")
    print(f"{'='*80}")
    print(f"\n{'Year':<6} {'Alliance':<8} {'Recognised':<12} {'IND/Small':<12} {'Total':<8} {'Expected'}")
    print("-" * 60)
    
    for year in ['2011', '2016', '2021']:
        for alliance in ['UDF', 'LDF', 'NDA']:
            r = all_results[year][alliance]
            expected = 140 if not (year == '2021' and alliance == 'NDA') else 138
            total = r['combined_total']
            status = "OK" if total == expected else f"** ({total - expected:+d})"
            print(f"{year:<6} {alliance:<8} {r['recognised_total']:<12} {r['ind_potential']:<12} {total:<8} {expected} {status}")
    
    # Output the corrected data as JSON for easy consumption
    corrected = {}
    for year in ['2011', '2016', '2021']:
        corrected[year] = {}
        for alliance in ['UDF', 'LDF', 'NDA']:
            r = all_results[year][alliance]
            entry = dict(r['party_seats'])
            if r['ind_potential'] > 0:
                entry['IND'] = r['ind_potential']
            corrected[year][alliance] = entry
    
    outpath = os.path.join(FIX_DIR, 'corrected_tally_from_csv.json')
    with open(outpath, 'w') as f:
        json.dump(corrected, f, indent=2)
    print(f"\nCorrected tally written to: {outpath}")


if __name__ == '__main__':
    main()
