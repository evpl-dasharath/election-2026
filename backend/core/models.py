from django.db import models
from django.utils import timezone


class Alliance(models.Model):
    """Political alliances — UDF, LDF, NDA, OTH."""
    code = models.CharField(max_length=3, unique=True, help_text="UDF, LDF, NDA, OTH")
    full_name = models.CharField(max_length=100)
    color_code = models.CharField(max_length=7, default='#808080', help_text="Primary hex color")

    class Meta:
        ordering = ['code']

    def __str__(self):
        return self.code


class District(models.Model):
    """Kerala districts"""
    name = models.CharField(max_length=100, unique=True)
    order = models.IntegerField(help_text="Display order from north to south")
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.name


class Constituency(models.Model):
    """Legislative Assembly constituencies"""
    RESERVED_CHOICES = [
        ('GEN', 'General'),
        ('SC', 'Scheduled Caste'),
        ('ST', 'Scheduled Tribe'),
    ]
    
    number = models.IntegerField(unique=True, help_text="ECI constituency number (1-140)")
    name = models.CharField(max_length=100)
    district = models.ForeignKey(District, on_delete=models.PROTECT, related_name='constituencies')
    reserved_category = models.CharField(max_length=3, choices=RESERVED_CHOICES, default='GEN')
    
    # For Parliament results mapping
    parliament_constituency = models.CharField(max_length=100, blank=True, help_text="LS constituency this AC falls under")
    
    # Geographic region for UI grouping
    REGION_CHOICES = [
        ('north', 'North (Malabar)'),
        ('central_north', 'Central North'),
        ('south_central', 'South Central'),
        ('south', 'South (Travancore)'),
    ]
    region = models.CharField(max_length=20, choices=REGION_CHOICES, blank=True, help_text="Geographic region for UI grouping")
    
    class Meta:
        ordering = ['number']
        verbose_name_plural = "Constituencies"
    
    def __str__(self):
        return f"{self.number}. {self.name}"


class Party(models.Model):
    """Political parties — canonical registry.
    Each real-world party has exactly ONE entry here with a canonical code.
    Alliance here is the 2026 default.
    For historical lookups, always use PartyAllianceYear."""
    
    code = models.CharField(max_length=20, unique=True, help_text="Canonical abbreviation (INC, CPI_M, BJP, etc)")
    full_name = models.CharField(max_length=200)
    alliance = models.ForeignKey(
        Alliance, on_delete=models.PROTECT, related_name='parties',
        help_text="Default / 2026 alliance"
    )
    color_code = models.CharField(max_length=7, default='#808080', help_text="Hex color for charts")
    
    class Meta:
        verbose_name_plural = "Parties"
        ordering = ['alliance__code', 'code']
    
    def __str__(self):
        return f"{self.code} ({self.alliance.code})"


class PartyAlias(models.Model):
    """Maps variant/ECI party codes to canonical Party entries.
    e.g. CPM -> CPI_M, MUL -> IUML, KEC(M) -> KC_M, RMPOI -> RMPI.
    Optional election_year for year-specific aliases; null means all years."""
    alias_code = models.CharField(max_length=50, help_text="ECI/CSV code variant")
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='aliases')
    election_year = models.IntegerField(
        null=True, blank=True,
        help_text="Year-specific alias (null = universal)"
    )

    class Meta:
        unique_together = [['alias_code', 'election_year']]
        ordering = ['alias_code']
        verbose_name = "Party Alias"
        verbose_name_plural = "Party Aliases"

    def __str__(self):
        yr = f" ({self.election_year})" if self.election_year else ""
        return f"{self.alias_code}{yr} -> {self.party.code}"


class PartyAllianceYear(models.Model):
    """Year-specific alliance mapping for parties.
    Defines which alliance a party belongs to in a specific election year."""
    ELECTION_TYPE_CHOICES = [
        ('LA', 'Legislative Assembly'),
        ('LS', 'Lok Sabha'),
    ]

    party = models.ForeignKey(
        Party, on_delete=models.CASCADE, related_name='alliance_years',
        help_text="Canonical party"
    )
    election_year = models.IntegerField(help_text="Election year e.g. 2021")
    election_type = models.CharField(max_length=2, choices=ELECTION_TYPE_CHOICES)
    alliance = models.ForeignKey(
        Alliance, on_delete=models.PROTECT, related_name='party_years',
        help_text="Alliance for this year"
    )
    color_code = models.CharField(max_length=7, default='#808080')

    class Meta:
        unique_together = [['party', 'election_year', 'election_type']]
        ordering = ['election_year', 'alliance__code', 'party__code']
        verbose_name = "Party Alliance (by Year)"
        verbose_name_plural = "Party Alliances (by Year)"

    def __str__(self):
        return f"{self.party.code} -- {self.alliance.code} [{self.election_year} {self.election_type}]"


