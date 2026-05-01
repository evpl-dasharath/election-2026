"""
Kerala Legislative Assembly Election Data Extractor
Extracts structured candidate/constituency data from Election Commission PDFs.

Supports:
  - 2006 format: No. NAME SEX GENERAL POSTAL PARTY AGE CAT TOTAL SERIAL (one constituency per page)
  - 2011 format: NAME SEX AGE CATEGORY PARTY POSTAL TOTAL GENERAL PCT SERIAL
  - 2021 format: SERIAL NAME SEX AGE CATEGORY PARTY SYMBOL GENERAL POSTAL TOTAL PCT

The format is auto-detected from the PDF content.

Usage:
    python extract_election_data.py 2006.pdf
    python extract_election_data.py 2011.pdf
    python extract_election_data.py statistical_report.pdf
    python extract_election_data.py 2006.pdf --output results.csv
    python extract_election_data.py 2006.pdf --json

Output files (CSV):
    election_candidates.csv  - one row per candidate (incl. NOTA for 2021), with winner flag
    election_summary.csv     - one row per constituency (turnout data)

Requirements:
    pip install pypdf
"""

import re
import csv
import json
import argparse
from pathlib import Path
from collections import defaultdict


# -- PDF text extraction -------------------------------------------------------

def extract_text_from_pdf(pdf_path):
    try:
        from pypdf import PdfReader
    except ImportError:
        raise SystemExit("pypdf not found. Run: pip install pypdf")
    reader = PdfReader(pdf_path)
    return "\n".join(p.extract_text() or "" for p in reader.pages)


# -- Format detection ----------------------------------------------------------

def detect_format(text):
    """
    Returns '2006', '2011', or '2021' based on the PDF column header signature.
    """
    if "SYMBOL" in text[:3000]:
        return "2021"
    # 2006: 'No. CANDIDATE NAME SEX' header
    if re.search(r"No\.\s+CANDIDATE NAME\s+SEX", text[:3000]):
        return "2006"
    # 2011: 'POSTALTOTALGENERALVALID' in concatenated header
    if "POSTALTOTALGENERALVALID" in text[:3000].replace(" ", ""):
        return "2011"
    if re.search(r"TOTAL ELECTORS\s*:\s*\d+", text):
        return "2011"
    return "2021"


# ==============================================================================
#  2006 FORMAT PARSER
# ==============================================================================
#
# Each page = one constituency. Raw text per page (with real newlines):
#
#   No. CANDIDATE NAME SEX\n
#   VALID VOTES POLLED\n
#   TOTALAGE CATEGORY PARTY GENERAL POSTAL\n
#    DETAILED RESULTS\n
#   Election Commission of India - State Election, 2006 ...\n
#   {N}.  {CONSTITUENCY NAME}\n
#   . {NAME} M/F {GENERAL} {POSTAL}{PARTY}{AGE} {CAT} {TOTAL}{SERIAL}\n
#   ...more candidates...
#   TOTAL: {GENERAL} {POSTAL} {TOTAL}\n
#   {page_number}\n
#
# Key: PARTY is letters/brackets only (no digits).
#      AGE is exactly 2 digits concatenated directly after party.
#      TOTAL and SERIAL are concatenated (TOTAL has 5-6 digits, SERIAL 1-2).

# Regex to split on the repeating page header
PAGE_HEADER_2006_RE = re.compile(
    r"No\.\s+CANDIDATE NAME\s+SEX\s*\n"
    r"VALID VOTES POLLED\s*\n"
    r"TOTAL.*?\n"
    r"\s*DETAILED RESULTS\s*\n"
    r"Election Commission.*?\n",
    re.DOTALL
)

# Constituency header line: "1.  MANJESWAR"
CONSTITUENCY_2006_RE = re.compile(r"^(\d+)\.\s+(.+)$", re.MULTILINE)

# Turnout: "TOTAL: 109747 131 109878"
TURNOUT_2006_RE = re.compile(r"TOTAL:\s*(\d+)\s+(\d+)\s+(\d+)")

