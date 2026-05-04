"""
Re-run the party-aware candidate matching on already-scraped ECIScrapeRaw records.

This is useful after improving the matching logic — it replays matching on all
existing raw scrapes (PENDING / PARTIAL, or all) without hitting ECI again.

Usage:
    # Rematch only PENDING + PARTIAL scrapes (default)
    python manage.py rematch_scrapes

    # Rematch all scrapes (including already MATCHED)
    python manage.py rematch_scrapes --all

    # Rematch a specific constituency by AC number
    python manage.py rematch_scrapes --ac 42

    # Dry-run: show what would match without writing anything
    python manage.py rematch_scrapes --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import ECIScrapeRaw, ECICandidateMatch, Candidate, CandidateAlias
from core.admin_scraper_views import _normalise, _resolve_eci_party_code


class Command(BaseCommand):
    help = 'Re-run party-aware candidate matching on existing ECIScrapeRaw records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all', action='store_true',
            help='Rematch ALL scrapes including already-MATCHED ones'
        )
        parser.add_argument(
            '--ac', type=int, default=None,
            help='Rematch only this AC number'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show matching results without writing to the DB'
        )

    def handle(self, *args, **options):
        rematch_all = options['all']
        ac_filter = options['ac']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be written\n'))

        # ── Choose which raw scrapes to process ───────────────────────────────
        qs = ECIScrapeRaw.objects.select_related('constituency').order_by(
            'constituency__number', '-scraped_at'
        )
        if ac_filter:
            qs = qs.filter(constituency__number=ac_filter)
        if not rematch_all:
            qs = qs.filter(match_status__in=['PENDING', 'PARTIAL'])

        # Only the LATEST scrape per constituency (no point rematching old ones)
        seen_consts = set()
        raws_to_process = []
        for raw in qs:
            cid = raw.constituency_id
            if cid not in seen_consts:
                seen_consts.add(cid)
                raws_to_process.append(raw)

        total = len(raws_to_process)
        if total == 0:
            self.stdout.write(self.style.SUCCESS('Nothing to rematch.'))
            return

        self.stdout.write(f'Rematching {total} scrape(s)...\n')

        improved = 0
        fully_matched = 0

        for raw in raws_to_process:
            constituency = raw.constituency
            self.stdout.write(f'  [{raw.match_status:7s}] AC {constituency.number:3d} {constituency.name}')

            # Load all DB candidates for this constituency with party
            all_db_candidates = list(
                Candidate.objects.filter(constituency=constituency).select_related('party')
            )
            db_by_norm = {_normalise(c.name): c for c in all_db_candidates}

            # Get existing match rows for this scrape
            existing_matches = list(
                raw.matches.select_related('candidate', 'candidate__party').all()
            )

            # Collect ECI candidates from raw_candidates JSON (ground truth)
            raw_cands_by_name = {c['name']: c for c in raw.raw_candidates}

            matched_count = 0
            total_real = 0
            newly_matched = 0

            with transaction.atomic():
                for match in existing_matches:
                    if match.is_nota:
                        continue
                    total_real += 1

                    # Already confirmed — keep it
                    if match.is_confirmed and match.candidate:
                        matched_count += 1
                        continue

                    # Try to resolve using improved logic
                    db_candidate = None

                    # 1. Alias lookup
                    alias = CandidateAlias.objects.filter(
                        constituency=constituency, eci_name=match.eci_name
                    ).first()
                    if alias:
                        db_candidate = alias.candidate

                    if not db_candidate:
                        norm_name = _normalise(match.eci_name)
                        eci_party_code = _resolve_eci_party_code(match.eci_party or '')

                        # 2. Exact name
                        db_candidate = db_by_norm.get(norm_name)

                        # 3. Fuzzy first-word + party filter
                        if not db_candidate:
                            first_word = norm_name.split()[0] if norm_name else ''
                            if len(first_word) > 3:
                                # 3a. name prefix + party code match
                                if eci_party_code:
                                    for db_cand in all_db_candidates:
                                        db_norm = _normalise(db_cand.name)
                                        party_code = db_cand.party.code if db_cand.party else None
                                        if db_norm.startswith(first_word) and party_code == eci_party_code:
                                            db_candidate = db_cand
                                            break

                                # 3b. name prefix only (fallback)
                                # ONLY when party is unknown to prevent cross-party mismatches
                                if not db_candidate and not eci_party_code:
                                    for db_norm, db_cand in db_by_norm.items():
                                        if db_norm.startswith(first_word):
                                            db_candidate = db_cand
                                            break

                        # 4. Last resort: single candidate with this party
                        if not db_candidate and eci_party_code:
                            party_matches = [
                                c for c in all_db_candidates
                                if c.party and c.party.code == eci_party_code
                            ]
                            if len(party_matches) == 1:
                                db_candidate = party_matches[0]

                    if db_candidate:
                        matched_count += 1
                        newly_matched += 1
                        if not dry_run:
                            match.candidate = db_candidate
                            match.is_confirmed = True
                            match.save()
                            # Save alias so next time it hits immediately
                            CandidateAlias.objects.get_or_create(
                                constituency=constituency,
                                eci_name=match.eci_name,
                                defaults={'candidate': db_candidate}
                            )

                # Update match_status on the raw record
                if not dry_run:
                    if matched_count == total_real:
                        raw.match_status = 'MATCHED'
                        fully_matched += 1
                    elif matched_count > 0:
                        raw.match_status = 'PARTIAL'
                    raw.save()

                    # Auto-commit if now fully matched
                    if raw.match_status == 'MATCHED':
                        from core.api.scraper_views import _execute_commit
                        try:
                            _execute_commit(raw)
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f'    ! Commit failed: {e}'))

            # Summary line per constituency
            status_icon = 'OK ' if matched_count == total_real else ('>> ' if matched_count > 0 else 'XX ')
            suffix = f'+{newly_matched} new' if newly_matched else 'no change'
            self.stdout.write(
                f'    {status_icon} {matched_count}/{total_real} matched ({suffix})'
            )
            if newly_matched:
                improved += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nDone: {improved}/{total} constituencies improved, '
            f'{fully_matched} now fully matched.'
        ))
