from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from core.models import (
    District, Constituency, Party, Candidate, LiveResult,
    HistoricalResult2021, HistoricalResult2016, HistoricalResult2016Full,
    ParliamentResult, PartyAllianceYear
)
from core.api.serializers import (
    DistrictSerializer, ConstituencyListSerializer, ConstituencyDetailSerializer,
    PartySerializer, ParliamentResultSerializer
)

# Constituency-specific alliance overrides for 2016 ECI data
# where the same party code was reused for different factional parties.
CONSTITUENCY_2016_OVERRIDE: dict[int, dict[str, str]] = {
    117: {'CMPKSC': 'LDF'},  # Chavara: CMP(Aravindakshan) → LDF
}


class ConstituencyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for constituencies
    List view: lightweight data for all 140 constituencies
    Detail view: full data including candidates and historical results
    """
    queryset = Constituency.objects.select_related('district').prefetch_related(
        'candidates_2026', 'candidates_2026__party', 'live_results', 'results_2021'
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
    queryset = Party.objects.all()
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
    candidates = Candidate.objects.select_related('party')
    
    # Count seats by alliance; also track pure IND (party code exactly 'IND') separately
    alliance_seats = {
        'UDF': {'won': 0, 'leading': 0, 'trailing': 0},
        'LDF': {'won': 0, 'leading': 0, 'trailing': 0},
        'NDA': {'won': 0, 'leading': 0, 'trailing': 0},
        'OTH': {'won': 0, 'leading': 0, 'trailing': 0},
    }
    ind_summary = {'won': 0, 'leading': 0}

    for constituency in Constituency.objects.all():
        top_candidates = constituency.candidates_2026.select_related('party').order_by('-votes')[:2]
        if top_candidates:
            leader = top_candidates[0]
            alliance = leader.party.alliance
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

    return Response({
        'total_constituencies': 140,
        'results_declared': live_results.filter(status='RESULT_DECLARED').count(),
        'counting_in_progress': live_results.filter(status='IN_PROGRESS').count(),
        'not_started': live_results.filter(status='NOT_STARTED').count(),
        'alliance_summary': alliance_seats,
        'ind_summary': ind_summary,
        'total_votes_counted': candidates.aggregate(Sum('votes'))['votes__sum'] or 0,
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
    
    # 2021 LA results — all candidates
    results_2021 = constituency.results_2021.order_by('-total_votes')
    meta_2021 = constituency.meta_2021 if hasattr(constituency, 'meta_2021') else None
    
    # Parliament results
    ls_2019 = ParliamentResult.objects.filter(year=2019, constituency=constituency).first()
    ls_2024 = ParliamentResult.objects.filter(year=2024, constituency=constituency).first()
    
    # 2016 LA results — winner + runner-up summary
    result_2016 = constituency.results_2016.first()
    la_2016 = None
    if result_2016:
        # Build alliance-level vote-share aggregates from ALL 2016 candidates
        # (uses HistoricalResult2016Full which has every candidate from the xlsx)
        alliance_map_2016 = {
            r.party_code: {'alliance': r.alliance, 'color_code': r.color_code}
            for r in PartyAllianceYear.objects.filter(election_year=2016, election_type='LA')
        }
        shares_2016: dict = {'LDF': 0.0, 'UDF': 0.0, 'NDA': 0.0, 'OTH': 0.0}
        for r in constituency.results_2016_full.all():
            al = alliance_map_2016.get(r.party_code, {}).get('alliance', 'OTH')
            bucket = al if al in shares_2016 else 'OTH'
            shares_2016[bucket] += float(r.vote_percentage)

        # All 2016 candidates for the card list
        results_2016_full = list(constituency.results_2016_full.order_by('-total_votes'))

        la_2016 = {
            'winner_candidate':    result_2016.winner_candidate,
            'winner_party':        result_2016.winner_party,
            'winner_alliance':     result_2016.winner_alliance,
            'winner_votes':        result_2016.winner_votes,
            'winner_percentage':   float(result_2016.winner_percentage),
            'runnerup_candidate':  result_2016.runnerup_candidate,
            'runnerup_party':      result_2016.runnerup_party,
            'runnerup_alliance':   result_2016.runnerup_alliance,
            'runnerup_votes':      result_2016.runnerup_votes,
            'runnerup_percentage': float(result_2016.runnerup_percentage),
            'margin':              result_2016.margin,
            'alliance_shares': {k: round(v, 2) for k, v in shares_2016.items()},
            'candidates': [
                {
                    'candidate': r.candidate_name,
                    'party': r.party_code,
                    'votes': r.total_votes,
                    'percentage': float(r.vote_percentage),
                    'is_winner': r.is_winner,
                    'alliance': CONSTITUENCY_2016_OVERRIDE.get(constituency.number, {}).get(r.party_code)
                               or alliance_map_2016.get(r.party_code, {}).get('alliance', 'OTH'),
                    'color_code': alliance_map_2016.get(r.party_code, {}).get('color_code', '#808080'),
                } for r in results_2016_full if r.party_code != 'NOTA'
            ],
        }

    # Build year-specific alliance lookup from PartyAllianceYear table
    alliance_map_2021 = {
        r.party_code: {'alliance': r.alliance, 'color_code': r.color_code}
        for r in PartyAllianceYear.objects.filter(election_year=2021, election_type='LA')
    }

    # 2021 alliance-level vote-share aggregates (all candidates, not just top-5)
    all_2021 = constituency.results_2021.all()
    shares_2021: dict = {'LDF': 0.0, 'UDF': 0.0, 'NDA': 0.0, 'OTH': 0.0}
    for r in all_2021:
        al = alliance_map_2021.get(r.party_code, {}).get('alliance', 'OTH')
        bucket = al if al in shares_2021 else 'OTH'
        shares_2021[bucket] += float(r.vote_percentage)

    return Response({
        'constituency': {
            'number': constituency.number,
            'name': constituency.name,
            'district': constituency.district.name,
        },
        'la_2021': {
            'winner': meta_2021.winner_name if meta_2021 else None,
            'party': meta_2021.winner_party if meta_2021 else None,
            'margin': meta_2021.margin if meta_2021 else None,
            'alliance_shares': {k: round(v, 2) for k, v in shares_2021.items()},
            'candidates': [
                {
                    'candidate': r.candidate_name,
                    'party': r.party_code,
                    'votes': r.total_votes,
                    'percentage': float(r.vote_percentage),
                    'is_winner': r.is_winner,
                    'alliance': alliance_map_2021.get(r.party_code, {}).get('alliance', 'OTH'),
                    'color_code': alliance_map_2021.get(r.party_code, {}).get('color_code', '#808080'),
                } for r in results_2021
            ],
        },
        'la_2016': la_2016,
        'ls_2019': ParliamentResultSerializer(ls_2019).data if ls_2019 else None,
        'ls_2024': ParliamentResultSerializer(ls_2024).data if ls_2024 else None,
    })
