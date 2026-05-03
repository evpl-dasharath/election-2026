from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.db.models import Sum, Count, Q, Prefetch
from core.models import (
    District, Constituency, Party, Candidate, LiveResult,
    HistoricalResult2021, HistoricalResult2016, HistoricalResult2016Full,
    HistoricalResult2011, ConstituencyMeta2021,
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
            al = (CONSTITUENCY_2016_OVERRIDE.get(constituency.number, {}).get(r.party_code)
                  or alliance_map_2016.get(r.party_code, {}).get('alliance', 'OTH'))
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

    # 2011 LA results
    alliance_map_2011 = {
        r.party_code: {'alliance': r.alliance, 'color_code': r.color_code}
        for r in PartyAllianceYear.objects.filter(election_year=2011, election_type='LA')
    }
    results_2011 = list(constituency.results_2011.order_by('-total_votes'))
    la_2011 = None
    if results_2011:
        shares_2011: dict = {'LDF': 0.0, 'UDF': 0.0, 'NDA': 0.0, 'OTH': 0.0}
        for r in results_2011:
            al = alliance_map_2011.get(r.party_code, {}).get('alliance', 'OTH')
            bucket = al if al in shares_2011 else 'OTH'
            shares_2011[bucket] += float(r.vote_percentage)
        
        la_2011 = {
            'margin': results_2011[0].total_votes - results_2011[1].total_votes if len(results_2011) > 1 else None,
            'alliance_shares': {k: round(v, 2) for k, v in shares_2011.items()},
            'candidates': [
                {
                    'candidate': r.candidate_name,
                    'party': r.party_code,
                    'votes': r.total_votes,
                    'percentage': float(r.vote_percentage),
                    'is_winner': r.is_winner,
                    'alliance': alliance_map_2011.get(r.party_code, {}).get('alliance', 'OTH'),
                    'color_code': alliance_map_2011.get(r.party_code, {}).get('color_code', '#808080'),
                } for r in results_2011 if r.party_code != 'NOTA'
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
        'la_2011': la_2011,
        'ls_2019': ParliamentResultSerializer(ls_2019).data if ls_2019 else None,
        'ls_2024': ParliamentResultSerializer(ls_2024).data if ls_2024 else None,
    })


@api_view(['GET'])
def history_all(request):
    """
    Bulk historical endpoint — returns all 140 constituencies with
    la_2011, la_2016, la_2021 winner/margin/alliance summary.
    GET /api/history/all/

    Shape matches ConstituencyHistory in HistoryPage.tsx:
      { constituency_number, constituency_name, district,
        la_2011: { winner, winner_party, winner_alliance, margin } | null,
        la_2016: { ... } | null,
        la_2021: { ... } | null }
    """
    # ── Build alliance lookup maps once ──────────────────────────────────
    def _alliance_map(year):
        return {
            r.party_code: r.alliance
            for r in PartyAllianceYear.objects.filter(election_year=year, election_type='LA')
        }

    am2011 = _alliance_map(2011)
    am2016 = _alliance_map(2016)
    am2021 = _alliance_map(2021)

    # ── Prefetch all historical data in bulk (3 queries total) ──────────
    constituencies = (
        Constituency.objects
        .select_related('district', 'meta_2021')
        .prefetch_related(
            Prefetch('results_2011', queryset=HistoricalResult2011.objects.order_by('-total_votes')),
            Prefetch('results_2016', queryset=HistoricalResult2016.objects.all()),
            Prefetch('results_2021', queryset=HistoricalResult2021.objects.order_by('-total_votes')),
            'parliament_results'
        )
        .order_by('number')
    )

    # 2016 override (Chavara factional CMP)
    OVERRIDE_2016 = {
        117: {'CMPKSC': 'LDF'},
    }

    def _winner_alliance(party_code, alliance_map, const_number=None, year_override=None):
        if year_override and const_number in year_override:
            overridden = year_override[const_number].get(party_code)
            if overridden:
                return overridden
        return alliance_map.get(party_code, 'OTH')

    results = []
    for c in constituencies:
        district_name = c.district.name

        # ── 2011 ─────────────────────────────────────────────────────────
        r11_list = list(c.results_2011.all())
        la_2011 = None
        if r11_list:
            winner_r11 = next((r for r in r11_list if r.is_winner), r11_list[0])
            margin_11 = (
                r11_list[0].total_votes - r11_list[1].total_votes
                if len(r11_list) > 1 else None
            )
            la_2011 = {
                'winner': winner_r11.candidate_name,
                'winner_party': winner_r11.party_code,
                'winner_alliance': _winner_alliance(winner_r11.party_code, am2011),
                'margin': margin_11,
            }

        # ── 2016 ─────────────────────────────────────────────────────────
        r16 = list(c.results_2016.all())
        la_2016 = None
        if r16:
            r = r16[0]
            la_2016 = {
                'winner': r.winner_candidate,
                'winner_party': r.winner_party,
                'winner_alliance': _winner_alliance(
                    r.winner_party, am2016, c.number, OVERRIDE_2016
                ) or r.winner_alliance,
                'margin': r.margin,
            }

        # ── 2021 ─────────────────────────────────────────────────────────
        meta21 = getattr(c, 'meta_2021', None)
        r21_list = list(c.results_2021.all())
        la_2021 = None
        if meta21 and meta21.winner_name:
            margin_21 = (
                r21_list[0].total_votes - r21_list[1].total_votes
                if len(r21_list) > 1 else meta21.margin
            )
            la_2021 = {
                'winner': meta21.winner_name,
                'winner_party': meta21.winner_party,
                'winner_alliance': _winner_alliance(meta21.winner_party, am2021),
                'margin': margin_21,
            }

        # ── LS 2019 / 2024 ───────────────────────────────────────────────
        parliament_results = list(c.parliament_results.all())
        ls_2019_obj = next((r for r in parliament_results if r.year == 2019), None)
        ls_2024_obj = next((r for r in parliament_results if r.year == 2024), None)
        
        ls_2019 = None
        if ls_2019_obj:
            ls_2019 = {
                'winner': '',
                'winner_party': '',
                'winner_alliance': ls_2019_obj.lead_alliance,
                'margin': ls_2019_obj.margin,
            }
            
        ls_2024 = None
        if ls_2024_obj:
            ls_2024 = {
                'winner': '',
                'winner_party': '',
                'winner_alliance': ls_2024_obj.lead_alliance,
                'margin': ls_2024_obj.margin,
            }

        results.append({
            'constituency_number': c.number,
            'constituency_name': c.name,
            'district': district_name,
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

    parties_in_alliance = PartyAllianceYear.objects.filter(
        election_year=2026, election_type='LA', alliance=alliance_code
    ).values_list('party_code', flat=True)

    # 1. Total valid votes across the state (for vote share percentage)
    total_valid_votes = Candidate.objects.aggregate(t=Sum('votes'))['t'] or 0

    # 2. Total votes for the alliance
    alliance_votes = Candidate.objects.filter(
        party__code__in=parties_in_alliance
    ).aggregate(t=Sum('votes'))['t'] or 0

    vote_share = (alliance_votes / total_valid_votes * 100) if total_valid_votes > 0 else 0

    # 3. Component parties breakdown
    parties_data = []
    alliance_candidates = Candidate.objects.filter(
        party__code__in=parties_in_alliance
    ).select_related('party')

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
        party = Party.objects.get(code=party_code)
    except Party.DoesNotExist:
        return Response({'error': 'Party not found'}, status=404)

    total_valid_votes = Candidate.objects.aggregate(t=Sum('votes'))['t'] or 0

    candidates = Candidate.objects.filter(party=party).select_related('constituency')
    party_votes = candidates.aggregate(t=Sum('votes'))['t'] or 0
    vote_share = (party_votes / total_valid_votes * 100) if total_valid_votes > 0 else 0

    # Get alliance for the year 2026
    pay = PartyAllianceYear.objects.filter(party_code=party_code, election_year=2026, election_type='LA').first()
    alliance = pay.alliance if pay else party.alliance

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
