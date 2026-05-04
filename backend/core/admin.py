from django.contrib import admin
from core.models import (
    Alliance, District, Constituency, Party, PartyAlias, Candidate, LiveResult,
    HistoricalResult2021, HistoricalResult2016, HistoricalResult2016Full,
    HistoricalResult2011, ConstituencyMeta2021, ParliamentResult, DataSnapshot,
    ECIScrapeRaw, ECICandidateMatch, PartyAllianceYear,
)


@admin.register(Alliance)
class AllianceAdmin(admin.ModelAdmin):
    list_display = ['code', 'full_name', 'color_code']
    ordering = ['code']


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ['name', 'order']
    list_editable = ['order']
    ordering = ['order']


@admin.register(Constituency)
class ConstituencyAdmin(admin.ModelAdmin):
    list_display = ['number', 'name', 'district', 'reserved_category', 'parliament_constituency']
    list_filter = ['district', 'reserved_category']
    search_fields = ['name', 'parliament_constituency']
    ordering = ['number']


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ['code', 'full_name', 'alliance', 'color_code']
    list_filter = ['alliance']
    search_fields = ['code', 'full_name']
    ordering = ['alliance__code', 'code']


@admin.register(PartyAlias)
class PartyAliasAdmin(admin.ModelAdmin):
    list_display = ['alias_code', 'party', 'election_year']
    list_filter = ['election_year']
    search_fields = ['alias_code', 'party__code']
    ordering = ['alias_code']


class CandidateInline(admin.TabularInline):
    model = Candidate
    extra = 0
    fields = ['name', 'party', 'votes', 'vote_percentage', 'is_winner', 'is_leading']
    readonly_fields = []


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['name', 'party', 'constituency', 'votes', 'vote_percentage', 'is_winner', 'is_leading']
    list_filter = ['constituency__district', 'party__alliance', 'is_winner', 'is_leading']
    search_fields = ['name', 'constituency__name', 'party__code']
    ordering = ['constituency__number', '-votes']
    
    fieldsets = (
        ('Candidate Info', {
            'fields': ('name', 'party', 'constituency')
        }),
        ('Results', {
            'fields': ('votes', 'vote_percentage', 'is_winner', 'is_leading')
        }),
    )


@admin.register(LiveResult)
class LiveResultAdmin(admin.ModelAdmin):
    list_display = [
        'constituency', 'status', 'votes_counted', 'valid_votes',
        'rounds_completed', 'total_rounds', 'last_updated'
    ]
    list_filter = ['status', 'constituency__district']
    search_fields = ['constituency__name']
    ordering = ['constituency__number']
    
    fieldsets = (
        ('Constituency', {
            'fields': ('constituency', 'status')
        }),
        ('Counting Progress', {
            'fields': (
                'total_electors', 'votes_polled', 'votes_counted',
                'valid_votes', 'rejected_votes'
            )
        }),
        ('Rounds', {
            'fields': ('rounds_completed', 'total_rounds')
        }),
        ('Tracking', {
            'fields': ('updated_by', 'last_updated'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['last_updated']


@admin.register(HistoricalResult2021)
class HistoricalResult2021Admin(admin.ModelAdmin):
    list_display = [
        'constituency', 'candidate_name', 'party', 'party_code', 'total_votes',
        'vote_percentage', 'is_winner'
    ]
    list_filter = ['constituency__district', 'is_winner']
    search_fields = ['candidate_name', 'party_code', 'constituency__name']
    ordering = ['constituency__number', '-total_votes']


@admin.register(ConstituencyMeta2021)
class ConstituencyMeta2021Admin(admin.ModelAdmin):
    list_display = ['constituency', 'total_electors', 'winner_name', 'winner_party', 'margin']
    search_fields = ['constituency__name', 'winner_name']
    ordering = ['constituency__number']


@admin.register(ParliamentResult)
class ParliamentResultAdmin(admin.ModelAdmin):
    list_display = [
        'year', 'constituency', 'parliament_constituency',
        'lead_alliance', 'margin'
    ]
    list_filter = ['year', 'lead_alliance', 'constituency__district']
    search_fields = ['constituency__name', 'parliament_constituency']
    ordering = ['year', 'constituency__number']


@admin.register(DataSnapshot)
class DataSnapshotAdmin(admin.ModelAdmin):
    list_display = ['snapshot_type', 'last_exported', 'record_count', 'file_path']
    readonly_fields = ['last_exported']
    ordering = ['-last_exported']


@admin.register(ECIScrapeRaw)
class ECIScrapeRawAdmin(admin.ModelAdmin):
    list_display = ['constituency', 'scraped_at', 'rounds_completed', 'total_rounds', 'is_final', 'match_status']
    list_filter = ['match_status', 'is_final', 'constituency__district']
    search_fields = ['constituency__name']
    readonly_fields = ['scraped_at', 'raw_candidates']
    ordering = ['-scraped_at']


@admin.register(ECICandidateMatch)
class ECICandidateMatchAdmin(admin.ModelAdmin):
    list_display = ['eci_name', 'eci_party', 'eci_total_votes', 'candidate', 'is_confirmed', 'is_nota']
    list_filter = ['is_confirmed', 'is_nota', 'constituency__district']
    search_fields = ['eci_name', 'eci_party', 'constituency__name']
    ordering = ['-eci_total_votes']


@admin.register(HistoricalResult2016)
class HistoricalResult2016Admin(admin.ModelAdmin):
    list_display = ['constituency', 'winner_candidate', 'winner_party', 'winner_alliance', 'margin']
    list_filter = ['constituency__district']
    search_fields = ['winner_candidate', 'constituency__name']
    ordering = ['constituency__number']


@admin.register(HistoricalResult2016Full)
class HistoricalResult2016FullAdmin(admin.ModelAdmin):
    list_display = ['constituency', 'candidate_name', 'party', 'party_code', 'total_votes', 'vote_percentage', 'is_winner']
    list_filter = ['constituency__district', 'is_winner']
    search_fields = ['candidate_name', 'party_code', 'constituency__name']
    ordering = ['constituency__number', '-total_votes']


@admin.register(HistoricalResult2011)
class HistoricalResult2011Admin(admin.ModelAdmin):
    list_display = ['constituency', 'candidate_name', 'party', 'party_code', 'total_votes', 'vote_percentage', 'is_winner']
    list_filter = ['constituency__district', 'is_winner']
    search_fields = ['candidate_name', 'party_code', 'constituency__name']
    ordering = ['constituency__number', '-total_votes']


@admin.register(PartyAllianceYear)
class PartyAllianceYearAdmin(admin.ModelAdmin):
    list_display = ['party', 'alliance', 'election_year', 'election_type', 'color_code']
    list_filter = ['election_year', 'election_type', 'alliance']
    search_fields = ['party__code', 'party__full_name']
    ordering = ['election_year', 'alliance__code', 'party__code']
    list_editable = ['alliance', 'color_code']


# Customize admin site
admin.site.site_header = "Kerala Election 2026 - Admin"
admin.site.site_title = "Election Admin"
admin.site.index_title = "Election Data Management"
