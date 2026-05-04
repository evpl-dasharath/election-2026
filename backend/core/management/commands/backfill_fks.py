"""
Backfill the party FK on all historical result models.

For each row, resolves party_code -> Party via:
  1. PartyAlias (year-specific first, then universal)
  2. Direct Party.code match
  3. Creates an OTH stub Party if all else fails

Also backfills ConstituencyMeta2021.winner_party FK.

Usage:
    python manage.py backfill_fks
    python manage.py backfill_fks --dry-run
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import (
    Alliance, Party, PartyAlias,
    HistoricalResult2006, HistoricalResult2011,
    HistoricalResult2016Full, HistoricalResult2021,
    HistoricalResult2016, ConstituencyMeta2021,
)


def resolve_party(raw_code, year, alias_cache, party_cache, oth_alliance, created_stubs):
    """Resolve a raw CSV party code to a canonical Party object."""
    code = raw_code.strip() if raw_code else 'IND'

    # 1. Year-specific alias
    key_yr = (code, year)
    if key_yr in alias_cache:
        return alias_cache[key_yr]

    # 2. Universal alias
    key_uni = (code, None)
    if key_uni in alias_cache:
        return alias_cache[key_uni]

    # 3. Direct party code match
    if code in party_cache:
        return party_cache[code]

    # 4. Create a stub OTH party so no row is left with NULL
    if code not in created_stubs:
        party, _ = Party.objects.get_or_create(
            code=code,
            defaults={'full_name': code, 'alliance': oth_alliance, 'color_code': '#808080'}
        )
        party_cache[code] = party
        created_stubs.add(code)
        return party

    return party_cache[code]


class Command(BaseCommand):
    help = 'Backfill party FK on all historical result models using alias resolution'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Report but do not save')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Build alias cache: {(alias_code, year_or_None) -> Party}
        alias_cache = {}
        for a in PartyAlias.objects.select_related('party').all():
            alias_cache[(a.alias_code, a.election_year)] = a.party

        # Build party cache by canonical code
        party_cache = {p.code: p for p in Party.objects.select_related('alliance').all()}

        oth_alliance = Alliance.objects.get(code='OTH')
        created_stubs = set()

        def backfill_model(Model, year, label):
            qs = Model.objects.filter(party__isnull=True).select_related('constituency')
            total = qs.count()
            if total == 0:
                self.stdout.write(f"  {label}: all {Model.objects.count()} rows already have FK")
                return

            self.stdout.write(f"  {label}: resolving {total} rows...")
            unknown = {}
            updates = []

            for row in qs.iterator(chunk_size=500):
                party = resolve_party(
                    row.party_code, year, alias_cache, party_cache, oth_alliance, created_stubs
                )
                row.party = party
                updates.append(row)
                if party.code not in alias_cache.values() and party.code not in party_cache:
                    unknown[row.party_code] = unknown.get(row.party_code, 0) + 1

            if not dry_run:
                with transaction.atomic():
                    Model.objects.bulk_update(updates, ['party'], batch_size=500)
                self.stdout.write(self.style.SUCCESS(
                    f"    -> Updated {len(updates)} rows"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"    [DRY RUN] Would update {len(updates)} rows"
                ))

            if created_stubs:
                self.stdout.write(self.style.WARNING(
                    f"    Stub parties created for unknown codes: {sorted(created_stubs)}"
                ))

        self.stdout.write("=== Backfilling party FKs ===\n")
        backfill_model(HistoricalResult2006, 2006, "2006")
        backfill_model(HistoricalResult2011, 2011, "2011")
        backfill_model(HistoricalResult2016Full, 2016, "2016 Full")
        backfill_model(HistoricalResult2021, 2021, "2021")

        # Backfill ConstituencyMeta2021.winner_party
        self.stdout.write("\n  ConstituencyMeta2021.winner_party...")
        meta_qs = ConstituencyMeta2021.objects.filter(winner_party__isnull=True).exclude(winner_party_code='')
        self.stdout.write(f"    {meta_qs.count()} rows to resolve")
        meta_updates = []
        for meta in meta_qs:
            party = resolve_party(
                meta.winner_party_code, 2021, alias_cache, party_cache, oth_alliance, created_stubs
            )
            meta.winner_party = party
            meta_updates.append(meta)
        if not dry_run and meta_updates:
            with transaction.atomic():
                ConstituencyMeta2021.objects.bulk_update(meta_updates, ['winner_party'], batch_size=200)
            self.stdout.write(self.style.SUCCESS(f"    -> Updated {len(meta_updates)} meta rows"))

        # Backfill HistoricalResult2016 (summary) winner/runnerup party FKs
        self.stdout.write("\n  HistoricalResult2016 (summary)...")
        r16_qs = HistoricalResult2016.objects.filter(winner_party__isnull=True)
        self.stdout.write(f"    {r16_qs.count()} rows to resolve")
        r16_updates = []
        for row in r16_qs:
            wp = resolve_party(row.winner_party_code, 2016, alias_cache, party_cache, oth_alliance, created_stubs)
            rp = resolve_party(row.runnerup_party_code, 2016, alias_cache, party_cache, oth_alliance, created_stubs)
            # Alliance FK
            wal = Alliance.objects.filter(code=row.winner_alliance_code).first() or oth_alliance
            ral = Alliance.objects.filter(code=row.runnerup_alliance_code).first() or oth_alliance
            row.winner_party = wp
            row.runnerup_party = rp
            row.winner_alliance = wal
            row.runnerup_alliance = ral
            r16_updates.append(row)
        if not dry_run and r16_updates:
            with transaction.atomic():
                HistoricalResult2016.objects.bulk_update(
                    r16_updates,
                    ['winner_party', 'runnerup_party', 'winner_alliance', 'runnerup_alliance'],
                    batch_size=200
                )
            self.stdout.write(self.style.SUCCESS(f"    -> Updated {len(r16_updates)} summary rows"))

        self.stdout.write("\n=== Summary ===")
        for Model, year, label in [
            (HistoricalResult2006, 2006, "2006"),
            (HistoricalResult2011, 2011, "2011"),
            (HistoricalResult2016Full, 2016, "2016 Full"),
            (HistoricalResult2021, 2021, "2021"),
        ]:
            null_count = Model.objects.filter(party__isnull=True).count()
            total = Model.objects.count()
            status = self.style.SUCCESS("OK") if null_count == 0 else self.style.ERROR(f"{null_count} NULL")
            self.stdout.write(f"  {label}: {total} rows, {null_count} still NULL -> {status}")

        if created_stubs:
            self.stdout.write(self.style.WARNING(
                f"\nStub parties created (check and assign correct alliance): {sorted(created_stubs)}"
            ))