# Candidate line examples after name-continuation joining:
#   ". C H KUNHAMBU M 39197 45CPI(M)47 GEN 392421"
#   ". ADV. M NARAYANA BHAT M 34352 61BJP55 GEN 344132"
#   ". K SUDHAKARAN S/O RAMUNNI M 49508 237INC57 GEN 497451"
#
# Groups: (1)name (2)sex (3)general (4)postal (5)party (6)age (7)cat (8)total (9)serial
#
# Party pattern: uppercase letters, parentheses, slash, dot, dash - NO digits
# Age: exactly 2 digits right after party
# Total+serial: total is the bigger number, serial is 1-2 trailing digits

CANDIDATE_2006_RE = re.compile(
    r"^\.\s+"                              # leading '. '
    r"(.+?)"                               # (1) name
    r"\s+(M|F)\s+"                         # (2) sex
    r"(\d+)\s+"                            # (3) general votes
    r"(\d+)"                               # (4) postal votes  [no space before party]
    r"([A-Z][A-Z()/'.-]*)"                 # (5) party abbrev: letters & brackets only
    r"(\d{2})\s+"                          # (6) age: exactly 2 digits after party
    r"(GEN|SC|ST)\s+"                      # (7) category
    r"(\d+)"                               # (8) total votes   [no space before serial]
    r"(\d{1,2})$"                          # (9) serial: 1-2 digits at end of line
)


def _join_2006_name_continuations(lines):
    """Join wrapped name lines back onto the '. NAME ...' line they belong to."""
    joined = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("."):
            joined.append(s)
        elif joined and joined[-1].startswith(".") and not CANDIDATE_2006_RE.match(joined[-1]):
            joined[-1] = joined[-1] + " " + s
        else:
            joined.append(s)
    return joined


def parse_2006(text):
    """Parse 2006-format election PDF (one constituency per page)."""
    candidates = []
    summaries  = []

    # Split on repeating page header; pages[0] = party list, pages[1..] = data
    pages = PAGE_HEADER_2006_RE.split(text)

    for page in pages[1:]:
        lines = _join_2006_name_continuations(page.splitlines())

        # Find constituency header
        con_no = con_name = None
        for line in lines:
            m = CONSTITUENCY_2006_RE.match(line.strip())
            if m:
                con_no   = int(m.group(1))
                con_name = m.group(2).strip()
                break
        if con_no is None:
            continue

        # Turnout
        tm = TURNOUT_2006_RE.search(page)
        if tm:
            summaries.append({
                "constituency_no":   con_no,
                "constituency_name": con_name,
                "total_electors":    None,
                "general_votes":     int(tm.group(1)),
                "postal_votes":      int(tm.group(2)),
                "total_votes":       int(tm.group(3)),
                "turnout_pct":       None,
            })

        # Candidates
        for line in lines:
            cm = CANDIDATE_2006_RE.match(line.strip())
            if cm:
                candidates.append({
                    "constituency_no":   con_no,
                    "constituency_name": con_name,
                    "total_electors":    None,
                    "serial_no":         int(cm.group(9)),
                    "candidate_name":    cm.group(1).strip(),
                    "sex":               cm.group(2),
                    "age":               int(cm.group(6)),
                    "category":          cm.group(7),
                    "party":             cm.group(5),
                    "symbol":            None,
                    "general_votes":     int(cm.group(3)),
                    "postal_votes":      int(cm.group(4)),
                    "total_votes":       int(cm.group(8)),
                    "vote_pct":          None,
                })

    return candidates, summaries


# ==============================================================================
#  2011 FORMAT PARSER
# ==============================================================================
#
# All pages concatenated into one string.  No symbol column.
# Constituency header: "{NAME}{N}.Constituency TOTAL ELECTORS : {ELECTORS}"
# Candidate row: "{NAME}M/F {AGE} {CAT}{PARTY} {POSTAL} {TOTAL} {GENERAL} {PCT} {SERIAL}"
# Turnout: "{POSTAL} {TOTAL} TOTAL: {GENERAL} TURNOUT {PCT}"

