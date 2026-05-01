"""
Import 2026 Kerala Assembly Election candidates from OpenDataKerala dataset.

Source: https://zenodo.org/records/19323710
CSV: Kerala Legislative Assembly Election 2026 Candidate Data.csv
License: ODbL

CSV Columns (from Zenodo dataset description):
  reference        - Unique ID e.g. "26kla001"
  constituencyName - Official AC name e.g. "Manjeshwar"
  alliance         - LDF / UDF / NDA / OTH (or blank)
  party            - Party name e.g. "CPI(M)", "INC", "BJP"
  candidateName    - Name in English
  malayalamName    - Name in Malayalam Unicode
  aparanTag        - Reference to primary candidate if this is a dummy/namesake
  candidateGender  - male / female
  candidateAge     - Integer age from affidavit
  Symbol           - Election symbol name
  mlaTrackLink     - URL to MLATrack profile (if sitting MLA)

Usage:
  # Download the CSV first:
  curl -L "https://zenodo.org/records/19323710/files/Kerala%20Legislative%20Assembly%20Election%202026%20Candidate%20Data.csv?download=1" \
       -o data/kla2026_candidates.csv

  # Then import:
  python manage.py import_2026_candidates ../data/kla2026_candidates.csv

  # Dry run (no DB writes):
  python manage.py import_2026_candidates ../data/kla2026_candidates.csv --dry-run

  # Re-run safely (uses get_or_create, won't duplicate):
  python manage.py import_2026_candidates ../data/kla2026_candidates.csv --update
"""

import csv
import re
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Constituency, Party, Candidate

# ─── Alliance normalisation ───────────────────────────────────────────────────
# ODK uses various forms; map them to your model's choices
ALLIANCE_MAP = {
    "ldf": "LDF",
    "udf": "UDF",
    "nda": "NDA",
    "oth": "OTH",
    "others": "OTH",
    "independent": "OTH",
    "ind": "OTH",
    "": "OTH",
}

# ─── Party auto-create defaults ───────────────────────────────────────────────
# If a party code appears in the CSV but not in your DB, it will be created
# with these alliance defaults. Adjust as needed.
KNOWN_PARTY_ALLIANCES = {
    # LDF
    "CPI(M)": "LDF", "CPM": "LDF",
    "CPI": "LDF",
    "JD(S)": "LDF",
    "NCP": "LDF",
    "KC(B)": "LDF",
    "INL": "LDF",
    "RSP": "LDF",
    "LJD": "LDF",

    # UDF
    "INC": "UDF", "CONGRESS": "UDF",
    "IUML": "UDF",
    "KC(M)": "UDF",
    "KC(J)": "UDF",
    "VCK": "UDF",
    "AIFB": "UDF",
    "KEC": "UDF",
    "KMDK": "UDF",

    # NDA
    "BJP": "NDA",
    "BDJS": "NDA",
    "KGP": "NDA",
    "NSS": "NDA",

    # Others
    "SDPI": "OTH",
    "AAP": "OTH",
    "IND": "OTH",
}


def normalise_alliance(raw):
    return ALLIANCE_MAP.get(raw.strip().lower(), "OTH")


# ─── Constituency name aliases ────────────────────────────────────────────────
# CSV (Zenodo 2026 dataset) uses slightly different transliterations from the DB.
# Keys are CSV names lowercased; values are DB names lowercased.
CONSTITUENCY_ALIASES = {
    "manjeshwaram":    "manjeshwar",
    "thrikaripur":     "trikaripur",
    "dharmadom":       "dharmadam",
    "vatakara":        "vadakara",
    "mattanur":        "mattannur",
    "koyilandy":       "quilandy",
    "thanur":          "tanur",
    "mannarkkad":      "mannarkad",
    "guruvayur":       "guruvayoor",
    "irinjalakuda":    "irinjalakkuda",
    "chalakudy":       "chalakkudy",
    "vypin":           "vypen",
    "vypeen":          "vypen",
    "thrippunithura":  "thripunithura",
    "ernakulam":       "eranakulam",
    "payyanur":        "payyannur",       # DB uses double-n
    "kuttiady":        "kuttiadi",
    "balussery":       "balusseri",
    "ambalappuzha":    "ambalapuzha",     # DB spelling
    "mavelikkara":     "mavelikara",
    "kazhakoottam":    "kazhakkoottam",   # DB spelling
    "karunagapally":   "karunagappally",  # DB uses double-p
    "sulthan bathery":  "sulthanbathery",  # DB has no space
    "chathannoor":     "chathannur",
}