class Candidate(models.Model):
    """Candidates for 2026 election"""
    name = models.CharField(max_length=200)
    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='candidates_2026')
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE, related_name='candidates_2026')
    
    # For live results
    votes = models.IntegerField(default=0)
    vote_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Status tracking
    is_winner = models.BooleanField(default=False)
    is_leading = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-votes']
    
    def __str__(self):
        return f"{self.name} ({self.party.code}) - {self.constituency.name}"


class LiveResult(models.Model):
    """Live vote counting updates for 2026"""
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE, related_name='live_results')
    
    # Counting status
    STATUS_CHOICES = [
        ('NOT_STARTED', 'Counting Not Started'),
        ('IN_PROGRESS', 'Counting In Progress'),
        ('COMPLETED', 'Counting Completed'),
        ('RESULT_DECLARED', 'Result Declared'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NOT_STARTED')
    
    # Counting stats
    total_electors = models.IntegerField(default=0)
    votes_polled = models.IntegerField(default=0)
    votes_counted = models.IntegerField(default=0)
    valid_votes = models.IntegerField(default=0)
    rejected_votes = models.IntegerField(default=0)
    
    # Round/stage info
    rounds_completed = models.IntegerField(default=0)
    total_rounds = models.IntegerField(default=0)
    
    # Tracking
    last_updated = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=100, default='system')
    
    class Meta:
        ordering = ['constituency__number']
    
    def __str__(self):
        return f"{self.constituency.name} - {self.status}"


class HistoricalResult2021(models.Model):
    """2021 LA election results - individual candidate records"""
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE, related_name='results_2021')
    
    # Candidate details
    serial_no = models.IntegerField(help_text="Serial number on ballot", null=True, blank=True)
    candidate_name = models.CharField(max_length=200)
    sex = models.CharField(max_length=10, blank=True)
    age = models.IntegerField(null=True, blank=True)
    category = models.CharField(max_length=20, blank=True, help_text="GENERAL, SC, ST")
    
    # Party — FK to canonical Party
    party = models.ForeignKey(
        Party, on_delete=models.PROTECT, related_name='results_2021',
        null=True, blank=True,
        help_text="Canonical party (FK)"
    )
    # Legacy field kept for migration reference
    party_code = models.CharField(max_length=50, help_text="Original ECI party code (legacy)")
    party_symbol = models.CharField(max_length=200, blank=True)
    
    # Votes
    general_votes = models.IntegerField(default=0)
    postal_votes = models.IntegerField(default=0)
    total_votes = models.IntegerField()
    vote_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Status
    is_winner = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['constituency__number', '-total_votes']
        verbose_name = "2021 LA Result"
        verbose_name_plural = "2021 LA Results"
    
    def __str__(self):
        code = self.party.code if self.party else self.party_code
        winner_mark = " W" if self.is_winner else ""
        return f"{self.constituency.name} - {self.candidate_name} ({code}){winner_mark}"


class ConstituencyMeta2021(models.Model):
    """Metadata for each constituency in 2021 election"""
    constituency = models.OneToOneField(Constituency, on_delete=models.CASCADE, related_name='meta_2021')
    total_electors = models.IntegerField()
    
    # Computed fields (from candidate records)
    winner_name = models.CharField(max_length=200, blank=True)
    winner_party = models.ForeignKey(
        Party, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+',
        help_text="Winning party FK"
    )
    winner_party_code = models.CharField(max_length=50, blank=True, help_text="Legacy winner party code")
    margin = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "2021 Constituency Metadata"
        verbose_name_plural = "2021 Constituency Metadata"
    
    def __str__(self):
        return f"{self.constituency.name} - {self.total_electors} electors"


class HistoricalResult2016(models.Model):
    """2016 LA election results (winner + runner-up summary — kept for backward compat)"""
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE, related_name='results_2016')
    
    # Winner
    winner_candidate = models.CharField(max_length=200)
    winner_party = models.ForeignKey(
        Party, on_delete=models.PROTECT, related_name='wins_2016',
        null=True, blank=True,
        help_text="Winner party FK"
    )
    winner_party_code = models.CharField(max_length=20, blank=True, help_text="Legacy")
    winner_alliance = models.ForeignKey(
        Alliance, on_delete=models.PROTECT, related_name='+',
        null=True, blank=True
    )
    winner_alliance_code = models.CharField(max_length=3, blank=True, help_text="Legacy")
    winner_votes = models.IntegerField()
    winner_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Runner-up
    runnerup_candidate = models.CharField(max_length=200)
    runnerup_party = models.ForeignKey(
        Party, on_delete=models.PROTECT, related_name='runnerups_2016',
        null=True, blank=True,
        help_text="Runner-up party FK"
    )
    runnerup_party_code = models.CharField(max_length=20, blank=True, help_text="Legacy")
    runnerup_alliance = models.ForeignKey(
        Alliance, on_delete=models.PROTECT, related_name='+',
        null=True, blank=True
    )
    runnerup_alliance_code = models.CharField(max_length=3, blank=True, help_text="Legacy")
    runnerup_votes = models.IntegerField()
    runnerup_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    
    margin = models.IntegerField()
    
    class Meta:
        unique_together = [['constituency']]
        verbose_name = "2016 LA Result"
        verbose_name_plural = "2016 LA Results"
    
    def __str__(self):
        code = self.winner_party.code if self.winner_party else self.winner_party_code
        return f"{self.constituency.name} - {self.winner_candidate} ({code})"


