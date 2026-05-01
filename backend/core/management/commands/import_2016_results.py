"""
Import 2016 LA election results from 'Detailed Results.xlsx'.

Populates TWO tables:
  • HistoricalResult2016Full  — every candidate row (mirrors HistoricalResult2021)
  • HistoricalResult2016      — winner + runner-up summary (backward compat)

Usage:
    python manage.py import_2016_results
    python manage.py import_2016_results --xlsx "path/to/Detailed Results.xlsx"
    python manage.py import_2016_results --clear   # wipe both tables first
"""

import os
import openpyxl
from django.core.management.base import BaseCommand
from core.models import (
    Constituency, PartyAllianceYear,
    HistoricalResult2016, HistoricalResult2016Full,
)


# Default path — two levels up from backend/ to project root, then data/
DEFAULT_XLSX = os.path.normpath(os.path.join(
    os.path.dirname(__file__),
    '..', '..', '..', '..', '..', '..',
    'data', 'Detailed Results.xlsx'
))

# Column indices (0-based) in the xlsx sheet
COL_CONST_NO     = 0
COL_CONST_NAME   = 1
COL_CAND_NAME    = 2
COL_SEX          = 3
COL_AGE          = 4
COL_CATEGORY     = 5
COL_PARTY        = 6
COL_GEN_VOTES    = 7
COL_POST_VOTES   = 8
COL_TOTAL        = 9
COL_ELECTORS     = 10
COL_VOTES_POLLED = 11

# Party-code aliases: xlsx code → canonical code stored in PartyAllianceYear
PARTY_ALIAS = {
    'CPM':  'CPI(M)',   # ECI xlsx uses CPM
    'CPIM': 'CPI(M)',   # another variant
    'C(S)': 'CON(S)',   # Congress (Secular) / Kadannappalli faction
    'KCST': 'KC(ST)',   # Kerala Congress (Skaria Thomas)
    'KCS':  'KC(S)',    # Kerala Congress (Secular) — C. F. Thomas, Changanassery
}

# Constituency-specific alliance overrides where ECI reuses the same code for
# two factionally-distinct parties that belong to different alliances.
# Format: {const_no: {normalised_party_code: 'ALLIANCE'}}
CONSTITUENCY_PARTY_ALLIANCE_OVERRIDE = {
    # CMPKSC in Chavara = CMP(Aravindakshan) → LDF
    # CMPKSC in Kunnamkulam = C.P.John faction → UDF (normal mapping)
    117: {'CMPKSC': 'LDF'},
}


