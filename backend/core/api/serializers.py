from rest_framework import serializers
from core.models import (
    District, Constituency, Party, Candidate, LiveResult,
    HistoricalResult2021, ConstituencyMeta2021, ParliamentResult,
    PartyAllianceYear
)


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ['id', 'name', 'order']


class PartySerializer(serializers.ModelSerializer):
    class Meta:
        model = Party
        fields = ['code', 'full_name', 'alliance', 'color_code']


class CandidateSerializer(serializers.ModelSerializer):
    party_code = serializers.CharField(source='party.code')
    party_name = serializers.CharField(source='party.full_name')
    alliance = serializers.CharField(source='party.alliance')
    party_color = serializers.CharField(source='party.color_code')
    
    class Meta:
        model = Candidate
        fields = [
            'id', 'name', 'party_code', 'party_name', 'alliance', 'party_color',
            'votes', 'vote_percentage', 'is_winner', 'is_leading'
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
    leader = serializers.SerializerMethodField()
    runner_up = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    sitting_party = serializers.SerializerMethodField()
    sitting_alliance = serializers.SerializerMethodField()
    
    class Meta:
        model = Constituency
        fields = [
            'id', 'number', 'name', 'district', 'region', 'reserved',
            'leader', 'runner_up', 'status', 'sitting_party', 'sitting_alliance'
        ]
    
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
                'alliance': leader.party.alliance,
                'votes': leader.votes,
                'percentage': float(leader.vote_percentage),
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
                'alliance': runner.party.alliance,
                'votes': runner.votes,
                'percentage': float(runner.vote_percentage),
            }
        return None

    def get_status(self, obj):
        live_result = obj.live_results.first()
        return live_result.status if live_result else 'NOT_STARTED'

    def get_sitting_party(self, obj):
        meta = getattr(obj, 'meta_2021', None)
        return meta.winner_party if meta else None

    def get_sitting_alliance(self, obj):
        meta = getattr(obj, 'meta_2021', None)
        if meta and meta.winner_party:
            entry = PartyAllianceYear.objects.filter(
                party_code=meta.winner_party,
                election_year=2021,
                election_type='LA'
            ).first()
            if entry:
                return entry.alliance
        return None

    def get_sitting_color(self, obj):
        """Convenience: color for the 2021 sitting party."""
        meta = getattr(obj, 'meta_2021', None)
        if meta and meta.winner_party:
            entry = PartyAllianceYear.objects.filter(
                party_code=meta.winner_party,
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
                    'party': c['party_code'],
                    'alliance': c['alliance'],
                    'votes': c['votes'],
                    'percentage': float(c['vote_percentage']),
                    'is_winner': c['is_winner'],
                    # is_leading computed dynamically: highest votes when counting is active
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