CONSTITUENCY_2011_RE = re.compile(
    r"([A-Z][A-Z\s().,\'&/-]+?)"
    r"(\d+)\.\s*Constituency"
    r"\s*TOTAL ELECTORS\s*:\s*([\d,]+)"
)

CANDIDATE_2011_RE = re.compile(
    r"([A-Z][A-Z .,\'&()/\-]+?)"
    r"(M|F)\s+"
    r"(\d{1,3})\s+"
    r"(GEN|SC|ST)\s*"
    r"([A-Z][A-Z0-9()/\-.']*)\s+"
    r"(\d+)\s+"
    r"(\d+)\s+"
    r"(\d+)\s+"
    r"([\d.]+)\s+"
    r"(\d+)"
)

TURNOUT_2011_RE = re.compile(
    r"(\d+)\s+(\d+)\s+TOTAL:\s+(\d+)\s+TURNOUT\s+([\d.]+)"
)

# Repeating page header on every 2011 page
PAGE_HEADER_2011_RE = re.compile(
    r"CANDIDATE NAMES?EXAGE\s*CATEGORYPARTYPOSTALTOTALGENERALVALID VOTES POLLED"
    r".*?"
    r"%\s*VOTES\s*POLLED",
    re.DOTALL
)
PAGE_FOOTER_2011_RE = re.compile(r"\\?nPage\s+\d+\s+of\s+\d+")


def _strip_2011_headers(text):
    text = PAGE_HEADER_2011_RE.sub(" ", text)
    text = PAGE_FOOTER_2011_RE.sub(" ", text)
    text = re.sub(
        r"LIST OF PARTICIPATING POLITICAL PARTIES.*?INDEPENDENTS.*?IND.*?31\.",
        " ", text, flags=re.DOTALL
    )
    return text


def parse_2011(text):
    """Parse 2011-format election PDF text."""
    text = _strip_2011_headers(text)
    candidates = []
    summaries  = []

    header_positions = [(m.start(), m) for m in CONSTITUENCY_2011_RE.finditer(text)]

    for idx, (start, m) in enumerate(header_positions):
        end   = header_positions[idx + 1][0] if idx + 1 < len(header_positions) else len(text)
        block = text[start:end]

        con_no   = int(m.group(2))
        con_name = m.group(1).strip()
        con_elec = int(m.group(3).replace(",", ""))

        tm = TURNOUT_2011_RE.search(block)
        if tm:
            summaries.append({
                "constituency_no":   con_no,
                "constituency_name": con_name,
                "total_electors":    con_elec,
                "general_votes":     int(tm.group(3)),
                "postal_votes":      int(tm.group(1)),
                "total_votes":       int(tm.group(2)),
                "turnout_pct":       float(tm.group(4)),
            })
            block = block[:tm.start()]

        block_body = block[m.end() - start:]
        for cm in CANDIDATE_2011_RE.finditer(block_body):
            candidates.append({
                "constituency_no":   con_no,
                "constituency_name": con_name,
                "total_electors":    con_elec,
                "serial_no":         int(cm.group(10)),
                "candidate_name":    cm.group(1).strip(),
                "sex":               cm.group(2),
                "age":               int(cm.group(3)),
                "category":          cm.group(4),
                "party":             cm.group(5),
                "symbol":            None,
                "general_votes":     int(cm.group(8)),
                "postal_votes":      int(cm.group(6)),
                "total_votes":       int(cm.group(7)),
                "vote_pct":          float(cm.group(9)),
            })

    return candidates, summaries


# ==============================================================================
#  2021 FORMAT PARSER
# ==============================================================================