class HistoricalResult2016Full(models.Model):
    """2016 LA election results -- full candidate-level records."""
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE, related_name='results_2016_full')

    # Candidate details
    candidate_name = models.CharField(max_length=200)
    sex = models.CharField(max_length=10, blank=True)
    age = models.IntegerField(null=True, blank=True)
    category = models.CharField(max_length=20, blank=True, help_text="GEN, SC, ST")

    # Party — FK to canonical Party
    party = models.ForeignKey(
        Party, on_delete=models.PROTECT, related_name='results_2016',
        null=True, blank=True,
        help_text="Canonical party (FK)"
    )
    party_code = models.CharField(max_length=50, help_text="Original ECI party code (legacy)")

    # Votes
    general_votes = models.IntegerField(default=0)
    postal_votes = models.IntegerField(default=0)
    total_votes = models.IntegerField(default=0)
    vote_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Constituency totals (denormalised for convenience)
    total_electors = models.IntegerField(default=0)
    total_votes_polled = models.IntegerField(default=0)

    # Status
    is_winner = models.BooleanField(default=False)

    class Meta:
        ordering = ['constituency__number', '-total_votes']
        verbose_name = "2016 LA Result (Full)"
        verbose_name_plural = "2016 LA Results (Full)"

    def __str__(self):
        code = self.party.code if self.party else self.party_code
        mark = " W" if self.is_winner else ""
        return f"{self.constituency.name} - {self.candidate_name} ({code}){mark}"


class HistoricalResult2011(models.Model):
    """2011 LA election results -- individual candidate records."""
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE, related_name='results_2011')

    serial_no = models.IntegerField(null=True, blank=True)
    candidate_name = models.CharField(max_length=200)
    sex = models.CharField(max_length=10, blank=True)
    age = models.IntegerField(null=True, blank=True)
    category = models.CharField(max_length=20, blank=True)

    # Party — FK to canonical Party
    party = models.ForeignKey(
        Party, on_delete=models.PROTECT, related_name='results_2011',
        null=True, blank=True,
        help_text="Canonical party (FK)"
    )
    party_code = models.CharField(max_length=50, help_text="Original ECI party code (legacy)")
    party_symbol = models.CharField(max_length=200, blank=True)

    general_votes = models.IntegerField(default=0)
    postal_votes = models.IntegerField(default=0)
    total_votes = models.IntegerField(default=0)
    vote_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    total_electors = models.IntegerField(default=0)

    is_winner = models.BooleanField(default=False)

    class Meta:
        ordering = ['constituency__number', '-total_votes']
        verbose_name = '2011 LA Result'
        verbose_name_plural = '2011 LA Results'

    def __str__(self):
        code = self.party.code if self.party else self.party_code
        mark = ' W' if self.is_winner else ''
        return f'{self.constituency.name} - {self.candidate_name} ({code}){mark}'


class HistoricalResult2006(models.Model):
    """2006 LA election results -- individual candidate records."""
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE, related_name='results_2006')

    serial_no = models.IntegerField(null=True, blank=True)
    candidate_name = models.CharField(max_length=200)
    sex = models.CharField(max_length=10, blank=True)
    age = models.IntegerField(null=True, blank=True)
    category = models.CharField(max_length=20, blank=True)

    # Party — FK to canonical Party
    party = models.ForeignKey(
        Party, on_delete=models.PROTECT, related_name='results_2006',
        null=True, blank=True,
        help_text="Canonical party (FK)"
    )
    party_code = models.CharField(max_length=50, help_text="Original ECI party code (legacy)")
    party_symbol = models.CharField(max_length=200, blank=True)

    general_votes = models.IntegerField(default=0)
    postal_votes = models.IntegerField(default=0)
    total_votes = models.IntegerField(default=0)
    vote_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    total_electors = models.IntegerField(default=0)

    is_winner = models.BooleanField(default=False)

    class Meta:
        ordering = ['constituency__number', '-total_votes']
        verbose_name = '2006 LA Result'
        verbose_name_plural = '2006 LA Results'

    def __str__(self):
        code = self.party.code if self.party else self.party_code
        mark = ' W' if self.is_winner else ''
        return f'{self.constituency.name} - {self.candidate_name} ({code}){mark}'