def normalise_party_code(raw_party):
    """
    Convert full party name from ODK CSV to a short code.
    e.g. "Communist Party of India (Marxist)" → "CPI(M)"
    ODK often uses the short form already; this is a passthrough with cleanup.
    """
    return raw_party.strip()[:20]  # truncate to model's max_length if needed


def guess_alliance_for_party(party_code, csv_alliance):
    """
    Use CSV alliance first; fall back to our known-party lookup; default OTH.
    """
    if csv_alliance and csv_alliance.upper() in ("LDF", "UDF", "NDA"):
        return csv_alliance.upper()
    return KNOWN_PARTY_ALLIANCES.get(party_code, "OTH")


class Command(BaseCommand):
    help = "Import 2026 Kerala Assembly Election candidates from OpenDataKerala CSV"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", help="Path to the ODK candidate CSV file")
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Parse and validate without writing to database"
        )
        parser.add_argument(
            "--update", action="store_true",
            help="Update existing candidates if they already exist"
        )
        parser.add_argument(
            "--skip-unknown-constituencies", action="store_true",
            help="Skip rows where constituency isn't in DB (instead of erroring)"
        )

    def handle(self, *args, **options):
        csv_path = options["csv_file"]
        dry_run = options["dry_run"]
        do_update = options["update"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no database changes will be made\n"))

        # ── Load CSV ──────────────────────────────────────────────────────────
        try:
            with open(csv_path, encoding="utf-8-sig") as f:
                # Peek at header
                sample = f.read(500)
                f.seek(0)
                self.stdout.write(f"CSV header preview:\n  {sample.splitlines()[0]}\n")
                reader = csv.DictReader(f)
                rows = list(reader)
        except FileNotFoundError:
            raise CommandError(f"File not found: {csv_path}")
        except Exception as e:
            raise CommandError(f"Error reading CSV: {e}")

        self.stdout.write(f"Loaded {len(rows)} rows from CSV\n")

        # ── Build constituency lookup: name → object ──────────────────────────
        # ODK uses English names; your DB might have slightly different spellings
        constituencies_by_name = {}
        for c in Constituency.objects.select_related("district"):
            constituencies_by_name[c.name.lower().strip()] = c
            # Also index by number for fallback
            constituencies_by_name[str(c.number)] = c

        # ── Process rows ──────────────────────────────────────────────────────
        created_candidates = 0
        updated_candidates = 0
        created_parties = 0
        skipped = 0
        errors = []

        with transaction.atomic():
            for i, row in enumerate(rows, 1):
                # ── Field extraction ──────────────────────────────────────────
                # Handle both possible column name variants gracefully
                reference       = row.get("reference", row.get("Reference", "")).strip()
                constituency_name = row.get("constituencyName", row.get("ConstituencyName", "")).strip()
                alliance_raw    = row.get("alliance", row.get("Alliance", "")).strip()
                party_raw       = row.get("party", row.get("Party", "")).strip()
                candidate_name  = row.get("candidateName", row.get("CandidateName", "")).strip()
                malayalam_name  = row.get("malayalamName", row.get("MalayalamName", "")).strip()
                aparan_tag      = row.get("aparanTag", "").strip()
                gender          = row.get("candidateGender", row.get("Gender", "")).strip().lower()
                age_raw         = row.get("candidateAge", row.get("Age", "")).strip()
                symbol          = row.get("Symbol", row.get("symbol", "")).strip()
                mla_track_link  = row.get("mlaTrackLink", row.get("MLATrackLink", "")).strip()

                # ── Validate required fields ──────────────────────────────────
                if not candidate_name:
                    errors.append(f"Row {i}: missing candidateName")
                    skipped += 1
                    continue

                if not constituency_name:
                    errors.append(f"Row {i} ({candidate_name}): missing constituencyName")
                    skipped += 1
                    continue

                # ── Constituency lookup ───────────────────────────────────────
                csv_key = constituency_name.lower().strip()
                # 1. Direct match
                constituency = constituencies_by_name.get(csv_key)
                # 2. Alias map for known transliteration differences
                if not constituency:
                    alias_key = CONSTITUENCY_ALIASES.get(csv_key)
                    if alias_key:
                        constituency = constituencies_by_name.get(alias_key)
                # 3. Fuzzy first-word match as last resort
                if not constituency:
                    first_word = csv_key.split()[0]
                    for key, val in constituencies_by_name.items():
                        if isinstance(key, str) and key.startswith(first_word) and len(first_word) > 4:
                            constituency = val
                            self.stdout.write(
                                self.style.WARNING(
                                    f"  Row {i}: fuzzy-matched '{constituency_name}' -> '{val.name}'"
                                )
                            )
                            break

                if not constituency:
                    msg = f"Row {i} ({candidate_name}): constituency '{constituency_name}' not in DB"
                    if options["skip_unknown_constituencies"]:
                        self.stdout.write(self.style.WARNING(f"  SKIP: {msg}"))
                        skipped += 1
                        continue
                    else:
                        errors.append(msg)
                        skipped += 1
                        continue

                # ── Party lookup / create ─────────────────────────────────────
                party_code = normalise_party_code(party_raw) if party_raw else "IND"
                alliance = guess_alliance_for_party(party_code, alliance_raw)

                party, party_created = Party.objects.get_or_create(
                    code=party_code,
                    defaults={
                        "full_name": party_raw or "Independent",
                        "alliance": alliance,
                        "color_code": "#808080",  # default grey; update via admin
                    }
                )
                if party_created:
                    created_parties += 1
                    if not dry_run:
                        self.stdout.write(f"  Created party: {party_code} ({alliance})")

                # ── Age parsing ───────────────────────────────────────────────
                age = None
                if age_raw:
                    try:
                        age = int(re.sub(r"\D", "", age_raw))
                    except ValueError:
                        pass

                # ── Candidate create / update ─────────────────────────────────
                candidate_defaults = {
                    "party": party,
                    "votes": 0,
                    "vote_percentage": 0.0,
                    "is_winner": False,
                    "is_leading": False,
                    # Extra fields from ODK — add these to your Candidate model if desired
                    # "malayalam_name": malayalam_name,
                    # "gender": gender,
                    # "age": age,
                    # "symbol": symbol,
                    # "mla_track_link": mla_track_link,
                    # "odk_reference": reference,
                    # "is_aparan": bool(aparan_tag),
                }

                if not dry_run:
                    candidate, created = Candidate.objects.get_or_create(
                        name=candidate_name,
                        constituency=constituency,
                        defaults=candidate_defaults,
                    )
                    if not created and do_update:
                        for field, value in candidate_defaults.items():
                            setattr(candidate, field, value)
                        candidate.save()
                        updated_candidates += 1
                    elif created:
                        created_candidates += 1
                else:
                    # Dry run — just count
                    exists = Candidate.objects.filter(
                        name=candidate_name, constituency=constituency
                    ).exists()
                    if exists:
                        updated_candidates += 1
                    else:
                        created_candidates += 1

                if i % 100 == 0:
                    self.stdout.write(f"  Processed {i}/{len(rows)}...")

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(
            f"{'[DRY RUN] ' if dry_run else ''}Import complete!"
        ))
        self.stdout.write(f"  Candidates created : {created_candidates}")
        self.stdout.write(f"  Candidates updated : {updated_candidates}")
        self.stdout.write(f"  Parties created    : {created_parties}")
        self.stdout.write(f"  Rows skipped       : {skipped}")

        if errors:
            self.stdout.write(self.style.WARNING(f"\n  Warnings/errors ({len(errors)}):"))
            for e in errors[:20]:
                self.stdout.write(f"    - {e}")
            if len(errors) > 20:
                self.stdout.write(f"    ... and {len(errors) - 20} more")

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\nThis was a dry run. Re-run without --dry-run to commit."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "\nNext step: verify in Django admin -> Candidates"
            ))