STARTS_RECORD_2021 = re.compile(
    r"^\d+\s+[A-Za-z]"
    r"|^NOTA\s+NOTA"
    r"|^TURN OUT TOTAL:"
    r"|^Constituency\s+"
    r"|^GRAND TOTAL:"
    r"|^Page\s+\d"
    r"|^ST1006"
    r"|^Election Commission"
    r"|^VALID VOTES"
    r"|^CANDIDATE NAME"
    r"|^PARTY TYPE"
    r"|^Disclaimer"
    r"|^This report"
    r"|^LIST OF"
    r"|^NATIONAL PARTIES"
    r"|^STATE PARTIES"
    r"|^REGISTERED"
    r"|^INDEPENDENTS"
    r"|^\d+\.\s+[A-Z]"
)

CONSTITUENCY_2021_RE = re.compile(
    r"Constituency\s+(\d+)\s*\.\s*(.+?)\s+TOTAL ELECTORS\s+([\d,\s]+)"
)
TURNOUT_2021_RE = re.compile(
    r"TURN OUT TOTAL:\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)"
)
NOTA_2021_RE = re.compile(
    r"^\d+\s+NOTA\s+NOTA\s+NOTA\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)$"
)
CANDIDATE_2021_RE = re.compile(
    r"^(\d+)\s+"
    r"(.+?)\s+"
    r"(MALE|FEMALE|THIRD)\s+"
    r"(\d{1,3})\s+"
    r"(GENERAL|SC|ST)\s+"
    r"([A-Z][A-Z0-9()/\-.]*)\s+"
    r"(.+?)\s+"
    r"(\d+)\s+"
    r"(\d+)\s+"
    r"(\d+)\s+"
    r"([\d.]+)$"
)


def _join_continuation_lines_2021(text):
    raw    = [l.rstrip() for l in text.splitlines()]
    joined = []
    for line in raw:
        s = line.strip()
        if not s:
            continue
        if joined and not STARTS_RECORD_2021.match(s):
            joined[-1] = joined[-1] + " " + s
        else:
            joined.append(s)
    return joined


def parse_2021(text):
    lines      = _join_continuation_lines_2021(text)
    candidates = []
    summaries  = []
    cur_no = cur_name = cur_elec = None

    for line in lines:
        m = CONSTITUENCY_2021_RE.search(line)
        if m:
            cur_no   = int(m.group(1))
            cur_name = m.group(2).strip()
            cur_elec = int(re.sub(r"\s+", "", m.group(3)))
            continue

        m = TURNOUT_2021_RE.search(line)
        if m and cur_no is not None:
            summaries.append({
                "constituency_no":   cur_no,
                "constituency_name": cur_name,
                "total_electors":    cur_elec,
                "general_votes":     int(m.group(1).replace(",", "")),
                "postal_votes":      int(m.group(2).replace(",", "")),
                "total_votes":       int(m.group(3).replace(",", "")),
                "turnout_pct":       float(m.group(4)),
            })
            continue

        m = NOTA_2021_RE.match(line)
        if m and cur_no is not None:
            candidates.append({
                "constituency_no":   cur_no,
                "constituency_name": cur_name,
                "total_electors":    cur_elec,
                "serial_no":         None,
                "candidate_name":    "NOTA",
                "sex":               None,
                "age":               None,
                "category":          None,
                "party":             "NOTA",
                "symbol":            "NOTA",
                "general_votes":     int(m.group(1)),
                "postal_votes":      int(m.group(2)),
                "total_votes":       int(m.group(3)),
                "vote_pct":          float(m.group(4)),
            })
            continue

        m = CANDIDATE_2021_RE.match(line)
        if m and cur_no is not None:
            candidates.append({
                "constituency_no":   cur_no,
                "constituency_name": cur_name,
                "total_electors":    cur_elec,
                "serial_no":         int(m.group(1)),
                "candidate_name":    m.group(2).strip(),
                "sex":               m.group(3),
                "age":               int(m.group(4)),
                "category":          m.group(5),
                "party":             m.group(6),
                "symbol":            m.group(7).strip(),
                "general_votes":     int(m.group(8)),
                "postal_votes":      int(m.group(9)),
                "total_votes":       int(m.group(10)),
                "vote_pct":          float(m.group(11)),
            })

    return candidates, summaries


# -- Winner flag ---------------------------------------------------------------