class ParliamentResult(models.Model):
    """Parliament election results at AC level (2019 & 2024)"""
    ELECTION_YEAR_CHOICES = [
        (2019, '2019'),
        (2024, '2024'),
    ]
    
    year = models.IntegerField(choices=ELECTION_YEAR_CHOICES)
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE, related_name='parliament_results')
    parliament_constituency = models.CharField(max_length=100, help_text="LS constituency name")
    
    # Alliance-level votes
    udf_votes = models.IntegerField()
    ldf_votes = models.IntegerField()
    nda_votes = models.IntegerField()
    
    # Lead info
    lead_alliance = models.CharField(max_length=3)
    runnerup_alliance = models.CharField(max_length=3)
    margin = models.IntegerField()
    
    class Meta:
        unique_together = [['year', 'constituency']]
        ordering = ['year', 'constituency__number']
        verbose_name = "Parliament Result (AC Level)"
        verbose_name_plural = "Parliament Results (AC Level)"
    
    def __str__(self):
        return f"{self.year} - {self.constituency.name} ({self.parliament_constituency})"


class DataSnapshot(models.Model):
    """Track when data was last exported to JSON"""
    snapshot_type = models.CharField(max_length=50, unique=True, 
                                     help_text="meta, constituencies, results, historical")
    last_exported = models.DateTimeField(default=timezone.now)
    file_path = models.CharField(max_length=500, blank=True)
    record_count = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.snapshot_type} - {self.last_exported}"


class ECIScrapeRaw(models.Model):
    """
    Staging table -- raw data scraped from ECI website.
    Holds unmatched/unconfirmed results before they're committed
    to the Candidate table.
    """
    constituency = models.ForeignKey(
        Constituency,
        on_delete=models.CASCADE,
        related_name='eci_raw_results'
    )
    scraped_at = models.DateTimeField(auto_now_add=True)

    # Round info
    rounds_completed = models.IntegerField(default=0)
    total_rounds = models.IntegerField(default=0)
    is_final = models.BooleanField(default=False)
    eci_last_updated = models.CharField(max_length=100, blank=True)

    # Raw JSON blob of all candidates as scraped
    raw_candidates = models.JSONField(default=list)

    # Match status
    MATCH_STATUS = [
        ('PENDING',  'Pending Review'),
        ('MATCHED',  'Matched & Committed'),
        ('PARTIAL',  'Partially Matched'),
        ('SKIPPED',  'Skipped'),
    ]
    match_status = models.CharField(max_length=20, choices=MATCH_STATUS, default='PENDING')

    class Meta:
        ordering = ['-scraped_at']
        verbose_name = 'ECI Raw Scrape'
        verbose_name_plural = 'ECI Raw Scrapes'

    def __str__(self):
        return f"{self.constituency.name} -- scraped {self.scraped_at:%Y-%m-%d %H:%M}"


class ECICandidateMatch(models.Model):
    """
    Maps a scraped ECI candidate name to a DB Candidate.
    Once confirmed, used for all future scrapes automatically.
    """
    scrape = models.ForeignKey(
        ECIScrapeRaw,
        on_delete=models.CASCADE,
        related_name='matches'
    )
    constituency = models.ForeignKey(
        Constituency,
        on_delete=models.CASCADE
    )

    # ECI side
    eci_name = models.CharField(max_length=200)
    eci_party = models.CharField(max_length=200)
    eci_total_votes = models.IntegerField(default=0)
    eci_vote_percentage = models.FloatField(default=0.0)
    eci_is_leading = models.BooleanField(default=False)

    # DB side (null = unmatched)
    candidate = models.ForeignKey(
        'Candidate',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='eci_matches'
    )
    is_confirmed = models.BooleanField(default=False)
    is_nota = models.BooleanField(default=False)

    class Meta:
        ordering = ['-eci_total_votes']

    def __str__(self):
        matched = self.candidate.name if self.candidate else '(unmatched)'
        return f"{self.eci_name} -> {matched}"


class CandidateAlias(models.Model):
    """
    Stores manual matches (aliases) for ECI candidate names so future scrapes auto-match.
    """
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE)
    eci_name = models.CharField(max_length=255)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='name_aliases')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('constituency', 'eci_name')
        verbose_name = 'Candidate Alias'
        verbose_name_plural = 'Candidate Aliases'

    def __str__(self):
        return f"{self.eci_name} -> {self.candidate.name}"
