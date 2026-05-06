from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.db.models import Sum, Count, Q, Prefetch
from core.models import (
    District, Constituency, Party, Candidate, LiveResult,
    HistoricalResult2021, HistoricalResult2016, HistoricalResult2016Full,
    HistoricalResult2011, ConstituencyMeta2021,
    ParliamentResult, PartyAllianceYear, Alliance
)
from core.api.serializers import (
    DistrictSerializer, ConstituencyListSerializer, ConstituencyDetailSerializer,
    PartySerializer, ParliamentResultSerializer
)


def _build_alliance_map(year, etype='LA'):
    """Build {party_code: {'alliance': alliance_code, 'color_code': hex}} for a given year."""
    return {
        r.party.code: {'alliance': r.alliance.code, 'color_code': r.color_code}
        for r in PartyAllianceYear.objects.select_related('party', 'alliance').filter(
            election_year=year, election_type=etype
        )
    }


def _party_alliance(party_code, alliance_map):
    """Get alliance code for a party code from a pre-built map."""
    entry = alliance_map.get(party_code)
    return entry['alliance'] if entry else 'OTH'


def _party_color(party_code, alliance_map):
    """Get color code for a party code from a pre-built map."""
    entry = alliance_map.get(party_code)
    return entry['color_code'] if entry else '#808080'


class ConstituencyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for constituencies
    List view: lightweight data for all 140 constituencies
    Detail view: full data including candidates and historical results
    """
    queryset = Constituency.objects.select_related('district').prefetch_related(
        'candidates_2026', 'candidates_2026__party', 'candidates_2026__party__alliance',
        'live_results', 'results_2021', 'results_2021__party'
    ).all()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ConstituencyListSerializer
        return ConstituencyDetailSerializer
    
    @action(detail=False, methods=['get'])
    def by_district(self, request):
        """Get constituencies grouped by district"""
        district_name = request.query_params.get('district')
        if district_name:
            constituencies = self.queryset.filter(district__name__iexact=district_name)
        else:
            constituencies = self.queryset.all()
        
        serializer = self.get_serializer(constituencies, many=True)
        return Response(serializer.data)


class PartyViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for parties"""
    queryset = Party.objects.select_related('alliance').all()
    serializer_class = PartySerializer


class DistrictViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for districts"""
    queryset = District.objects.all()
    serializer_class = DistrictSerializer


@api_view(['GET'])
def state_summary(request):
    """
    State-level summary with live aggregates
    GET /api/summary/
    """
    live_results = LiveResult.objects.all()
    candidates = Candidate.objects.select_related('party', 'party__alliance')
    
    alliance_seats = {
        'UDF': {'won': 0, 'leading': 0, 'trailing': 0},
        'LDF': {'won': 0, 'leading': 0, 'trailing': 0},
        'NDA': {'won': 0, 'leading': 0, 'trailing': 0},
        'OTH': {'won': 0, 'leading': 0, 'trailing': 0},
    }
    ind_summary = {'won': 0, 'leading': 0}

    constituencies = Constituency.objects.prefetch_related(
        Prefetch(
            'candidates_2026',
            queryset=Candidate.objects.select_related('party', 'party__alliance').order_by('-votes'),
            to_attr='prefetched_candidates'
        ),
        Prefetch(
            'live_results',
            to_attr='prefetched_live_results'
        )
    ).all()

    for constituency in constituencies:
        top_candidates = constituency.prefetched_candidates[:2]
        if top_candidates:
            leader = top_candidates[0]
            alliance = leader.party.alliance.code
            party_code = leader.party.code

            result = constituency.prefetched_live_results[0] if constituency.prefetched_live_results else None
            if result and result.status == 'RESULT_DECLARED':
                alliance_seats[alliance]['won'] += 1
                if party_code == 'IND':
                    ind_summary['won'] += 1
            elif result and result.status == 'IN_PROGRESS' and leader.votes > 0:
                alliance_seats[alliance]['leading'] += 1
                if party_code == 'IND':
                    ind_summary['leading'] += 1

    total_votes_counted = candidates.aggregate(Sum('votes'))['votes__sum'] or 0

    for c in candidates:
        alliance = c.party.alliance.code if c.party and c.party.alliance else 'OTH'
        bucket = alliance if alliance in alliance_seats else 'OTH'
        alliance_seats[bucket]['votes'] = alliance_seats[bucket].get('votes', 0) + c.votes

    for al in alliance_seats:
        votes = alliance_seats[al].get('votes', 0)
        alliance_seats[al]['vote_share'] = (votes / total_votes_counted * 100) if total_votes_counted > 0 else 0
        alliance_seats[al].pop('votes', None)

    return Response({
        'total_constituencies': 140,
        'results_declared': live_results.filter(status='RESULT_DECLARED').count(),
        'counting_in_progress': live_results.filter(status='IN_PROGRESS').count(),
        'not_started': live_results.filter(status='NOT_STARTED').count(),
        'alliance_summary': alliance_seats,
        'ind_summary': ind_summary,
        'total_votes_counted': total_votes_counted,
        'total_votes_polled': live_results.aggregate(Sum('votes_polled'))['votes_polled__sum'] or 0,
    })


@api_view(['GET'])
def historical_comparison(request, constituency_number):
    """
    Historical comparison for a constituency
    GET /api/historical/{constituency_number}/
    """
    try:
        constituency = Constituency.objects.get(number=constituency_number)
    except Constituency.DoesNotExist:
        return Response({'error': 'Constituency not found'}, status=404)
    
    results_2021 = constituency.results_2021.select_related('party').order_by('-total_votes')
    meta_2021 = constituency.meta_2021 if hasattr(constituency, 'meta_2021') else None
    
    ls_2019 = ParliamentResult.objects.filter(year=2019, constituency=constituency).first()
    ls_2024 = ParliamentResult.objects.filter(year=2024, constituency=constituency).first()
    
    result_2016 = constituency.results_2016.select_related('winner_party', 'winner_alliance').first()
    la_2016 = None
    if result_2016:
        am2016 = _build_alliance_map(2016)
        shares_2016 = {'LDF': 0.0, 'UDF': 0.0, 'NDA': 0.0, 'OTH': 0.0}
        results_2016_full = list(
            constituency.results_2016_full.select_related('party').order_by('-total_votes')
        )
        for r in results_2016_full:
            pc = r.party.code if r.party else r.party_code
            al = _party_alliance(pc, am2016)
            bucket = al if al in shares_2016 else 'OTH'
            shares_2016[bucket] += float(r.vote_percentage)

        wp = result_2016.winner_party
        wa = result_2016.winner_alliance
        rp = result_2016.runnerup_party
        ra = result_2016.runnerup_alliance

        la_2016 = {
            'winner_candidate':    result_2016.winner_candidate,
            'winner_party':        wp.code if wp else result_2016.winner_party_code,
            'winner_alliance':     wa.code if wa else result_2016.winner_alliance_code,
            'winner_votes':        result_2016.winner_votes,
            'winner_percentage':   float(result_2016.winner_percentage),
            'runnerup_candidate':  result_2016.runnerup_candidate,
            'runnerup_party':      rp.code if rp else result_2016.runnerup_party_code,
            'runnerup_alliance':   ra.code if ra else result_2016.runnerup_alliance_code,
            'runnerup_votes':      result_2016.runnerup_votes,
            'runnerup_percentage': float(result_2016.runnerup_percentage),
            'margin':              result_2016.margin,
            'alliance_shares': {k: round(v, 2) for k, v in shares_2016.items()},
            'candidates': [
                {
                    'candidate': r.candidate_name,
                    'party': r.party.code if r.party else r.party_code,
                    'votes': r.total_votes,
                    'percentage': float(r.vote_percentage),
                    'is_winner': r.is_winner,
                    'alliance': _party_alliance(r.party.code if r.party else r.party_code, am2016),
                    'color_code': _party_color(r.party.code if r.party else r.party_code, am2016),
                } for r in results_2016_full
                if (r.party.code if r.party else r.party_code) != 'NOTA'
            ],
        }

    am2021 = _build_alliance_map(2021)
    all_2021 = constituency.results_2021.select_related('party').all()
    shares_2021 = {'LDF': 0.0, 'UDF': 0.0, 'NDA': 0.0, 'OTH': 0.0}
    for r in all_2021:
        pc = r.party.code if r.party else r.party_code
        al = _party_alliance(pc, am2021)
        bucket = al if al in shares_2021 else 'OTH'
        shares_2021[bucket] += float(r.vote_percentage)

    am2011 = _build_alliance_map(2011)
    results_2011 = list(constituency.results_2011.select_related('party').order_by('-total_votes'))
    la_2011 = None
    if results_2011:
        shares_2011 = {'LDF': 0.0, 'UDF': 0.0, 'NDA': 0.0, 'OTH': 0.0}
        for r in results_2011:
            pc = r.party.code if r.party else r.party_code
            al = _party_alliance(pc, am2011)
            bucket = al if al in shares_2011 else 'OTH'
            shares_2011[bucket] += float(r.vote_percentage)
        
        la_2011 = {
            'margin': results_2011[0].total_votes - results_2011[1].total_votes if len(results_2011) > 1 else None,
            'alliance_shares': {k: round(v, 2) for k, v in shares_2011.items()},
            'candidates': [
                {
                    'candidate': r.candidate_name,
                    'party': r.party.code if r.party else r.party_code,
                    'votes': r.total_votes,
                    'percentage': float(r.vote_percentage),
                    'is_winner': r.is_winner,
                    'alliance': _party_alliance(r.party.code if r.party else r.party_code, am2011),
                    'color_code': _party_color(r.party.code if r.party else r.party_code, am2011),
                } for r in results_2011
                if (r.party.code if r.party else r.party_code) != 'NOTA'
            ]
        }

    return Response({
        'constituency': {
            'number': constituency.number,
            'name': constituency.name,
            'district': constituency.district.name,
        },
        'la_2021': {
            'winner': meta_2021.winner_name if meta_2021 else None,
            'party': meta_2021.winner_party.code if meta_2021 and meta_2021.winner_party else None,
            'margin': meta_2021.margin if meta_2021 else None,
            'alliance_shares': {k: round(v, 2) for k, v in shares_2021.items()},
            'candidates': [
                {
                    'candidate': r.candidate_name,
                    'party': r.party.code if r.party else r.party_code,
                    'votes': r.total_votes,
                    'percentage': float(r.vote_percentage),
                    'is_winner': r.is_winner,
                    'alliance': _party_alliance(r.party.code if r.party else r.party_code, am2021),
                    'color_code': _party_color(r.party.code if r.party else r.party_code, am2021),
                } for r in results_2021
            ],
        },
        'la_2016': la_2016,
        'la_2011': la_2011,
        'ls_2019': ParliamentResultSerializer(ls_2019).data if ls_2019 else None,
        'ls_2024': ParliamentResultSerializer(ls_2024).data if ls_2024 else None,
    })


@api_view(['GET'])
def history_all(request):
    """
    Bulk historical endpoint -- returns all 140 constituencies with
    la_2011, la_2016, la_2021 winner/margin/alliance summary.
    GET /api/history/all/
    """
    am2011 = _build_alliance_map(2011)
    am2016 = _build_alliance_map(2016)
    am2021 = _build_alliance_map(2021)

    constituencies = (
        Constituency.objects
        .select_related('district', 'meta_2021', 'meta_2021__winner_party')
        .prefetch_related(
            Prefetch('results_2011', queryset=HistoricalResult2011.objects.select_related('party').order_by('-total_votes')),
            Prefetch('results_2016', queryset=HistoricalResult2016.objects.select_related('winner_party', 'winner_alliance')),
            Prefetch('results_2021', queryset=HistoricalResult2021.objects.select_related('party').order_by('-total_votes')),
            'parliament_results'
        )
        .order_by('number')
    )

    results = []
    for c in constituencies:
        r11_list = list(c.results_2011.all())
        la_2011 = None
        if r11_list:
            winner_r11 = next((r for r in r11_list if r.is_winner), r11_list[0])
            pc = winner_r11.party.code if winner_r11.party else winner_r11.party_code
            margin_11 = (
                r11_list[0].total_votes - r11_list[1].total_votes
                if len(r11_list) > 1 else None
            )
            la_2011 = {
                'winner': winner_r11.candidate_name,
                'winner_party': pc,
                'winner_alliance': _party_alliance(pc, am2011),
                'margin': margin_11,
            }

        r16 = list(c.results_2016.all())
        la_2016 = None
        if r16:
            r = r16[0]
            wp_code = r.winner_party.code if r.winner_party else r.winner_party_code
            la_2016 = {
                'winner': r.winner_candidate,
                'winner_party': wp_code,
                'winner_alliance': _party_alliance(wp_code, am2016),
                'margin': r.margin,
            }

        meta21 = getattr(c, 'meta_2021', None)
        r21_list = list(c.results_2021.all())
        la_2021 = None
        if meta21 and meta21.winner_name:
            margin_21 = (
                r21_list[0].total_votes - r21_list[1].total_votes
                if len(r21_list) > 1 else meta21.margin
            )
            wp_code = meta21.winner_party.code if meta21.winner_party else meta21.winner_party_code
            la_2021 = {
                'winner': meta21.winner_name,
                'winner_party': wp_code,
                'winner_alliance': _party_alliance(wp_code, am2021),
                'margin': margin_21,
            }

        parliament_results = list(c.parliament_results.all())
        ls_2019_obj = next((r for r in parliament_results if r.year == 2019), None)
        ls_2024_obj = next((r for r in parliament_results if r.year == 2024), None)
        
        ls_2019 = {
            'winner': '', 'winner_party': '',
            'winner_alliance': ls_2019_obj.lead_alliance,
            'margin': ls_2019_obj.margin,
        } if ls_2019_obj else None
            
        ls_2024 = {
            'winner': '', 'winner_party': '',
            'winner_alliance': ls_2024_obj.lead_alliance,
            'margin': ls_2024_obj.margin,
        } if ls_2024_obj else None

        results.append({
            'constituency_number': c.number,
            'constituency_name': c.name,
            'district': c.district.name,
            'la_2011': la_2011,
            'la_2016': la_2016,
            'la_2021': la_2021,
            'ls_2019': ls_2019,
            'ls_2024': ls_2024,
        })

    return Response(results)


@api_view(['GET'])
def alliance_detail(request, alliance_code):
    """
    Get detailed breakdown for an alliance — includes seat movement, swing analysis,
    vote share vs 2021, and the full 140-constituency list annotated with competing flag.
    GET /api/alliance/{alliance_code}/
    """
    alliance_code = alliance_code.upper()
    if alliance_code not in ['LDF', 'UDF', 'NDA', 'OTH']:
        return Response({'error': 'Invalid alliance code'}, status=404)

    party_ids = list(PartyAllianceYear.objects.filter(
        election_year=2026, election_type='LA', alliance__code=alliance_code
    ).values_list('party_id', flat=True))
    party_ids_set = set(party_ids)

    # 1. Total valid votes (state-wide)
    total_valid_votes = Candidate.objects.aggregate(t=Sum('votes'))['t'] or 0

    # 2. Alliance total votes (2026)
    alliance_votes = Candidate.objects.filter(
        party_id__in=party_ids
    ).aggregate(t=Sum('votes'))['t'] or 0
    vote_share = (alliance_votes / total_valid_votes * 100) if total_valid_votes > 0 else 0

    # 3. 2021 totals for comparison
    total_2021 = HistoricalResult2021.objects.aggregate(t=Sum('total_votes'))['t'] or 0
    am2021 = _build_alliance_map(2021)
    am2026 = _build_alliance_map(2026)

    votes_2021_alliance = 0
    party_2021_votes = {}
    for r in HistoricalResult2021.objects.select_related('party').all():
        pc = r.party.code if r.party else r.party_code
        party_2021_votes[pc] = party_2021_votes.get(pc, 0) + r.total_votes
        if _party_alliance(pc, am2021) == alliance_code:
            votes_2021_alliance += r.total_votes
    vote_share_2021 = (votes_2021_alliance / total_2021 * 100) if total_2021 > 0 else 0

    # 4. Per-party breakdown init
    party_stats = {}
    for c in Candidate.objects.filter(party_id__in=party_ids).select_related('party'):
        pc = c.party.code
        if pc not in party_stats:
            party_stats[pc] = {
                'code': pc, 'name': c.party.full_name, 'color': c.party.color_code,
                'contested': 0, 'won': 0, 'leading': 0, 'votes': 0, 'constituency_ids': [],
                'seats_2nd': 0, 'seats_close_3rd': 0, 'seats_distant_3rd': 0,
            }
        party_stats[pc]['contested'] += 1
        party_stats[pc]['constituency_ids'].append(c.constituency_id)
        party_stats[pc]['votes'] += c.votes

    # 5. Seat movement vs 2021 + swing analysis + won/leading tally
    gained = held = lost = 0
    pushed_to_3rd = pulled_up_to_2nd = 0
    seats_2nd = seats_close_3rd = seats_distant_3rd = 0
    swing_gained_from = {'LDF': 0, 'UDF': 0, 'NDA': 0, 'OTH': 0}
    swing_lost_to = {'LDF': 0, 'UDF': 0, 'NDA': 0, 'OTH': 0}

    for meta in ConstituencyMeta2021.objects.select_related(
        'winner_party', 'constituency'
    ).prefetch_related(
        'constituency__candidates_2026', 'constituency__candidates_2026__party',
        'constituency__live_results', 'constituency__results_2021', 'constituency__results_2021__party'
    ).all():
        wp = meta.winner_party.code if meta.winner_party else None
        sitting_al = _party_alliance(wp, am2021) if wp else 'OTH'
        cands_2026 = list(meta.constituency.candidates_2026.order_by('-votes'))
        if not cands_2026 or cands_2026[0].votes == 0:
            continue
        live = meta.constituency.live_results.first()
        if not live or live.status == 'NOT_STARTED':
            continue

        # Get current alliance position
        current_pos = None
        for i, cand in enumerate(cands_2026):
            if _party_alliance(cand.party.code, am2026) == alliance_code:
                current_pos = i + 1
                break
                
        # Get 2021 position
        r21_list = list(meta.constituency.results_2021.all().order_by('-total_votes'))
        pos_2021 = None
        for i, r in enumerate(r21_list):
            pc = r.party.code if r.party else r.party_code
            if _party_alliance(pc, am2021) == alliance_code:
                pos_2021 = i + 1
                break
                
        if current_pos == 2:
            seats_2nd += 1
        elif current_pos == 3:
            if cands_2026[1].votes - cands_2026[2].votes < 10000:
                seats_close_3rd += 1
            else:
                seats_distant_3rd += 1
            
        if current_pos == 3 and pos_2021 in (1, 2):
            pushed_to_3rd += 1
        if current_pos == 2 and (pos_2021 is None or pos_2021 > 2):
            pulled_up_to_2nd += 1

        current_al = _party_alliance(cands_2026[0].party.code, am2026)

        if current_al == alliance_code:
            top_pc = cands_2026[0].party.code
            if top_pc in party_stats:
                if live.status in ('RESULT_DECLARED', 'COMPLETED'):
                    party_stats[top_pc]['won'] += 1
                else:
                    party_stats[top_pc]['leading'] += 1

            if sitting_al == alliance_code:
                held += 1
            else:
                gained += 1
                swing_gained_from[sitting_al if sitting_al in swing_gained_from else 'OTH'] += 1
        elif sitting_al == alliance_code:
            lost += 1
            swing_lost_to[current_al if current_al in swing_lost_to else 'OTH'] += 1

        # Track 2nd and 3rd per party
        if current_pos in (2, 3):
            # Find the party in this alliance at this position
            target_cand = cands_2026[current_pos-1]
            target_pc = target_cand.party.code
            if target_pc in party_stats:
                if current_pos == 2:
                    party_stats[target_pc]['seats_2nd'] += 1
                else:
                    if cands_2026[1].votes - cands_2026[2].votes < 10000:
                        party_stats[target_pc]['seats_close_3rd'] += 1
                    else:
                        party_stats[target_pc]['seats_distant_3rd'] += 1

    parties_data = []
    for p in party_stats.values():
        v21 = party_2021_votes.get(p['code'], 0)
        
        c_ids_26 = p['constituency_ids']
        total_valid_26_contested = Candidate.objects.filter(constituency_id__in=c_ids_26).aggregate(t=Sum('votes'))['t'] or 0
        vote_share_26 = (p['votes'] / total_valid_26_contested * 100) if total_valid_26_contested > 0 else 0
        
        c_ids_21 = HistoricalResult2021.objects.filter(
            Q(party__code=p['code']) | Q(party_code=p['code'])
        ).values_list('constituency_id', flat=True)
        
        if c_ids_21:
            total_valid_21_contested = HistoricalResult2021.objects.filter(constituency_id__in=c_ids_21).aggregate(t=Sum('total_votes'))['t'] or 0
            vote_share_21 = (v21 / total_valid_21_contested * 100) if total_valid_21_contested > 0 else 0
        else:
            vote_share_21 = 0

        parties_data.append({
            'code': p['code'], 'name': p['name'], 'color': p['color'],
            'contested': p['contested'], 'won': p['won'], 'leading': p['leading'],
            'seats_2nd': p['seats_2nd'],
            'seats_close_3rd': p['seats_close_3rd'],
            'seats_distant_3rd': p['seats_distant_3rd'],
            'vote_share': round(vote_share_26, 2),
            'vote_share_2021_pct': round(vote_share_21, 2),
        })
    parties_data.sort(key=lambda x: (x['won'] + x['leading'], x['vote_share']), reverse=True)

    total_won = sum(p['won'] for p in parties_data)
    total_leading = sum(p['leading'] for p in parties_data)
    total_contested = sum(p['contested'] for p in parties_data)

    # 6. Best/worst margins (alliance leading seats only)
    best_margin = worst_margin = None
    best_val, worst_val = -1, 10**9
    for const in Constituency.objects.prefetch_related(
        'candidates_2026', 'candidates_2026__party', 'live_results'
    ).all():
        live = const.live_results.first()
        if not live or live.status not in ('IN_PROGRESS', 'RESULT_DECLARED', 'COMPLETED'):
            continue
        top2 = list(const.candidates_2026.order_by('-votes')[:2])
        if len(top2) < 2 or top2[0].votes == 0:
            continue
        if top2[0].party_id not in party_ids_set:
            continue
        margin = top2[0].votes - top2[1].votes
        if margin > best_val:
            best_val = margin
            best_margin = {'constituency': const.name, 'margin': margin}
        if margin < worst_val:
            worst_val = margin
            worst_margin = {'constituency': const.name, 'margin': margin}

    # 7. All 140 constituencies annotated with competing=True/False
    all_consts = list(Constituency.objects.select_related(
        'district', 'meta_2021', 'meta_2021__winner_party'
    ).prefetch_related(
        'candidates_2026', 'candidates_2026__party', 'live_results', 'results_2021'
    ).order_by('number'))

    competing_ids = set(
        Candidate.objects.filter(party_id__in=party_ids_set).values_list('constituency_id', flat=True)
    )

    consts_data = []
    for c, item in zip(all_consts, ConstituencyListSerializer(all_consts, many=True).data):
        item = dict(item)
        item['competing'] = item['id'] in competing_ids
        
        cands = list(c.candidates_2026.order_by('-votes'))
        alliance_pos = None
        margin_to_second = None
        alliance_votes_cand = 0
        alliance_candidate_name = None
        alliance_party_code = None
        for i, cand in enumerate(cands):
            if _party_alliance(cand.party.code, am2026) == alliance_code:
                alliance_pos = i + 1
                alliance_votes_cand = cand.votes
                alliance_candidate_name = cand.name
                alliance_party_code = cand.party.code
                break
        if len(cands) >= 3:
            margin_to_second = cands[1].votes - cands[2].votes
            
        item['alliance_pos'] = alliance_pos
        item['margin_to_second'] = margin_to_second
        item['alliance_votes'] = alliance_votes_cand
        item['alliance_candidate_name'] = alliance_candidate_name
        item['alliance_party_code'] = alliance_party_code
        consts_data.append(item)

    return Response({
        'alliance': alliance_code,
        'seats_won': total_won,
        'seats_leading': total_leading,
        'seats_2nd': seats_2nd,
        'seats_close_3rd': seats_close_3rd,
        'seats_distant_3rd': seats_distant_3rd,
        'seats_trailing': total_contested - total_won - total_leading,
        'seats_contested': total_contested,
        'total_votes': alliance_votes,
        'vote_share': round(vote_share, 2),
        'vote_share_2021_pct': round(vote_share_2021, 2),
        'best_margin': best_margin,
        'worst_margin': worst_margin,
        'seat_movement': {
            'gained': gained, 
            'held': held, 
            'lost': lost,
            'pushed_to_3rd': pushed_to_3rd,
            'pulled_up_to_2nd': pulled_up_to_2nd
        },
        'swing_analysis': {'gained_from': swing_gained_from, 'lost_to': swing_lost_to},
        'parties': parties_data,
        'constituencies': consts_data,
    })


@api_view(['GET'])
def party_detail(request, party_code):
    """
    Get detailed breakdown for a specific party — includes 2021 vote share
    and the scoped list of constituencies this party is contesting.
    GET /api/party/{party_code}/
    """
    try:
        party = Party.objects.select_related('alliance').get(code=party_code)
    except Party.DoesNotExist:
        return Response({'error': 'Party not found'}, status=404)

    candidates = Candidate.objects.filter(party=party).select_related('constituency')
    party_votes = candidates.aggregate(t=Sum('votes'))['t'] or 0
    
    contested_ids = list(candidates.values_list('constituency_id', flat=True))
    total_valid_votes_contested = Candidate.objects.filter(constituency_id__in=contested_ids).aggregate(t=Sum('votes'))['t'] or 0
    vote_share = (party_votes / total_valid_votes_contested * 100) if total_valid_votes_contested > 0 else 0

    pay = PartyAllianceYear.objects.select_related('alliance').filter(
        party=party, election_year=2026, election_type='LA'
    ).first()
    alliance = pay.alliance.code if pay else party.alliance.code

    contested = candidates.count()

    # 2021 vote share for this party
    votes_2021 = HistoricalResult2021.objects.filter(party=party).aggregate(t=Sum('total_votes'))['t'] or 0
    c_ids_21 = HistoricalResult2021.objects.filter(party=party).values_list('constituency_id', flat=True)
    total_2021_contested = HistoricalResult2021.objects.filter(constituency_id__in=c_ids_21).aggregate(t=Sum('total_votes'))['t'] or 0
    vote_share_2021 = (votes_2021 / total_2021_contested * 100) if total_2021_contested > 0 else 0

    # Constituencies this party is contesting (scoped list)
    contested_ids = list(candidates.values_list('constituency_id', flat=True))
    scoped_consts = Constituency.objects.filter(id__in=contested_ids).select_related(
        'district', 'meta_2021', 'meta_2021__winner_party'
    ).prefetch_related(
        'candidates_2026', 'candidates_2026__party', 'live_results', 'results_2021'
    ).order_by('number')

    won = 0
    leading = 0
    seats_2nd = 0
    seats_close_3rd = 0
    seats_distant_3rd = 0
    for c in scoped_consts:
        cands = list(c.candidates_2026.order_by('-votes'))
        current_pos = None
        for i, cand in enumerate(cands):
            if cand.party == party:
                current_pos = i + 1
                break
                
        if current_pos == 1:
            live = c.live_results.first()
            if live and live.status in ('RESULT_DECLARED', 'COMPLETED'):
                won += 1
            elif live and live.status == 'IN_PROGRESS':
                leading += 1
        elif current_pos == 2:
            seats_2nd += 1
        elif current_pos == 3:
            if cands[1].votes - cands[2].votes < 10000:
                seats_close_3rd += 1
            else:
                seats_distant_3rd += 1

    consts_data = []
    for c, item in zip(scoped_consts, ConstituencyListSerializer(scoped_consts, many=True).data):
        item = dict(item)
        cands = list(c.candidates_2026.order_by('-votes'))
        party_pos = None
        margin_to_second = None
        party_votes_cand = 0
        party_candidate_name = None
        for i, cand in enumerate(cands):
            if cand.party == party:
                party_pos = i + 1
                party_votes_cand = cand.votes
                party_candidate_name = cand.name
                break
        if len(cands) >= 3:
            margin_to_second = cands[1].votes - cands[2].votes
            
        item['party_pos'] = party_pos
        item['margin_to_second'] = margin_to_second
        item['party_votes'] = party_votes_cand
        item['party_candidate_name'] = party_candidate_name
        consts_data.append(item)

    return Response({
        'code': party.code,
        'full_name': party.full_name,
        'alliance': alliance,
        'color_code': party.color_code,
        'seats_contested': contested,
        'seats_won': won,
        'seats_leading': leading,
        'seats_2nd': seats_2nd,
        'seats_close_3rd': seats_close_3rd,
        'seats_distant_3rd': seats_distant_3rd,
        'seats_trailing': contested - won - leading,
        'total_votes': party_votes,
        'vote_share': round(vote_share, 2),
        'vote_share_2021_pct': round(vote_share_2021, 2),
        'constituencies': consts_data,
    })
