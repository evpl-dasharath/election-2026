"""
Validate kerala_elections_tally.json against actual CSV data.

For each election year (2011, 2016, 2021), counts unique candidates per party
from the CSV files and compares against the tally's claimed seats_contested.

Uses the ECI party abbreviation mappings from:
  - "2011, 2021 party names and code.txt"
  - "2016 party names and code.csv"
to map CSV abbreviations → tally party_ids.
"""

import csv
import json
import os
from collections import Counter

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX_DIR  = os.path.dirname(os.path.abspath(__file__))

# ─── Abbreviation mapping: CSV party code → tally party_id ────────────────────
# The CSV files use ECI abbreviations (e.g. CPM, MUL, KEC(M))
# The tally uses normalised IDs (e.g. CPI_M, IUML, KC_M)

CSV_TO_TALLY_2011 = {
    "INC":       "INC",
    "MUL":       "IUML",      # 2011 ECI code for Muslim League
    "CPM":       "CPI_M",
    "CPI":       "CPI",
    "BJP":       "BJP",
    "NCP":       "NCP",
    "JD(S)":     "JD_S",
    "JD(U)":     "JD_U",
    "JPSS":      "JSS",       # Janadhipathya Samrakshana Samithi
    "KC(AMG)":   "KC_AMG",
    "KEC(M)":    "KC_M",      # Kerala Congress (M)
    "RSP":       "RSP",
    "CMPKSC":    "CMP",       # Communist Marxist Party Kerala State Committee
    "INL":       "INL",
    "KEC(B)":    "KC_B",      # Kerala Congress (B)
    "KEC(J)":    "KC_J",      # Kerala Congress (Jacob)
    "KRSP":      "RSP_BJ",    # Kerala Revolutionary Socialist Party (Baby John)
    "SJD":       "SJD",       # Socialist Janata (Democratic)
    "AIADMK":    "AIADMK",
    "LJP":       "LJP",
    "SHS":       "SHS",
    "BSP":       "BSP",
    "IND":       "IND",
    # Less common / small parties
    "DPSP":      "DPSP",
    "KJ":        "KJ",
    "PDP":       "PDP",
    "SDPI":      "SDPI",
    "SLAP":      "SLAP",
    "SUCI":      "SUCI",
    "SWJP":      "SWJP",
    "CPI(ML)(L)":"CPI_ML_L",
    # Congress (Secular) - 2011 ECI code unknown, check CSV
    "C(S)":      "CON_S",
}

CSV_TO_TALLY_2016 = {
    "INC":       "INC",
    "IUML":      "IUML",
    "CPM":       "CPI_M",     # 2016 still uses CPM
    "CPI":       "CPI",
    "BJP":       "BJP",
    "NCP":       "NCP",
    "JD(S)":     "JD_S",
    "JD(U)":     "JD_U",
    "RSP":       "RSP",
    "KEC(M)":    "KC_M",
    "BDJS":      "BDJS",
    "INL":       "INL",
    "KEC(B)":    "KC_B",
    "KEC(J)":    "KC_J",
    "CMPKSC":    "CMP",
    "C(S)":      "CON_S",
    "ADMK":      "AIADMK",    # 2016 uses ADMK
    "SHS":       "SHS",
    "BSP":       "BSP",
    "IND":       "IND",
    "NSC":       "NSC",
    "KCS":       "KCS",       # Kerala Congress Secular — separate party, NOT Skaria Thomas
    "KCST":      "KC_KST",    # Kerala Congress (Skariah Thomas) — direct match
    "KEC":       "KEC",       # Kerala Congress (generic)
    "SDPI":      "SDPI",
    "SUCI":      "SUCI",
    "MCPI":      "MCPI",
    "PDP":       "PDP",
    "AKTP":      "AKTP",
    "APoI":      "APoI",
    "CPI(ML)(L)":"CPI_ML_L",
    "CPIM":      "CPI_ML_RS", # CPI(ML) Red Star — NOT CPI(M)!
    "igp":       "igp",
    "KLJP":      "KLJP",
    "SDP":       "SDP",
    "SP":        "SP",
    "PpGP":      "PpGP",
    "WPOI":      "WPOI",
}

