"""
Import 2026 voter registration and turnout data from OpenDataKerala.

Sources:
  - Electors: "Assembly Constituency Wise Electors" table (actual 2026 rolls)
  - Turnout:  Turnout % per constituency (https://opendatakerala.org/KLA2026/)

Computes votes_polled = total_electors × (polling_pct / 100) and stores
both values in LiveResult. Keyed by AC number (1-140) — no name fuzzy
matching required.

Usage:
    python manage.py import_voter_turnout
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Constituency, LiveResult


# ── 2026 Registered Electors — AC number → total (Male + Female + Third Gender)
# Source: "Assembly Constituency Wise Electors (General + Overseas)", OpenDataKerala
ELECTORS_2026 = {
    1:  230113,   # MANJESHWAR
    2:  210923,   # KASARAGOD
    3:  228512,   # UDMA
    4:  223980,   # KANHANGAD
    5:  210090,   # TRIKARIPUR
    6:  188935,   # PAYYANNUR
    7:  203796,   # KALLIASSERI
    8:  232280,   # TALIPARAMBA
    9:  199326,   # IRIKKUR
    10: 188250,   # AZHIKODE
    11: 182682,   # KANNUR
    12: 206000,   # DHARMADAM
    13: 185841,   # THALASSERY
    14: 205771,   # KUTHUPARAMBA
    15: 201719,   # MATTANNUR
    16: 182384,   # PERAVOOR
    17: 205415,   # MANANTHAVADY
    18: 225329,   # SULTHANBATHERY
    19: 212881,   # KALPETTA
    20: 176832,   # VADAKARA
    21: 215940,   # KUTTIADI
    22: 233690,   # NADAPURAM
    23: 213254,   # QUILANDY
    24: 205970,   # PERAMBRA
    25: 228689,   # BALUSSERI
    26: 211105,   # ELATHUR
    27: 173205,   # KOZHIKODE NORTH
    28: 155972,   # KOZHIKODE SOUTH
    29: 218558,   # BEYPORE
    30: 241980,   # KUNNAMANGALAM
    31: 201668,   # KODUVALLY
    32: 191954,   # THIRUVAMBADY
    33: 229370,   # KONDOTTY
    34: 199556,   # ERANAD
    35: 236576,   # NILAMBUR
    36: 247184,   # WANDOOR
    37: 227762,   # MANJERI
    38: 229525,   # PERINTHALMANNA
    39: 230838,   # MANKADA
    40: 238080,   # MALAPPURAM
    41: 211630,   # VENGARA
    42: 221036,   # VALLIKKUNNU
    43: 222792,   # TIRURANGADI
    44: 214101,   # TANUR
    45: 255441,   # TIRUR
    46: 243014,   # KOTTAKKAL
    47: 208776,   # THAVANUR
    48: 216529,   # PONNANI
    49: 203700,   # THRITHALA
    50: 210790,   # PATTAMBI
    51: 199620,   # SHORNUR
    52: 209627,   # OTTAPALAM
    53: 182603,   # KONGAD
    54: 206436,   # MANNARKAD
    55: 195429,   # MALAMPUZHA
    56: 176224,   # PALAKKAD
    57: 164930,   # TARUR
    58: 172015,   # CHITTUR
    59: 181690,   # NENMARA
    60: 165657,   # ALATHUR
    61: 203956,   # CHELAKKARA
    62: 196839,   # KUNNAMKULAM
    63: 218704,   # GURUVAYOOR
    64: 222278,   # MANALUR
    65: 201786,   # WADAKKANCHERY
    66: 188395,   # OLLUR
    67: 161225,   # THRISSUR
    68: 203427,   # NATTIKA
    69: 182716,   # KAIPAMANGALAM
    70: 194592,   # IRINJALAKKUDA
    71: 192377,   # PUTHUKKAD
    72: 179208,   # CHALAKKUDY
    73: 187212,   # KODUNGALLUR
    74: 180299,   # PERUMBAVOOR
    75: 170404,   # ANGAMALY
    76: 194360,   # ALUVA
    77: 197712,   # KALAMASSERY
    78: 191646,   # PARAVUR
    79: 161285,   # VYPEN
    80: 165675,   # KOCHI
    81: 187923,   # THRIPUNITHURA
    82: 136223,   # ERANAKULAM
    83: 176387,   # THRIKKAKARA
    84: 188291,   # KUNNATHUNAD
    85: 195421,   # PIRAVOM
    86: 186254,   # MUVATTUPUZHA
    87: 171968,   # KOTHAMANGALAM
    88: 142265,   # DEVIKULAM
    89: 150303,   # UDUMBANCHOLA
    90: 188495,   # THODUPUZHA
    91: 167822,   # IDUKKI
    92: 156542,   # PEERUMADE
    93: 176585,   # PALA
    94: 175905,   # KADUTHURUTHY
    95: 155957,   # VAIKOM
    96: 158256,   # ETTUMANOOR
    97: 149573,   # KOTTAYAM
    98: 170254,   # PUTHUPPALLY
    99: 162885,   # CHANGANASSERY
    100: 177500,  # KANJIRAPPALLY
    101: 184665,  # POONJAR
    102: 191465,  # AROOR
    103: 206016,  # CHERTHALA
    104: 191880,  # ALAPPUZHA
    105: 171203,  # AMBALAPUZHA
    106: 153981,  # KUTTANAD
    107: 184457,  # HARIPAD
    108: 201394,  # KAYAMKULAM
    109: 192435,  # MAVELIKARA
    110: 189866,  # CHENGANNUR
    111: 198395,  # THIRUVALLA
    112: 176015,  # RANNI
    113: 215168,  # ARANMULA
    114: 189366,  # KONNI
    115: 201200,  # ADOOR
    116: 214513,  # KARUNAGAPPALLY
    117: 178798,  # CHAVARA
    118: 205694,  # KUNNATHUR
    119: 193272,  # KOTTARAKKARA
    120: 179783,  # PATHANAPURAM
    121: 197346,  # PUNALUR
    122: 201716,  # CHADAYAMANGALAM
    123: 206464,  # KUNDARA
    124: 164541,  # KOLLAM
    125: 168865,  # ERAVIPURAM
    126: 177000,  # CHATHANNUR
    127: 183280,  # VARKALA
    128: 197945,  # ATTINGAL
    129: 195296,  # CHIRAYINKEEZHU
    130: 198042,  # NEDUMANGAD
    131: 187828,  # VAMANAPURAM
    132: 164561,  # KAZHAKKOOTTAM
    133: 165272,  # VATTIYOORKAVU
    134: 158545,  # THIRUVANANTHAPURAM
    135: 171178,  # NEMOM
    136: 181308,  # ARUVIKKARA
    137: 195648,  # PARASSALA
    138: 177094,  # KATTAKKADA
    139: 201200,  # KOVALAM
    140: 167377,  # NEYYATTINKARA
}

# ── 2026 Voter Turnout % — AC number → polling percentage
# Source: OpenDataKerala (https://opendatakerala.org/KLA2026/)
TURNOUT_2026 = {
    1:  81.04,  # MANJESHWAR
    2:  79.61,  # KASARAGOD
    3:  78.07,  # UDMA
    4:  77.24,  # KANHANGAD
    5:  79.64,  # TRIKARIPUR
    6:  80.57,  # PAYYANNUR
    7:  76.99,  # KALLIASSERI
    8:  81.01,  # TALIPARAMBA
    9:  74.32,  # IRIKKUR
    10: 77.71,  # AZHIKODE
    11: 75.61,  # KANNUR
    12: 81.44,  # DHARMADAM
    13: 76.33,  # THALASSERY
    14: 78.46,  # KUTHUPARAMBA
    15: 82.24,  # MATTANNUR
    16: 79.10,  # PERAVOOR
    17: 78.96,  # MANANTHAVADY
    18: 77.21,  # SULTHANBATHERY
    19: 80.35,  # KALPETTA
    20: 79.51,  # VADAKARA
    21: 81.06,  # KUTTIADI
    22: 79.46,  # NADAPURAM
    23: 79.44,  # QUILANDY
    24: 81.56,  # PERAMBRA
    25: 81.83,  # BALUSSERY
    26: 82.45,  # ELATHUR
    27: 80.23,  # KOZHIKODE NORTH
    28: 81.07,  # KOZHIKODE SOUTH
    29: 83.77,  # BEYPORE
    30: 84.83,  # KUNNAMANGALAM
    31: 80.98,  # KODUVALLY
    32: 80.35,  # THIRUVAMBADY
    33: 82.49,  # KONDOTTY
    34: 83.27,  # ERANAD
    35: 79.19,  # NILAMBUR
    36: 81.33,  # WANDOOR
    37: 82.52,  # MANJERI
    38: 80.25,  # PERINTHALMANNA
    39: 80.30,  # MANKADA
    40: 81.77,  # MALAPPURAM
    41: 79.83,  # VENGARA
    42: 80.92,  # VALLIKKUNNU
    43: 78.53,  # TIRURANGADI
    44: 79.97,  # TANUR
    45: 76.84,  # TIRUR
    46: 77.93,  # KOTTAKKAL
    47: 77.80,  # THAVANUR
    48: 74.22,  # PONNANI
    49: 78.38,  # THRITHALA
    50: 78.79,  # PATTAMBI
    51: 78.82,  # SHORNUR
    52: 79.34,  # OTTAPALAM
    53: 79.63,  # KONGAD
    54: 79.73,  # MANNARKAD
    55: 81.60,  # MALAMPUZHA
    56: 81.59,  # PALAKKAD
    57: 78.42,  # TARUR
    58: 84.63,  # CHITTUR
    59: 80.90,  # NENMARA
    60: 79.17,  # ALATHUR
    61: 78.89,  # CHELAKKARA
    62: 77.14,  # KUNNAMKULAM
    63: 73.37,  # GURUVAYOOR
    64: 75.89,  # MANALUR
    65: 79.67,  # WADAKKANCHERY
    66: 79.60,  # OLLUR
    67: 75.70,  # THRISSUR
    68: 76.38,  # NATTIKA
    69: 77.07,  # KAIPAMANGALAM
    70: 76.87,  # IRINJALAKKUDA
    71: 78.98,  # PUTHUKKAD
    72: 75.55,  # CHALAKKUDY
    73: 77.57,  # KODUNGALLUR
    74: 80.40,  # PERUMBAVOOR
    75: 75.62,  # ANGAMALY
    76: 80.78,  # ALUVA
    77: 81.59,  # KALAMASSERY
    78: 81.96,  # PARAVUR
    79: 80.50,  # VYPEN
    80: 80.33,  # KOCHI
    81: 81.40,  # THRIPUNITHURA
    82: 78.17,  # ERANAKULAM
    83: 78.85,  # THRIKKAKARA
    84: 84.09,  # KUNNATHUNAD
    85: 76.43,  # PIRAVOM
    86: 78.11,  # MUVATTUPUZHA
    87: 79.30,  # KOTHAMANGALAM
    88: 77.87,  # DEVIKULAM
    89: 79.51,  # UDUMBANCHOLA
    90: 75.97,  # THODUPUZHA
    91: 75.40,  # IDUKKI
    92: 77.52,  # PEERUMADE
    93: 75.07,  # PALA
    94: 69.34,  # KADUTHURUTHY
    95: 76.74,  # VAIKOM
    96: 76.09,  # ETTUMANOOR
    97: 74.71,  # KOTTAYAM
    98: 73.74,  # PUTHUPPALLY
    99: 73.16,  # CHANGANASSERY
    100: 74.91, # KANJIRAPPALLY
    101: 76.99, # POONJAR
    102: 83.35, # AROOR
    103: 82.07, # CHERTHALA
    104: 81.29, # ALAPPUZHA
    105: 80.75, # AMBALAPUZHA
    106: 71.57, # KUTTANAD
    107: 76.33, # HARIPAD
    108: 75.64, # KAYAMKULAM
    109: 72.55, # MAVELIKARA
    110: 71.05, # CHENGANNUR
    111: 69.47, # THIRUVALLA
    112: 68.98, # RANNI
    113: 71.50, # ARANMULA
    114: 69.90, # KONNI
    115: 73.50, # ADOOR
    116: 78.82, # KARUNAGAPPALLY
    117: 77.93, # CHAVARA
    118: 77.81, # KUNNATHUR
    119: 75.12, # KOTTARAKKARA
    120: 75.17, # PATHANAPURAM
    121: 70.99, # PUNALUR
    122: 74.43, # CHADAYAMANGALAM
    123: 78.24, # KUNDARA
    124: 77.43, # KOLLAM
    125: 77.33, # ERAVIPURAM
    126: 75.89, # CHATHANNUR
    127: 73.96, # VARKALA
    128: 73.82, # ATTINGAL
    129: 74.13, # CHIRAYINKEEZHU
    130: 78.36, # NEDUMANGAD
    131: 77.46, # VAMANAPURAM
    132: 78.62, # KAZHAKKOOTTAM
    133: 76.92, # VATTIYOORKAVU
    134: 74.89, # THIRUVANANTHAPURAM
    135: 80.62, # NEMOM
    136: 79.10, # ARUVIKKARA
    137: 77.59, # PARASSALA
    138: 80.72, # KATTAKKADA
    139: 75.54, # KOVALAM
    140: 77.54, # NEYYATTINKARA
}


class Command(BaseCommand):
    help = 'Import 2026 actual voter counts and turnout % — computes real votes_polled per constituency'

    def handle(self, *args, **options):
        self.stdout.write("Importing 2026 actual voter registration + turnout data...\n")

        # Validate coverage
        missing_electors = set(TURNOUT_2026) - set(ELECTORS_2026)
        missing_turnout  = set(ELECTORS_2026) - set(TURNOUT_2026)
        if missing_electors:
            self.stdout.write(self.style.WARNING(f"  ACs in turnout but not electors: {sorted(missing_electors)}"))
        if missing_turnout:
            self.stdout.write(self.style.WARNING(f"  ACs in electors but not turnout: {sorted(missing_turnout)}"))

        matched = 0
        skipped = 0

        with transaction.atomic():
            constituencies = {c.number: c for c in Constituency.objects.all()}

            for ac_no, total_electors in sorted(ELECTORS_2026.items()):
                polling_pct = TURNOUT_2026.get(ac_no)
                if polling_pct is None:
                    self.stdout.write(self.style.WARNING(f"  [SKIP] AC {ac_no}: no turnout data"))
                    skipped += 1
                    continue

                constituency = constituencies.get(ac_no)
                if not constituency:
                    self.stdout.write(self.style.WARNING(f"  [SKIP] AC {ac_no}: not found in DB"))
                    skipped += 1
                    continue

                votes_polled = int(total_electors * polling_pct / 100)

                live, _ = LiveResult.objects.get_or_create(
                    constituency=constituency,
                    defaults={'total_electors': total_electors, 'votes_polled': votes_polled}
                )
                live.total_electors = total_electors
                live.votes_polled = votes_polled
                live.save(update_fields=['total_electors', 'votes_polled'])

                self.stdout.write(
                    f"  AC {ac_no:>3}  {constituency.name:<25} "
                    f"electors={total_electors:>7,}  "
                    f"turnout={polling_pct:>5.2f}%  "
                    f"votes_polled={votes_polled:>7,}"
                )
                matched += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDone — {matched} updated, {skipped} skipped"
        ))