class Command(BaseCommand):
    help = 'Import 2016 LA results from Detailed Results.xlsx (all candidates + summary)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--xlsx', type=str, default=None,
            help='Path to Detailed Results.xlsx (default: data/Detailed Results.xlsx)',
        )
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete all existing 2016 records before importing',
        )

    def handle(self, *args, **options):
        xlsx_path = options['xlsx'] or DEFAULT_XLSX
        if not os.path.exists(xlsx_path):
            self.stderr.write(self.style.ERROR(f'File not found: {xlsx_path}'))
            return

        self.stdout.write(f'Reading: {xlsx_path}')

        if options['clear']:
            n_full = HistoricalResult2016Full.objects.count()
            n_sum  = HistoricalResult2016.objects.count()
            HistoricalResult2016Full.objects.all().delete()
            HistoricalResult2016.objects.all().delete()
            self.stdout.write(self.style.WARNING(
                f'  Cleared {n_full} full records + {n_sum} summary records'
            ))

        # Build alliance lookup once — avoids repeated DB hits per candidate
        alliance_map: dict[str, str] = {
            r.party_code: r.alliance
            for r in PartyAllianceYear.objects.filter(election_year=2016, election_type='LA')
        }

        def get_alliance(party_code: str, const_no: int) -> str:
            overrides = CONSTITUENCY_PARTY_ALLIANCE_OVERRIDE.get(const_no, {})
            if party_code in overrides:
                return overrides[party_code]
            return alliance_map.get(party_code, 'OTH')

        wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
        ws = wb['DetailedResult']

        rows = list(ws.iter_rows(values_only=True))
        data_rows = rows[3:]  # skip title row, blank row, header row

        # Group rows by constituency number
        by_const: dict[int, list] = {}
        for row in data_rows:
            const_no = row[COL_CONST_NO]
            if const_no is None or not isinstance(const_no, int):
                continue
            by_const.setdefault(const_no, []).append(row)

        created_full = 0
        created_sum  = 0
        updated_sum  = 0
        skipped      = 0

        for const_no, crows in sorted(by_const.items()):
            try:
                constituency = Constituency.objects.get(number=const_no)
            except Constituency.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'  Constituency #{const_no} not found — skipping'
                ))
                skipped += 1
                continue

            # Pull constituency-level totals from any row
            electors     = crows[0][COL_ELECTORS]     or 0
            votes_polled = crows[0][COL_VOTES_POLLED] or 0

            # Parse every candidate row
            all_cands = []
            for row in crows:
                party_raw = (row[COL_PARTY] or '').strip()
                if not party_raw:
                    continue
                party_norm = PARTY_ALIAS.get(party_raw, party_raw)
                gen_v  = row[COL_GEN_VOTES]  or 0
                post_v = row[COL_POST_VOTES] or 0
                total  = row[COL_TOTAL]      or 0
                pct    = round(total / votes_polled * 100, 2) if votes_polled else 0
                all_cands.append({
                    'name':      (row[COL_CAND_NAME] or '').strip().title(),
                    'sex':       (row[COL_SEX]      or '').strip()[:1],
                    'age':       row[COL_AGE] if isinstance(row[COL_AGE], int) else None,
                    'category':  (row[COL_CATEGORY] or 'GEN').strip(),
                    'party':     party_norm,
                    'gen_v':     gen_v,
                    'post_v':    post_v,
                    'total':     total,
                    'pct':       pct,
                    'is_nota':   party_raw == 'NOTA',
                })

            real = [c for c in all_cands if not c['is_nota']]
            if len(real) < 2:
                self.stdout.write(self.style.WARNING(
                    f'  {constituency.name}: only {len(real)} non-NOTA candidates — skipping'
                ))
                skipped += 1
                continue

            real.sort(key=lambda c: c['total'], reverse=True)
            winner   = real[0]
            runnerup = real[1]

            # ── Populate HistoricalResult2016Full (delete old, bulk-create new) ──
            HistoricalResult2016Full.objects.filter(constituency=constituency).delete()
            bulk = []
            for c in all_cands:
                bulk.append(HistoricalResult2016Full(
                    constituency      = constituency,
                    candidate_name    = c['name'],
                    sex               = c['sex'],
                    age               = c['age'],
                    category          = c['category'],
                    party_code        = c['party'],
                    general_votes     = c['gen_v'],
                    postal_votes      = c['post_v'],
                    total_votes       = c['total'],
                    vote_percentage   = c['pct'],
                    total_electors    = electors,
                    total_votes_polled= votes_polled,
                    is_winner         = (not c['is_nota']) and c['total'] == winner['total'],
                ))
            HistoricalResult2016Full.objects.bulk_create(bulk)
            created_full += len(bulk)

            # ── Populate HistoricalResult2016 (winner + runner-up summary) ──
            w_alliance  = get_alliance(winner['party'],   const_no)
            ru_alliance = get_alliance(runnerup['party'], const_no)
            margin = winner['total'] - runnerup['total']

            _, was_created = HistoricalResult2016.objects.update_or_create(
                constituency=constituency,
                defaults={
                    'winner_candidate':    winner['name'],
                    'winner_party':        winner['party'],
                    'winner_alliance':     w_alliance,
                    'winner_votes':        winner['total'],
                    'winner_percentage':   winner['pct'],
                    'runnerup_candidate':  runnerup['name'],
                    'runnerup_party':      runnerup['party'],
                    'runnerup_alliance':   ru_alliance,
                    'runnerup_votes':      runnerup['total'],
                    'runnerup_percentage': runnerup['pct'],
                    'margin':              margin,
                },
            )
            if was_created:
                created_sum += 1
            else:
                updated_sum += 1

            self.stdout.write(
                f'  {constituency.name}: {len(all_cands)} candidates imported — '
                f'{winner["name"]} ({winner["party"]}/{w_alliance}) +{margin:,}'
            )

        self.stdout.write(self.style.SUCCESS(
            f'\nDone:\n'
            f'  Full records : {created_full} created\n'
            f'  Summary rows : {created_sum} created, {updated_sum} updated\n'
            f'  Skipped      : {skipped}'
        ))