CSV_TO_TALLY_2021 = {
    "INC":       "INC",
    "IUML":      "IUML",
    "CPI(M)":    "CPI_M",     # 2021 uses CPI(M)
    "CPI":       "CPI",
    "BJP":       "BJP",
    "NCP":       "NCP",
    "JD(S)":     "JD_S",
    "JD(U)":     "JD_U",
    "RSP":       "RSP",
    "KEC(M)":    "KC_M",
    "BDJS":      "BDJS",
    "INL":       "INL",
    "KEC(B)":    "KC_B",
    "KEC(J)":    "KC_J",
    "CMPKSC":    "CMP",
    "C(S)":      "CON_S",
    "ADMK":      "AIADMK",
    "RJD":       "RJD",
    "SHS":       "SHS",
    "BSP":       "BSP",
    "IND":       "IND",
    "JKC":       "JKC",
    "KEC":       "KEC",       # Kerala Congress (Joseph faction)
    "NSC":       "NSC",
    "RMPOI":     "RMPI",      # Revolutionary Marxist Party of India
    "SDPI":      "SDPI",
    "SUCI":      "SUCI",
    "MCPI":      "MCPI",
    "KJPS":      "KJPS",
    "KLJP":      "KLJP",
    "LJD":       "LJD",
    "TTPty":     "TTP",
    "ABHM":      "ABHM",
    "ADHRMPI":   "ADHRMPI",
    "APoI":      "APoI",
    "BHUDRP":    "BHUDRP",
    "CPIM":      "CPI_ML_RS",
    "DHRMP":     "DHRMP",
    "DSJP":      "DSJP",
    "ICSP":      "ICSP",
    "igp":       "igp",
    "NALAP":     "NALAP",
    "NWLBRP":    "NWLBRP",
    "RPI(A)":    "RPI_A",
    "SDC":       "SDC",
    "SMFB":      "SMFB",
    "SWARAJ":    "SWARAJ",
    "SWJP":      "SWJP",
    "WPOI":      "WPOI",
}


def read_csv(filepath, party_col, constituency_col):
    """
    Read a CSV and return a Counter of {party_code: num_constituencies_contested}.
    Each candidate appears once per constituency, so we count unique (constituency, party) pairs
    to get seats contested. But actually "seats_contested" means how many constituencies
    that party fielded at least one candidate in.
    """
    party_counts = Counter()
    constituency_parties = set()  # (constituency_no, party) pairs
    
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            party = row[party_col].strip()
            const = row[constituency_col].strip()
            if party and const and party != "NOTA":
                pair = (const, party)
                if pair not in constituency_parties:
                    constituency_parties.add(pair)
                    party_counts[party] += 1
    
    return party_counts


def load_tally():
    with open(os.path.join(FIX_DIR, "kerala_elections_tally.json"), "r") as f:
        return json.load(f)


def build_tally_lookup(tally_data, year_str):
    """Build {party_id: (alliance, seats_contested)} from tally for a given year."""
    lookup = {}
    election = tally_data["elections"][year_str]
    for alliance_name, alliance_data in election["alliances"].items():
        for party in alliance_data.get("parties", []):
            pid = party["party_id"]
            sc = party["seats_contested"]
            lookup[pid] = (alliance_name, sc)
        # Independents
        ind_count = alliance_data.get("independents_backed", 0)
        if ind_count and ind_count != "TBD":
            key = f"IND_{alliance_name}"
            lookup[key] = (alliance_name, ind_count)
    return lookup


