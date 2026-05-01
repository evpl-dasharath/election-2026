from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from core.models import (
    District, Constituency, Party, Candidate, LiveResult,
    HistoricalResult2021, HistoricalResult2016, ParliamentResult,
    PartyAllianceYear
)
from core.api.serializers import (
    DistrictSerializer, ConstituencyListSerializer, ConstituencyDetailSerializer,
    PartySerializer, ParliamentResultSerializer
)


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
    
    # Count seats by alliance
    alliance_seats = {
        'UDF': {'won': 0, 'leading': 0, 'trailing': 0},
        'LDF': {'won': 0, 'leading': 0, 'trailing': 0},
        'NDA': {'won': 0, 'leading': 0, 'trailing': 0},
        'OTH': {'won': 0, 'leading': 0, 'trailing': 0},
    }
    
    for constituency in Constituency.objects.all():
        top_candidates = constituency.candidates_2026.select_related('party').order_by('-votes')[:2]
        if top_candidates:
            leader = top_candidates[0]
            alliance = leader.party.alliance
            
            result = constituency.live_results.first()
            if result and result.status == 'RESULT_DECLARED':
                alliance_seats[alliance]['won'] += 1
            elif result and result.status == 'IN_PROGRESS' and leader.votes > 0:
                alliance_seats[alliance]['leading'] += 1
    
    return Response({
        'total_constituencies': 140,
        'results_declared': live_results.filter(status='RESULT_DECLARED').count(),
        'counting_in_progress': live_results.filter(status='IN_PROGRESS').count(),
        'not_started': live_results.filter(status='NOT_STARTED').count(),
        'alliance_summary': alliance_seats,
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
    
    # 2021 LA results
    results_2021 = constituency.results_2021.order_by('-total_votes')[:5]
    meta_2021 = constituency.meta_2021 if hasattr(constituency, 'meta_2021') else None
    
    # Parliament results
    ls_2019 = ParliamentResult.objects.filter(year=2019, constituency=constituency).first()
    ls_2024 = ParliamentResult.objects.filter(year=2024, constituency=constituency).first()
    
    # 2016 LA results
    result_2016 = constituency.results_2016.first()
    la_2016 = None
    if result_2016:
        la_2016 = {
            'winner_candidate': result_2016.winner_candidate,
            'winner_party': result_2016.winner_party,
            'winner_alliance': result_2016.winner_alliance,
            'winner_votes': result_2016.winner_votes,
            'winner_percentage': float(result_2016.winner_percentage),
            'runnerup_candidate': result_2016.runnerup_candidate,
            'runnerup_party': result_2016.runnerup_party,
            'runnerup_alliance': result_2016.runnerup_alliance,
            'runnerup_votes': result_2016.runnerup_votes,
            'runnerup_percentage': float(result_2016.runnerup_percentage),
            'margin': result_2016.margin,
        }

    # Build year-specific alliance lookup from PartyAllianceYear table
    alliance_map_2021 = {
        r.party_code: {'alliance': r.alliance, 'color_code': r.color_code}
        for r in PartyAllianceYear.objects.filter(election_year=2021, election_type='LA')
    }

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
            'top_5': [
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
