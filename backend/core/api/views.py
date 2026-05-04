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
    
    # Count seats by alliance; also track pure IND (party code exactly 'IND') separately
    alliance_seats = {
        'UDF': {'won': 0, 'leading': 0, 'trailing': 0},
        'LDF': {'won': 0, 'leading': 0, 'trailing': 0},
        'NDA': {'won': 0, 'leading': 0, 'trailing': 0},
        'OTH': {'won': 0, 'leading': 0, 'trailing': 0},
    }
    ind_summary = {'won': 0, 'leading': 0}

    for constituency in Constituency.objects.all():
        top_candidates = constituency.candidates_2026.select_related('party', 'party__alliance').order_by('-votes')[:2]
        if top_candidates:
            leader = top_candidates[0]
            alliance = leader.party.alliance.code
            party_code = leader.party.code

            result = constituency.live_results.first()
            if result and result.status == 'RESULT_DECLARED':
                alliance_seats[alliance]['won'] += 1
                if party_code == 'IND':
                    ind_summary['won'] += 1
            elif result and result.status == 'IN_PROGRESS' and leader.votes > 0:
                alliance_seats[alliance]['leading'] += 1
                if party_code == 'IND':
                    ind_summary['leading'] += 1

    total_votes_counted = candidates.aggregate(Sum('votes'))['votes__sum'] or 0

    # Aggregate votes per alliance
    for c in candidates:
        alliance = c.party.alliance.code if c.party and c.party.alliance else 'OTH'
        bucket = alliance if alliance in alliance_seats else 'OTH'
        alliance_seats[bucket]['votes'] = alliance_seats[bucket].get('votes', 0) + c.votes

    # Calculate vote share
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
    
    # 2021 LA results -- all candidates
    results_2021 = constituency.results_2021.select_related('party').order_by('-total_votes')
    meta_2021 = constituency.meta_2021 if hasattr(constituency, 'meta_2021') else None
    
    # Parliament results
    ls_2019 = ParliamentResult.objects.filter(year=2019, constituency=constituency).first()
    ls_2024 = ParliamentResult.objects.filter(year=2024, constituency=constituency).first()
    
    # 2016 LA results -- winner + runner-up summary
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

    # 2021
    am2021 = _build_alliance_map(2021)
    all_2021 = constituency.results_2021.select_related('party').all()
    shares_2021 = {'LDF': 0.0, 'UDF': 0.0, 'NDA': 0.0, 'OTH': 0.0}
    for r in all_2021:
        pc = r.party.code if r.party else r.party_code
        al = _party_alliance(pc, am2021)
        bucket = al if al in shares_2021 else 'OTH'
        shares_2021[bucket] += float(r.vote_percentage)

    # 2011
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
        # 2011
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

        # 2016
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

        # 2021
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

        # LS 2019 / 2024
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
    Get detailed breakdown for an alliance
    GET /api/alliance/{alliance_code}/
    """
    if alliance_code not in ['LDF', 'UDF', 'NDA', 'OTH']:
        return Response({'error': 'Invalid alliance code'}, status=404)

    party_ids = PartyAllianceYear.objects.filter(
        election_year=2026, election_type='LA', alliance__code=alliance_code
    ).values_list('party_id', flat=True)

    # 1. Total valid votes across the state (for vote share percentage)
    total_valid_votes = Candidate.objects.aggregate(t=Sum('votes'))['t'] or 0

    # 2. Total votes for the alliance
    alliance_votes = Candidate.objects.filter(
        party_id__in=party_ids
    ).aggregate(t=Sum('votes'))['t'] or 0

    vote_share = (alliance_votes / total_valid_votes * 100) if total_valid_votes > 0 else 0

    # 3. Component parties breakdown
    parties_data = []
    alliance_candidates = Candidate.objects.filter(
        party_id__in=party_ids
    ).select_related('party', 'party__alliance')

    # Group by party
    party_stats = {}
    for c in alliance_candidates:
        pc = c.party.code
        if pc not in party_stats:
            party_stats[pc] = {
                'code': pc,
                'name': c.party.full_name,
                'color': c.party.color_code,
                'contested': 0,
                'won': 0,
                'leading': 0,
                'votes': 0,
            }
        
        party_stats[pc]['contested'] += 1
        if c.is_winner:
            party_stats[pc]['won'] += 1
        elif c.is_leading:
            party_stats[pc]['leading'] += 1
        party_stats[pc]['votes'] += c.votes

    for p in party_stats.values():
        p['vote_share'] = (p['votes'] / total_valid_votes * 100) if total_valid_votes > 0 else 0
        parties_data.append(p)

    # Sort parties by seats won/leading, then votes
    parties_data.sort(key=lambda x: (x['won'] + x['leading'], x['votes']), reverse=True)

    total_won = sum(p['won'] for p in parties_data)
    total_leading = sum(p['leading'] for p in parties_data)

    return Response({
        'alliance': alliance_code,
        'seats_won': total_won,
        'seats_leading': total_leading,
        'total_votes': alliance_votes,
        'vote_share': vote_share,
        'parties': parties_data,
    })


@api_view(['GET'])
def party_detail(request, party_code):
    """
    Get detailed breakdown for a specific party
    GET /api/party/{party_code}/
    """
    try:
        party = Party.objects.select_related('alliance').get(code=party_code)
    except Party.DoesNotExist:
        return Response({'error': 'Party not found'}, status=404)

    total_valid_votes = Candidate.objects.aggregate(t=Sum('votes'))['t'] or 0

    candidates = Candidate.objects.filter(party=party).select_related('constituency')
    party_votes = candidates.aggregate(t=Sum('votes'))['t'] or 0
    vote_share = (party_votes / total_valid_votes * 100) if total_valid_votes > 0 else 0

    # Get alliance for the year 2026
    pay = PartyAllianceYear.objects.select_related('alliance').filter(
        party=party, election_year=2026, election_type='LA'
    ).first()
    alliance = pay.alliance.code if pay else party.alliance.code

    # Seats breakdown
    won = candidates.filter(is_winner=True).count()
    leading = candidates.filter(is_leading=True).count()
    contested = candidates.count()

    return Response({
        'code': party.code,
        'full_name': party.full_name,
        'alliance': alliance,
        'color_code': party.color_code,
        'seats_contested': contested,
        'seats_won': won,
        'seats_leading': leading,
        'total_votes': party_votes,
        'vote_share': vote_share,
    })