def compare(year_str, csv_path, party_col, constituency_col, csv_to_tally_map):
    print(f"\n{'='*80}")
    print(f"  ELECTION YEAR: {year_str}")
    print(f"  CSV: {os.path.basename(csv_path)}")
    print(f"{'='*80}")
    
    tally_data = load_tally()
    tally_lookup = build_tally_lookup(tally_data, year_str)
    
    csv_counts = read_csv(csv_path, party_col, constituency_col)
    
    # Map CSV counts to tally IDs
    mapped_counts = {}
    unmapped = {}
    for csv_code, count in csv_counts.items():
        tally_id = csv_to_tally_map.get(csv_code)
        if tally_id:
            mapped_counts[tally_id] = mapped_counts.get(tally_id, 0) + count
        else:
            unmapped[csv_code] = count
    
    # Compare
    all_tally_ids = set(tally_lookup.keys())
    all_csv_ids = set(mapped_counts.keys())
    
    # Parties in tally (skip IND_* entries for now)
    tally_party_ids = {k for k in all_tally_ids if not k.startswith("IND_")}
    
    print(f"\n--- Parties in tally with CSV comparison ---")
    print(f"{'Tally ID':<15} {'Alliance':<8} {'Tally':>6} {'CSV':>6} {'Diff':>6} {'Status'}")
    print("-" * 70)
    
    discrepancies = []
    for pid in sorted(tally_party_ids):
        alliance, tally_seats = tally_lookup[pid]
        csv_seats = mapped_counts.get(pid, 0)
        diff = csv_seats - tally_seats if isinstance(tally_seats, int) else "?"
        status = "OK" if diff == 0 else f"** MISMATCH"
        if diff != 0:
            discrepancies.append((pid, alliance, tally_seats, csv_seats, diff))
        print(f"{pid:<15} {alliance:<8} {str(tally_seats):>6} {csv_seats:>6} {str(diff):>6} {status}")
    
    # IND comparison (special handling)
    ind_csv = mapped_counts.get("IND", 0)
    ind_tally_total = 0
    for k, v in tally_lookup.items():
        if k.startswith("IND_"):
            alliance, seats = v
            ind_tally_total += seats
            print(f"{'IND ('+alliance+')':<15} {alliance:<8} {seats:>6} {'?':>6} {'?':>6} (total IND in CSV: {ind_csv})")
    
    if ind_tally_total > 0:
        print(f"{'IND TOTAL':<15} {'---':<8} {ind_tally_total:>6} {ind_csv:>6} {ind_csv - ind_tally_total:>6} {'OK' if ind_csv == ind_tally_total else '** MISMATCH'}")
    
    # Unmapped CSV parties (not in tally — these are parties not in any alliance)
    if unmapped:
        print(f"\n--- Unmapped CSV parties (no mapping to tally ID) ---")
        for code, count in sorted(unmapped.items(), key=lambda x: -x[1]):
            print(f"  {code:<20} -> {count} constituencies")
    
    # CSV parties mapped but not in tally
    extra_csv = all_csv_ids - tally_party_ids - {"IND"}
    if extra_csv:
        print(f"\n--- In CSV but NOT in tally (non-alliance parties) ---")
        for pid in sorted(extra_csv):
            print(f"  {pid:<20} -> {mapped_counts[pid]} constituencies")
    
    # Tally parties not found in CSV
    missing_from_csv = tally_party_ids - all_csv_ids
    if missing_from_csv:
        print(f"\n--- In tally but NOT found in CSV ---")
        for pid in sorted(missing_from_csv):
            alliance, seats = tally_lookup[pid]
            print(f"  {pid:<20} ({alliance}) -> tally says {seats} seats")
    
    if discrepancies:
        print(f"\n{'!'*60}")
        print(f"  TOTAL DISCREPANCIES: {len(discrepancies)}")
        for pid, alliance, tally_seats, csv_seats, diff in discrepancies:
            sign = "+" if diff > 0 else ""
            print(f"    {pid} ({alliance}): tally={tally_seats}, csv={csv_seats} ({sign}{diff})")
        print(f"{'!'*60}")
    else:
        print(f"\n  OK - All tally entries match CSV for {year_str}!")
    
    return discrepancies, unmapped


def main():
    print("KERALA ELECTIONS TALLY VALIDATION")
    print("Comparing tally.json against actual ECI CSV data\n")
    
    all_discrepancies = {}
    
    # 2011
    d, u = compare(
        "2011",
        os.path.join(DATA_DIR, "2011_candidates.csv"),
        party_col="party",
        constituency_col="constituency_no",
        csv_to_tally_map=CSV_TO_TALLY_2011,
    )
    all_discrepancies["2011"] = (d, u)
    
    # 2016
    d, u = compare(
        "2016",
        os.path.join(DATA_DIR, "2016_candinates.csv"),
        party_col=" Party Name",  # note leading space in CSV header
        constituency_col="Constituency No.",
        csv_to_tally_map=CSV_TO_TALLY_2016,
    )
    all_discrepancies["2016"] = (d, u)
    
    # 2021
    d, u = compare(
        "2021",
        os.path.join(DATA_DIR, "2021_candinates.csv"),
        party_col="party",
        constituency_col="constituency_no",
        csv_to_tally_map=CSV_TO_TALLY_2021,
    )
    all_discrepancies["2021"] = (d, u)
    
    # Summary
    print(f"\n\n{'='*80}")
    print("  SUMMARY")
    print(f"{'='*80}")
    for year, (discs, unmapped) in all_discrepancies.items():
        disc_count = len(discs)
        unmap_count = len(unmapped)
        status = "CLEAN" if disc_count == 0 and unmap_count == 0 else f"** {disc_count} mismatches, {unmap_count} unmapped"
        print(f"  {year}: {status}")


if __name__ == "__main__":
    main()
