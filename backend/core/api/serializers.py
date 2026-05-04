from rest_framework import serializers
from core.models import (
    District, Constituency, Party, Candidate, LiveResult,
    HistoricalResult2021, ConstituencyMeta2021, ParliamentResult,
    PartyAllianceYear
)
from django.db import models

# District → region mapping (matches frontend DISTRICT_REGION and export_json)
_DISTRICT_REGION = {
    'Kasaragod': 'north', 'Kannur': 'north', 'Wayanad': 'north', 'Kozhikode': 'north',
    'Malappuram': 'central_north', 'Palakkad': 'central_north', 'Thrissur': 'central_north',
    'Ernakulam': 'south_central', 'Idukki': 'south_central',
    'Kottayam': 'south_central', 'Alappuzha': 'south_central',
    'Pathanamthitta': 'south', 'Kollam': 'south', 'Thiruvananthapuram': 'south',
}

# Pre-load alliance maps once at import time for O(1) lookups
# These are refreshed on server restart; call _refresh_alliance_cache() after DB changes.
_ALLIANCE_CACHE: dict[tuple, str] = {}

def _build_cache():
    global _ALLIANCE_CACHE
    try:
        _ALLIANCE_CACHE = {
            (r.party.code, r.election_year, r.election_type): r.alliance.code
            for r in PartyAllianceYear.objects.select_related('party', 'alliance').all()
        }
    except Exception:
        # Tables may not exist yet during migrations
        _ALLIANCE_CACHE = {}

_build_cache()  # run at startup

def get_alliance(party_code: str, year: int = 2026, etype: str = 'LA') -> str:
    """Return alliance code for a party in a specific election year.
    Looks up PartyAllianceYear first; falls back to Party.alliance."""
    cached = _ALLIANCE_CACHE.get((party_code, year, etype))
    if cached:
        return cached
    # Fallback: live DB lookup (handles parties added after server start)
    try:
        entry = PartyAllianceYear.objects.select_related('party', 'alliance').filter(
            party__code=party_code, election_year=year, election_type=etype
        ).first()
        if entry:
            _ALLIANCE_CACHE[(party_code, year, etype)] = entry.alliance.code
            return entry.alliance.code
        # Final fallback: Party.alliance
        party = Party.objects.select_related('alliance').filter(code=party_code).first()
        return party.alliance.code if party else 'OTH'
    except Exception:
        return 'OTH'


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ['id', 'name', 'order']


class PartySerializer(serializers.ModelSerializer):
    seats_contested = serializers.SerializerMethodField()
    seats_leading_or_won = serializers.SerializerMethodField()
    alliance = serializers.SerializerMethodField()

    class Meta:
        model = Party
        fields = ['code', 'full_name', 'alliance', 'color_code', 'seats_contested', 'seats_leading_or_won']

    def get_alliance(self, obj):
        return get_alliance(obj.code, 2026)

    def get_seats_contested(self, obj):
        return obj.candidates_2026.count()

    def get_seats_leading_or_won(self, obj):
        return obj.candidates_2026.filter(
            models.Q(is_winner=True) | models.Q(is_leading=True)
        ).count()


class CandidateSerializer(serializers.ModelSerializer):
    party = serializers.CharField(source='party.code')
    party_name = serializers.CharField(source='party.full_name')
    alliance = serializers.CharField(source='party.alliance.code')
    party_color = serializers.CharField(source='party.color_code')
    alliance_color = serializers.SerializerMethodField()

    def get_alliance_color(self, obj):
        return obj.party.alliance.color_code if obj.party and obj.party.alliance else '#808080'
    
    class Meta:
        model = Candidate
        fields = [
            'id', 'name', 'party', 'party_name', 'alliance', 'party_color',
            'alliance_color', 'votes', 'vote_percentage', 'is_winner', 'is_leading'
        ]


class LiveResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveResult
        fields = [
            'status', 'total_electors', 'votes_polled', 'votes_counted',
            'valid_votes', 'rejected_votes', 'rounds_completed', 'total_rounds',
            'last_updated', 'updated_by'
        ]


class HistoricalResult2021Serializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricalResult2021
        fields = [
            'serial_no', 'candidate_name', 'party_code', 'party_symbol',
            'total_votes', 'vote_percentage', 'is_winner'
        ]


class ConstituencyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list view"""
    district = serializers.CharField(source='district.name')
    reserved = serializers.CharField(source='get_reserved_category_display')
    region = serializers.SerializerMethodField()
    leader = serializers.SerializerMethodField()
    runner_up = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    sitting_party = serializers.SerializerMethodField()
    sitting_alliance = serializers.SerializerMethodField()
    # Static polling-day fields — never change during counting
    total_electors = serializers.SerializerMethodField()
    votes_polled = serializers.SerializerMethodField()
    
    class Meta:
        model = Constituency
        fields = [
            'id', 'number', 'name', 'district', 'region', 'reserved',
            'leader', 'runner_up', 'status', 'sitting_party', 'sitting_alliance',
            'total_electors', 'votes_polled',
        ]

    def get_region(self, obj):
        """Compute region from district name — the DB field is often empty."""
        return _DISTRICT_REGION.get(obj.district.name, 'south')
    
    def get_leader(self, obj):
        live = obj.live_results.first()
        # No leader before counting starts
        if not live or live.status == 'NOT_STARTED':
            return None
        leader = obj.candidates_2026.order_by('-votes').first()
        if leader and leader.votes > 0:
            return {
                'name': leader.name,
                'party': leader.party.code,
                'alliance': get_alliance(leader.party.code, 2026),
                'votes': leader.votes,
                'percentage': float(leader.vote_percentage),
                'party_color': leader.party.color_code,
            }
        return None

    def get_runner_up(self, obj):
        live = obj.live_results.first()
        if not live or live.status == 'NOT_STARTED':
            return None
        candidates = list(obj.candidates_2026.order_by('-votes')[:2])
        if len(candidates) >= 2 and candidates[1].votes > 0:
            runner = candidates[1]
            return {
                'name': runner.name,
                'party': runner.party.code,
                'alliance': get_alliance(runner.party.code, 2026),
                'votes': runner.votes,
                'percentage': float(runner.vote_percentage),
                'party_color': runner.party.color_code,
            }
        return None

    def get_status(self, obj):
        live_result = obj.live_results.first()
        return live_result.status if live_result else 'NOT_STARTED'

    def get_sitting_party(self, obj):
        meta = getattr(obj, 'meta_2021', None)
        return meta.winner_party.code if meta and meta.winner_party else None

    def get_sitting_alliance(self, obj):
        meta = getattr(obj, 'meta_2021', None)
        if meta and meta.winner_party:
            entry = PartyAllianceYear.objects.select_related('alliance').filter(
                party=meta.winner_party,
                election_year=2021,
                election_type='LA'
            ).first()
            if entry:
                return entry.alliance.code
        return None

    def get_total_electors(self, obj):
        """Total registered electors — static from electoral rolls."""
        live = obj.live_results.first()
        return live.total_electors if live and live.total_electors else 0

    def get_votes_polled(self, obj):
        """Votes polled on polling day — static once polling ends."""
        live = obj.live_results.first()
        return live.votes_polled if live and live.votes_polled else 0

    def get_sitting_color(self, obj):
        """Convenience: color for the 2021 sitting party."""
        meta = getattr(obj, 'meta_2021', None)
        if meta and meta.winner_party:
            entry = PartyAllianceYear.objects.select_related('alliance').filter(
                party=meta.winner_party,
                election_year=2021,
                election_type='LA'
            ).first()
            if entry:
                return entry.color_code
        return '#808080'


class ConstituencyDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail view - returns nested structure matching frontend types"""
    district_name = serializers.CharField(source='district.name')
    candidates = CandidateSerializer(source='candidates_2026', many=True)
    live_result = serializers.SerializerMethodField()
    results_2021 = HistoricalResult2021Serializer(many=True, read_only=True)

    class Meta:
        model = Constituency
        fields = [
            'id', 'number', 'name', 'district_name', 'reserved_category',
            'parliament_constituency', 'candidates', 'live_result', 'results_2021'
        ]

    def get_live_result(self, obj):
        live = obj.live_results.first()
        if live:
            return LiveResultSerializer(live).data
        return None
    def to_representation(self, instance):
        raw = super().to_representation(instance)
        # Reshape to match TypeScript ConstituencyDetail interface
        live_status = (raw.get('live_result') or {}).get('status', 'NOT_STARTED')
        return {
            'constituency': {
                'id': raw['id'],
                'number': raw['number'],
                'name': raw['name'],
                'district': raw['district_name'],
            },
            'live_result': raw['live_result'],
            'candidates_2026': [
                {
                    'name': c['name'],
                    'party': c['party'],
                    # Use year-aware lookup for 2026 alliance
                    'alliance': get_alliance(c['party'], 2026),
                    'party_color': c.get('party_color', '#808080'),
                    'votes': c['votes'],
                    'percentage': float(c['vote_percentage']),
                    'is_winner': c['is_winner'],
                    'is_leading': (
                        idx == 0
                        and c['votes'] > 0
                        and not c['is_winner']
                        and live_status == 'IN_PROGRESS'
                    ),
                }
                for idx, c in enumerate(
                    sorted(raw['candidates'], key=lambda x: x['votes'], reverse=True)
                )
            ],
            'results_2021': [
                {
                    'candidate': r['candidate_name'],
                    'party': r['party_code'],
                    # Use 2021-specific alliance lookup (handles JD(S)=LDF, LJD=LDF, etc.)
                    'alliance': get_alliance(r['party_code'], 2021),
                    'votes': r['total_votes'],
                    'percentage': float(r['vote_percentage']),
                    'is_winner': r['is_winner'],
                }
                for r in raw['results_2021']
            ],
        }




class ParliamentResultSerializer(serializers.ModelSerializer):
    constituency_name = serializers.CharField(source='constituency.name')
    
    class Meta:
        model = ParliamentResult
        fields = [
            'year', 'constituency_name', 'parliament_constituency',
            'udf_votes', 'ldf_votes', 'nda_votes',
            'lead_alliance', 'runnerup_alliance', 'margin'
        ]