def add_winner_flag(candidates):
    best = defaultdict(int)
    for r in candidates:
        if r["candidate_name"] != "NOTA":
            c = r["constituency_no"]
            if r["total_votes"] > best[c]:
                best[c] = r["total_votes"]
    for r in candidates:
        r["winner"] = (
            r["candidate_name"] != "NOTA"
            and r["total_votes"] == best[r["constituency_no"]]
        )
    return candidates


# -- Output helpers ------------------------------------------------------------

CAND_FIELDS = [
    "constituency_no", "constituency_name", "total_electors",
    "serial_no", "candidate_name", "sex", "age", "category",
    "party", "symbol",
    "general_votes", "postal_votes", "total_votes", "vote_pct", "winner",
]
SUMM_FIELDS = [
    "constituency_no", "constituency_name", "total_electors",
    "general_votes", "postal_votes", "total_votes", "turnout_pct",
]


def write_csv(rows, fields, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  [OK] {len(rows):>5,} rows  ->  {path}")


def write_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  [OK] JSON          ->  {path}")


# -- Main ----------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Extract Kerala election results from an ECI PDF (2006, 2011, or 2021 format)."
    )
    ap.add_argument("pdf", nargs="?", default="statistical_report.pdf",
                    help="Path to the PDF (default: statistical_report.pdf)")
    ap.add_argument("--output", "-o", default="election_candidates.csv",
                    help="Candidate data output CSV")
    ap.add_argument("--summary-output", default="election_summary.csv",
                    help="Turnout summary output CSV")
    ap.add_argument("--json", action="store_true",
                    help="Also write election_data.json")
    ap.add_argument("--format", choices=["2006", "2011", "2021", "auto"], default="auto",
                    help="Force a specific PDF format (default: auto-detect)")
    args = ap.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        raise SystemExit(f"File not found: {pdf_path}")

    print(f"\nReading: {pdf_path}")
    text = extract_text_from_pdf(str(pdf_path))
    print(f"  {len(text):,} characters extracted")

    fmt = args.format if args.format != "auto" else detect_format(text)
    print(f"  Detected format: {fmt}")

    print("\nParsing ...")
    if fmt == "2006":
        candidates, summaries = parse_2006(text)
    elif fmt == "2011":
        candidates, summaries = parse_2011(text)
    else:
        candidates, summaries = parse_2021(text)

    candidates = add_winner_flag(candidates)

    nota_rows = sum(1 for r in candidates if r["candidate_name"] == "NOTA")
    real_rows  = len(candidates) - nota_rows
    winners    = [r for r in candidates if r.get("winner")]
    con_count  = len(set(r["constituency_no"] for r in candidates))

    print(f"  {con_count} constituencies")
    print(f"  {real_rows} candidates  +  {nota_rows} NOTA rows  =  {len(candidates)} total")
    print(f"  {len(winners)} winners identified")
    print(f"  {len(summaries)} turnout summaries")

    print("\nWriting files ...")
    write_csv(candidates, CAND_FIELDS, args.output)
    write_csv(summaries,  SUMM_FIELDS, args.summary_output)
    if args.json:
        write_json({"candidates": candidates, "summaries": summaries},
                   "election_data.json")

    # Quick stats
    total_votes = sum(r["total_votes"] for r in candidates if r["total_votes"] is not None)
    total_elec  = sum(s["total_electors"] for s in summaries if s["total_electors"] is not None)
    turnout     = total_votes / total_elec * 100 if total_elec else 0

    seat_tally = {}
    for r in winners:
        seat_tally[r["party"]] = seat_tally.get(r["party"], 0) + 1

    print(f"\n-- Seat tally -----------------------------------------------")
    for party, seats in sorted(seat_tally.items(), key=lambda x: -x[1]):
        print(f"  {party:<15s}  {seats:3d}")
    print(f"\n  Total votes cast:  {total_votes:,}")
    if total_elec:
        print(f"  Total electors:    {total_elec:,}")
        print(f"  Overall turnout:   {turnout:.2f}%")
    print()


if __name__ == "__main__":
    main()
