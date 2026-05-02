"""
Seed PartyAllianceYear table with election-year-specific alliance data.

This is the single source of truth for which party belonged to which alliance
in a given election. It also normalises party code variants/aliases that appear
in source CSVs (e.g. RMPOI -> UDF, same as RMPI).

Usage:
    python manage.py seed_party_alliances
    python manage.py seed_party_alliances --clear   # wipe and re-seed
"""

from django.core.management.base import BaseCommand
from core.models import PartyAllianceYear


# ---------------------------------------------------------------------------
# 2021 Kerala Legislative Assembly election
# Source: Wikipedia / ECI official alliance declarations
# Format: (party_code_in_csv, canonical_code, alliance, color_hex)
# If canonical_code == party_code_in_csv just put ''
# ---------------------------------------------------------------------------
LA_2021 = [
    # LDF -------------------------------------------------------------------
    ('CPI(M)',   '',        'LDF', '#ED1E26'),   # Communist Party of India (Marxist)
    ('CPIM',    '',        'OTH', '#808080'),   # NOT CPI(M) — obscure fringe party (Rajesh Appatt etc.)
    ('CPI',      '',        'LDF', '#FF4444'),   # Communist Party of India
    ('KEC(M)',   '',        'LDF', '#8B4513'),   # Kerala Congress (M) - Jose K. Mani faction
    ('KC(M)',   'KEC(M)',  'LDF', '#8B4513'),   # alias used in some CSVs
    ('JD(S)',    '',        'LDF', '#006400'),   # Janata Dal (Secular) - LDF faction
    ('NCP',      '',        'LDF', '#00BFFF'),   # Nationalist Congress Party
    ('NCP(M)',  'NCP',     'LDF', '#00BFFF'),   # alias
    ('LJD',      '',        'LDF', '#DAA520'),   # Loktantrik Janata Dal
    ('INL',      '',        'LDF', '#2E8B57'),   # Indian National League
    ('CON(S)',   '',        'LDF', '#87CEEB'),   # Congress (S)
    ('CONG(S)', 'CON(S)',  'LDF', '#87CEEB'),   # alias
    ('C(S)',    'CON(S)',  'LDF', '#87CEEB'),   # short-form alias in 2021 CSV
    ('KEC(B)',   '',        'LDF', '#A0522D'),   # Kerala Congress (B) - R. Balakrishna Pillai
    ('KC(B)',   'KEC(B)',  'LDF', '#A0522D'),   # alias
    ('JKC',      '',        'LDF', '#B8860B'),   # Janadhipathya Kerala Congress

    # UDF -------------------------------------------------------------------
    ('INC',      '',        'UDF', '#19AAED'),   # Indian National Congress
    ('IUML',     '',        'UDF', '#0F8A3C'),   # Indian Union Muslim League
    ('KEC',      '',        'UDF', '#1E90FF'),   # Kerala Congress (P. J. Joseph)
    ('KC',      'KEC',     'UDF', '#1E90FF'),   # alias
    ('RSP',      '',        'UDF', '#FF6347'),   # Revolutionary Socialist Party - A. A. Aziz faction
    ('NCK',      '',        'UDF', '#4682B4'),   # Nationalist Congress Kerala (Mani C. Kappan)
    ('KEC(J)',   '',        'UDF', '#5F9EA0'),   # Kerala Congress (Jacob)
    ('KC(J)',   'KEC(J)',  'UDF', '#5F9EA0'),   # alias
    ('CMP',      '',        'UDF', '#6495ED'),   # Congress (M) Party - C. P. John
    ('RMPI',     '',        'UDF', '#DC143C'),   # Revolutionary Marxist Party of India - N. Venu
    ('RMPOI',  'RMPI',    'UDF', '#DC143C'),   # typo/variant in 2021 CSV (e.g. K.K.REMA, Vadakara)
    ('RMP',    'RMPI',    'UDF', '#DC143C'),   # shorter alias
    ('KDP',      '',        'UDF', '#4B9CD3'),   # Kerala Democratic Party (Elathur 2021 - Zulphikar Mayoori)

    # NDA -------------------------------------------------------------------
    ('BJP',      '',        'NDA', '#FF9933'),   # Bharatiya Janata Party - 113 seats
    ('BDJS',     '',        'NDA', '#FFD700'),   # Bharat Dharma Jana Sena - 21 seats
    ('AIADMK',   '',        'NDA', '#D4AC0D'),   # All India Anna Dravida Munnetra Kazhagam - 2 seats
    ('ADMK',   'AIADMK',  'NDA', '#D4AC0D'),   # ADMK short alias in 2021 CSV
    ('KKC',      '',        'NDA', '#CD853F'),   # Kerala Kanavu Congress (Vishnupuram Chandrasekharan) - 1 seat
    ('JRP',      '',        'NDA', '#B8860B'),   # Janadhipathya Rashtriya Party - C.K.Janu - 1 seat

    ('NSC',      '',        'LDF', '#6B8E23'),   # National Secular Congress (V.Abdurahiman) - LDF ally (Tanur 2021)

    # OTH -------------------------------------------------------------------
    ('IND',      '',        'OTH', '#808080'),
    # Alliance-backed independents (pseudo-codes used for specific known IND candidates)
    ('IND-LDF',  '',        'LDF', '#ED1E26'),   # LDF-backed independent
    ('IND-UDF',  '',        'UDF', '#19AAED'),   # UDF-backed independent
    ('IND-NDA',  '',        'NDA', '#FF9933'),   # NDA-backed independent
    ('IND (CPI(M))', '', 'LDF', '#ED1E26'),      # IND with CPI(M) backing (e.g. Chavara 2021)
    ('WPI',      '',        'OTH', '#800080'),
    ('WPOI',   'WPI',     'OTH', '#800080'),   # WPI alias in 2021 CSV
    ('BSP',      '',        'OTH', '#00008B'),
    ('SUCI',     '',        'OTH', '#B22222'),
    ('AAP',      '',        'OTH', '#0066CC'),
    ('NOTA',     '',        'OTH', '#A9A9A9'),
    ('RJD',      '',        'OTH', '#336699'),   # Rashtriya Janata Dal - no Kerala front in 2021
    ('JD(U)',    '',        'OTH', '#008000'),   # Janata Dal (United) - not in any 2021 Kerala front
    ('SHS',      '',        'OTH', '#FF6600'),   # Shiv Sena - not in any 2021 Kerala front
    ('AITC',     '',        'OTH', '#1B8A00'),   # All India Trinamool Congress - not in any 2021 Kerala front
    # Small fringe / unrecognised parties in 2021 CSV - all OTH
    ('ABHM',     '',        'OTH', '#808080'),
    ('ADHRMPI',  '',        'OTH', '#808080'),
    ('BHUDRP',   '',        'OTH', '#808080'),
    ('CMPKSC',   '',        'OTH', '#808080'),
    ('DHRMP',    '',        'OTH', '#808080'),
    ('DSJP',     '',        'OTH', '#808080'),
    ('ICSP',     '',        'OTH', '#808080'),
    ('KJPS',     '',        'OTH', '#808080'),
    ('KLJP',     '',        'OTH', '#808080'),
    ('MCPI',     '',        'OTH', '#808080'),
    ('NALAP',    '',        'OTH', '#808080'),
    ('NWLBRP',   '',        'OTH', '#808080'),
    ('RPI(A)',   '',        'OTH', '#808080'),
    ('SDC',      '',        'OTH', '#808080'),
    ('SMFB',     '',        'OTH', '#808080'),
    ('SWARAJ',   '',        'OTH', '#808080'),
    ('SWJP',     '',        'OTH', '#808080'),
]


# ---------------------------------------------------------------------------
# 2006 Kerala Legislative Assembly election
# Source: Wikipedia alliance declarations
#
# Key differences from later years:
#   RSP      = LDF (4 seats, Kovoor Kunjumon). Switches to UDF from 2011 onward.
#   KEC      = LDF  — Kerala Congress (Joseph), P. J. Joseph, 6 seats
#   KCS      = LDF  — Kerala Congress (Secular), P. C. George, 1 seat
#   KEC(B)   = UDF  — Kerala Congress (B), R. Balakrishna Pillai, 2 seats
#              (Switches to LDF from 2016 onward)
#   MUL      = UDF  — alias for IUML (Muslim League Kerala State Committee)
#   CMPKSC   = UDF  — Communist Marxist Party (C. P. John faction)
#   DIC      = UDF  — Democratic Indira Congress (Karunakaran)
#   RSPK(B)  = UDF  — RSP (Baby John faction)
#   INL      = LDF  — Indian National League (3 seats)
#   C(S)     = LDF  — Congress (Secular), Kadannappalli Ramachandran
#   NCP      = LDF  — Nationalist Congress Party (2 seats)
#   JPSS     = UDF  — Janathipathiya Samrakshana Samithy, K. R. Gouri Amma
# ---------------------------------------------------------------------------
LA_2006 = [
    # LDF -------------------------------------------------------------------
    ('CPI(M)',   '',         'LDF', '#ED1E26'),   # 85 seats
    ('CPI',      '',         'LDF', '#FF4444'),   # 24 seats
    ('JD(S)',    '',         'LDF', '#006400'),   # 8 seats (Mathew T. Thomas)
    ('KEC',      '',         'LDF', '#1E90FF'),   # Kerala Congress (Joseph) — P.J. Joseph, 6 seats
    ('NCP',      '',         'LDF', '#00BFFF'),   # 2 seats
    ('C(S)',     '',         'LDF', '#87CEEB'),   # Congress (Secular) — Kadannappalli, 1 seat
    ('KCS',      '',         'LDF', '#7B68EE'),   # Kerala Congress (Secular) — P.C. George, 1 seat
    ('INL',      '',         'LDF', '#2E8B57'),   # Indian National League, 3 seats
    ('RSP',      '',         'LDF', '#FF6347'),   # Revolutionary Socialist Party — LDF in 2006 (4 seats)

    # UDF -------------------------------------------------------------------
    ('INC',      '',         'UDF', '#19AAED'),   # 77 seats
    ('MUL',      'IUML',     'UDF', '#0F8A3C'),   # Muslim League Kerala State Committee = IUML, 21 seats
    ('DIC',      '',         'UDF', '#9370DB'),   # Democratic Indira Congress (Karunakaran), 18 seats
    ('KEC(M)',   '',         'UDF', '#3399FF'),   # Kerala Congress (Mani) — K.M. Mani, 11 seats
    ('JPSS',     '',         'UDF', '#FF8C00'),   # Janathipathiya Samrakshana Samithy — K.R. Gouri Amma, 5 seats
    ('CMPKSC',   '',         'UDF', '#6495ED'),   # Communist Marxist Party (C.P. John), 3 seats
    ('KEC(B)',   '',         'UDF', '#A0522D'),   # Kerala Congress (B) — R. Balakrishna Pillai, 2 seats
    ('RSPK(B)',  '',         'UDF', '#CD5C5C'),   # RSP (Baby John faction), 1 seat

    # NDA -------------------------------------------------------------------
    ('BJP',      '',         'NDA', '#FF9933'),   # 140 seats (contested alone)

    # OTH -------------------------------------------------------------------
    ('IND',      '',         'OTH', '#808080'),
    ('BSP',      '',         'OTH', '#00008B'),
    ('AIADMK',   '',         'OTH', '#D4AC0D'),
    ('LJP',      '',         'OTH', '#808080'),   # Lok Jan Party
    ('RJD',      '',         'OTH', '#336699'),   # Rashtriya Janata Dal
    ('JD(U)',    '',         'OTH', '#808080'),   # Janata Dal (United) — no Kerala coalition 2006
    ('SLAP',     '',         'OTH', '#808080'),
    ('SWJP',     '',         'OTH', '#808080'),
    ('UIPP',     '',         'OTH', '#808080'),
]


# ---------------------------------------------------------------------------
# 2011 Kerala Legislative Assembly election
# Source: Wikipedia alliance declarations
#
# Key differences from 2006:
#   RSP      = UDF  — A. A. Aziz faction, 4 seats (switched from LDF)
#   KRSP     = UDF  — RSP (Baby John faction), 1 seat (Shibu Baby John)
#   CPM      = LDF  — CSV uses 'CPM' for CPI(M)
#   SJD      = UDF  — Socialist Janata (Democratic), M. P. Veerendra Kumar, 6 seats
#                      DIFFERENT party from JD(S) which is still LDF
#   JD(S)    = LDF  — Janata Dal (Secular), Mathew T. Thomas, 5 seats
#   KEC(B)   = UDF  — still R. Balakrishna Pillai (switches to LDF only in 2016)
#   KC(AMG)  = LDF  — Kerala Congress (Anti-merger Group), 3 seats
#   MUL      = UDF  — IUML alias
#   KEC(M)   = UDF  — Kerala Congress (Mani), K. M. Mani, 15 seats (UDF in 2011)
#   CMPKSC   = UDF  — C. P. John faction, 3 seats
#   JPSS     = UDF  — K. R. Gouri Amma, 4 seats
#   KEC(J)   = UDF  — Kerala Congress (Jacob), T. M. Jacob, 3 seats
# ---------------------------------------------------------------------------
LA_2011 = [
    # LDF -------------------------------------------------------------------
    ('CPI(M)',   '',         'LDF', '#ED1E26'),   # 93 seats
    ('CPM',     'CPI(M)',   'LDF', '#ED1E26'),   # CSV alias for CPI(M)
    ('CPI',      '',         'LDF', '#FF4444'),   # 27 seats
    ('JD(S)',    '',         'LDF', '#006400'),   # Janata Dal (Secular) — Mathew T. Thomas, 5 seats
    ('NCP',      '',         'LDF', '#00BFFF'),   # 4 seats
    ('INL',      '',         'LDF', '#2E8B57'),   # Indian National League, 3 seats
    ('KC(AMG)', '',          'LDF', '#8B6914'),   # Kerala Congress (Anti-merger Group), 3 seats
    ('C(S)',     '',         'LDF', '#87CEEB'),   # Congress (Secular) — Kadannappalli, 1 seat
    ('CON(S)',  'C(S)',      'LDF', '#87CEEB'),   # alias

    # UDF -------------------------------------------------------------------
    ('INC',      '',         'UDF', '#19AAED'),   # 82 seats
    ('MUL',      'IUML',     'UDF', '#0F8A3C'),   # Muslim League Kerala State Committee = IUML, 24 seats
    ('KEC(M)',   '',         'UDF', '#3399FF'),   # Kerala Congress (Mani) — K.M. Mani, 15 seats
    ('SJD',      '',         'UDF', '#6B8E23'),   # Socialist Janata (Democratic) — M.P. Veerendra Kumar, 6 seats
    ('JPSS',     '',         'UDF', '#FF8C00'),   # Janathipathiya Samrakshana Samithy — K.R. Gouri Amma, 4 seats
    ('RSP',      '',         'LDF', '#FF6347'),   # Revolutionary Socialist Party — LDF until March 2014 (left LDF 2014, 4 seats)
    ('CMPKSC',   '',         'UDF', '#6495ED'),   # Communist Marxist Party (C.P. John), 3 seats
    ('KEC(J)',   '',         'UDF', '#5F9EA0'),   # Kerala Congress (Jacob) — T.M. Jacob, 3 seats
    ('KC(J)',   'KEC(J)',    'UDF', '#5F9EA0'),   # alias
    ('KEC(B)',   '',         'UDF', '#A0522D'),   # Kerala Congress (B) — R. Balakrishna Pillai, 2 seats
    ('KRSP',     '',         'UDF', '#CD5C5C'),   # RSP (Baby John / Shibu Baby John), 1 seat

    # NDA -------------------------------------------------------------------
    ('BJP',      '',         'NDA', '#FF9933'),   # 139 seats
    ('JD(U)',    '',         'NDA', '#FFA500'),   # 1 seat

    # OTH -------------------------------------------------------------------
    ('IND',      '',         'OTH', '#808080'),
    # Alliance-backed independents
    ('IND-LDF',  '',         'LDF', '#ED1E26'),   # LDF-backed independent
    ('IND-UDF',  '',         'UDF', '#19AAED'),   # UDF-backed independent
    ('IND-NDA',  '',         'NDA', '#FF9933'),   # NDA-backed independent (e.g. CK Janu style, won't apply to 2011 but kept for consistency)
    ('BSP',      '',         'OTH', '#00008B'),
    ('SDPI',     '',         'OTH', '#4B0082'),
    ('SHS',      '',         'OTH', '#FF6600'),   # Shiv Sena (44 seats, no coalition)
    ('SUCI',     '',         'OTH', '#B22222'),   # Socialist Unity Centre of India
    ('AIADMK',   '',         'OTH', '#D4AC0D'),
    ('PDP',      '',         'OTH', '#8B0000'),   # Peoples Democratic Party
    ('CPI(ML)(L)', '',       'OTH', '#CC0000'),
    ('LJP',      '',         'OTH', '#808080'),
    ('SLAP',     '',         'OTH', '#808080'),
    ('SWJP',     '',         'OTH', '#808080'),
    ('KJ',       '',         'OTH', '#808080'),
    ('DPSP',     '',         'OTH', '#808080'),
]


# ---------------------------------------------------------------------------
# 2016 Kerala Legislative Assembly election
# Source: Wikipedia / ECI alliance declarations + Detailed Results.xlsx
# LUF (Left United Front: RMP, SUCI, MCPI-U) is NOT counted as an alliance — OTH
# ---------------------------------------------------------------------------
LA_2016 = [
    # LDF -------------------------------------------------------------------
    ('CPI(M)',   '',        'LDF', '#ED1E26'),   # Communist Party of India (Marxist) - 90 seats
    ('CPM',    'CPI(M)',   'LDF', '#ED1E26'),   # ECI xlsx alias
    ('CPIM',   '',         'OTH', '#808080'),   # NOT CPI(M) — obscure fringe party in 2016
    ('CPI',      '',        'LDF', '#FF4444'),   # Communist Party of India - 25 seats
    ('JD(S)',    '',        'LDF', '#006400'),   # Janata Dal (Secular) - 5 seats (LDF in 2016)
    ('KEC(B)',   '',        'LDF', '#A0522D'),   # Kerala Congress (B) - R. Balakrishna Pillai - 1 seat
    ('KC(B)',   'KEC(B)',  'LDF', '#A0522D'),
    ('INL',      '',        'LDF', '#2E8B57'),   # Indian National League - 3 seats (LDF ally)
    ('CON(S)',   '',        'LDF', '#87CEEB'),   # Congress (Secular) - Kadannappalli - 1 seat
    ('CONG(S)', 'CON(S)',  'LDF', '#87CEEB'),
    ('C(S)',    'CON(S)',  'LDF', '#87CEEB'),   # ECI xlsx code for Cong(S)
    ('JKC',      '',        'LDF', '#B8860B'),   # Janadhipathya Kerala Congress (Francis George) - 4 seats
    ('NCP',      '',        'LDF', '#00BFFF'),   # Nationalist Congress Party (T.P.Peethambaran) - 4 seats
    ('NSC',      '',        'LDF', '#6B8E23'),   # National Secular Congress (V.Abdurahiman) - LDF
    ('KC(ST)',   '',        'LDF', '#996633'),   # Kerala Congress (Skaria Thomas) - LDF ally 2016 - 1 seat
    ('KCST',   'KC(ST)',  'LDF', '#996633'),   # ECI xlsx alias
    ('KC(S)',    '',        'LDF', '#7B68EE'),   # Kerala Congress (Secular) - C.F.Thomas - LDF
    ('KCS',    'KC(S)',   'LDF', '#7B68EE'),   # ECI xlsx alias
    ('JSS',      '',        'LDF', '#556B2F'),   # Janathipathiya Samrakshana Samithy - 4 seats
    ('CMP(A)',   '',        'LDF', '#8B0000'),   # Communist Marxist Party (Aravindakshan) - 1 seat (LDF, distinct from CMP=C.P.John which is UDF)
    ('CMPA',   'CMP(A)',  'LDF', '#8B0000'),   # ECI xlsx alias
    ('RSP(L)',   '',        'LDF', '#B22222'),   # Revolutionary Socialist Party (Leninist) - Kovoor Kunjumon - 1 seat
    ('RSPL',   'RSP(L)',  'LDF', '#B22222'),   # ECI xlsx alias

    # UDF -------------------------------------------------------------------
    ('INC',      '',        'UDF', '#19AAED'),   # Indian National Congress - 87 seats
    ('IUML',     '',        'UDF', '#0F8A3C'),   # Indian Union Muslim League - 24 seats
    ('KEC(M)',   '',        'UDF', '#3399FF'),   # Kerala Congress (Mani) - 15 seats (UDF in 2016)
    ('KC(M)',   'KEC(M)',  'UDF', '#3399FF'),
    ('JD(U)',    '',        'UDF', '#008000'),   # Janata Dal (United) - 7 seats (UDF ally in 2016, NOT NDA)
    ('RSP',      '',        'UDF', '#FF6347'),   # Revolutionary Socialist Party (A.A.Aziz faction) - 5 seats
    ('CMPKSC',   '',        'UDF', '#6495ED'),   # Communist Marxist Party (C.P.John faction) - UDF ally
    ('KEC(J)',   '',        'UDF', '#5F9EA0'),   # Kerala Congress (Jacob) - Anoop Jacob - 1 seat
    ('KC(J)',   'KEC(J)',  'UDF', '#5F9EA0'),
    ('KEC',      '',        'UDF', '#1E90FF'),   # Kerala Congress (P.J.Joseph main faction)
    ('KC',      'KEC',    'UDF', '#1E90FF'),

    # NDA -------------------------------------------------------------------
    ('BJP',      '',        'NDA', '#FF9933'),   # Bharatiya Janata Party - 98 seats
    ('BDJS',     '',        'NDA', '#FFD700'),   # Bharat Dharma Jana Sena - 36 seats
    ('KC(T)',    '',        'NDA', '#CD853F'),   # Kerala Congress (Thomas) - P.C.Thomas - 4 seats
    ('KCT',    'KC(T)',   'NDA', '#CD853F'),   # ECI xlsx alias
    ('JSS(R)',   '',        'NDA', '#A0522D'),   # Janadhipathya Samrakshana Samithi (Rajan Babu) - 1 seat
    ('JRS',      '',        'NDA', '#B8860B'),   # Janadhipathya Rashtriya Sabha (C.K.Janu) - 1 seat (NDA in 2016, LDF-JRP in 2021)

    # OTH (includes LUF parties — LUF is NOT counted as a front, per policy) ------
    ('IND',      '',        'OTH', '#808080'),   # Independents
    # Alliance-backed independents (pseudo-codes used for specific known IND candidates)
    ('IND-LDF',  '',        'LDF', '#ED1E26'),   # LDF-backed independent
    ('IND-UDF',  '',        'UDF', '#19AAED'),   # UDF-backed independent
    ('IND-NDA',  '',        'NDA', '#FF9933'),   # NDA-backed independent
    ('IND (CPI(M))', '', 'LDF', '#ED1E26'),      # IND with CPI(M) backing (e.g. Koduvally 2016)
    ('SDPI',     '',        'OTH', '#4B0082'),   # Social Democratic Party of India
    ('BSP',      '',        'OTH', '#00008B'),   # Bahujan Samaj Party
    ('PDP',      '',        'OTH', '#8B0000'),   # Peoples Democratic Party (Abdul Nasar Madani)
    ('WPOI',    'WPI',     'OTH', '#800080'),   # Welfare Party of India (xlsx alias)
    ('WPI',      '',        'OTH', '#800080'),   # Welfare Party of India
    ('CPI(ML)(L)', '',     'OTH', '#CC0000'),   # CPI(ML) Liberation
    ('ADMK',   'AIADMK',  'OTH', '#D4AC0D'),   # AIADMK - independent (no Kerala front)
    ('AIADMK',   '',        'OTH', '#D4AC0D'),
    ('SP',       '',        'OTH', '#FF0000'),   # Samajwadi Party - 9 seats
    ('SHS',      '',        'OTH', '#FF6600'),   # Shiv Sena - 16 seats (no coalition in 2016 Kerala)
    # LUF parties → OTH (Left United Front is NOT recognised as alliance)
    ('SUCI',     '',        'OTH', '#B22222'),   # Socialist Unity Centre of India (Communist) - LUF
    ('MCPI',     '',        'OTH', '#8B0000'),   # Marxist Communist Party of India (United) - LUF
    ('RMPI',     '',        'OTH', '#DC143C'),   # Revolutionary Marxist Party of India - LUF
    ('RMPOI',  'RMPI',    'OTH', '#DC143C'),
    ('RMP',    'RMPI',    'OTH', '#DC143C'),
    # Miscellaneous fringe parties
    ('KLJP',     '',        'OTH', '#808080'),   # Kerala Lok Jan Party
    ('NOTA',     '',        'OTH', '#A9A9A9'),   # None of the above
    ('AKTP',     '',        'OTH', '#808080'),   # Akhila Kerala Thozhilali Party
    ('APOI',     '',        'OTH', '#808080'),   # Ambedkarite Party of India
    ('IGP',      '',        'OTH', '#808080'),   # Indian Gandhian Party
    ('PPGP',     '',        'OTH', '#808080'),   # Prarambha Pratinidhi Ganapam / fringe
    ('SDP',      '',        'OTH', '#808080'),   # Socialist Democratic Party (fringe)
]


# ---------------------------------------------------------------------------
# 2026 Kerala Legislative Assembly election
# Source: Wikipedia alliance declarations
# ---------------------------------------------------------------------------
LA_2026 = [
    # LDF -------------------------------------------------------------------
    ('CPI(M)',    '',          'LDF', '#ED1E26'),   # Communist Party of India (Marxist) - 77 seats
    ('CPIM',     'CPI(M)',    'LDF', '#ED1E26'),   # alias
    ('CPI',       '',          'LDF', '#FF4444'),   # Communist Party of India - 24 seats
    ('KC(M)',     '',          'LDF', '#8B4513'),   # Kerala Congress (M) - Jose K. Mani - 12 seats
    ('KEC(M)',    '',          'LDF', '#8B4513'),   # alias
    ('NCP(SP)',   '',          'LDF', '#00BFFF'),   # NCP – Sharadchandra Pawar - 3 seats
    ('RJD',       '',          'LDF', '#336699'),   # Rashtriya Janata Dal (LJD renamed) - 3 seats
    ('LJD',      'RJD',       'LDF', '#336699'),   # LJD alias (same party, renamed to RJD)
    ('JD(S)-LDF', '',          'LDF', '#006400'),   # Indian Socialist Janata Dal (JD(S) faction) - 1 seat
    ('ISJD',    'JD(S)-LDF',  'LDF', '#006400'),   # alias
    ('KEC(B)',    '',          'LDF', '#A0522D'),   # Kerala Congress (B) - K.B.Ganesh Kumar - 1 seat
    ('KC(B)',    'KEC(B)',     'LDF', '#A0522D'),   # alias
    ('INL',       '',          'LDF', '#2E8B57'),   # Indian National League - 1 seat
    ('CON(S)',    '',          'LDF', '#87CEEB'),   # Congress (Secular) - Kadannappalli - 1 seat
    ('C(S)',     'CON(S)',     'LDF', '#87CEEB'),   # alias
    ('CONG(S)',  'CON(S)',     'LDF', '#87CEEB'),   # alias
    ('RSP(L)',    '',          'LDF', '#B22222'),   # Revolutionary Socialist Party (Leninist) - 1 seat
    ('RSPL',    'RSP(L)',     'LDF', '#B22222'),   # alias

    # UDF -------------------------------------------------------------------
    ('INC',       '',          'UDF', '#19AAED'),   # Indian National Congress - 92 seats
    ('IUML',      '',          'UDF', '#0F8A3C'),   # Indian Union Muslim League - 26 seats
    ('KEC',       '',          'UDF', '#1E90FF'),   # Kerala Congress (P.J.Joseph) - 8 seats
    ('KC',       'KEC',        'UDF', '#1E90FF'),   # alias
    ('RSP',       '',          'UDF', '#FF6347'),   # Revolutionary Socialist Party (Shibu Baby John) - 4 seats
    ('KC(J)',     '',          'UDF', '#5F9EA0'),   # Kerala Congress (Jacob) - Anoop Jacob - 1 seat
    ('KEC(J)',   'KC(J)',      'UDF', '#5F9EA0'),   # alias
    ('RMPI',      '',          'UDF', '#DC143C'),   # Revolutionary Marxist Party of India - N.Venu - 1 seat
    ('RMP',      'RMPI',      'UDF', '#DC143C'),   # alias
    ('RMPOI',   'RMPI',       'UDF', '#DC143C'),   # alias
    ('CMP',       '',          'UDF', '#6495ED'),   # Communist Marxist Party - C.P.John - 1 seat

    # NDA -------------------------------------------------------------------
    ('BJP',       '',          'NDA', '#FF9933'),   # Bharatiya Janata Party - 98 seats
    ('BDJS',      '',          'NDA', '#FFD700'),   # Bharat Dharma Jana Sena - 22 seats
    ('TTP',       '',          'NDA', '#FF4500'),   # Twenty20 Party - Sabu M. Jacob - 19 seats

    # OTH -------------------------------------------------------------------
    ('IND',       '',          'OTH', '#808080'),
    ('NOTA',      '',          'OTH', '#A9A9A9'),
    ('BSP',       '',          'OTH', '#00008B'),
    ('AAP',       '',          'OTH', '#0066CC'),
    ('SDPI',      '',          'OTH', '#4B0082'),
    ('SUCI',      '',          'OTH', '#B22222'),
    ('DHRMP',     '',          'OTH', '#808080'),
    ('CPIML',     '',          'OTH', '#CC0000'),   # CPI(ML) Red Star
    ('CPIMLL',    '',          'OTH', '#CC0000'),   # CPI(ML) Liberation
    ('JRP',       '',          'OTH', '#808080'),   # Janam Rashtriya Party (not same as 2021 JRP)
    ('API',       '',          'OTH', '#808080'),   # Ambedkarite Party of India
    ('EPI',       '',          'OTH', '#808080'),   # Equality Party of India
    ('IGP',       '',          'OTH', '#808080'),   # Indian Gandhiyan Party
    ('NCP',       '',          'OTH', '#808080'),   # NCP (Sharad Pawar breakaway contesting alone — NOT LDF's NCP-SP)
    ('SP(I)',     '',          'OTH', '#808080'),   # Socialist Party (India)
    ('SRP',       '',          'OTH', '#808080'),   # Socialist Republican Party (Kerala)
]


DATASETS = {
    (2006, 'LA'): LA_2006,
    (2011, 'LA'): LA_2011,
    (2016, 'LA'): LA_2016,
    (2021, 'LA'): LA_2021,
    (2026, 'LA'): LA_2026,
}


class Command(BaseCommand):
    help = 'Seed PartyAllianceYear table with election-year-specific alliance data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all existing PartyAllianceYear records before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            count = PartyAllianceYear.objects.count()
            PartyAllianceYear.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing records'))

        total_created = 0
        total_updated = 0

        for (year, etype), entries in DATASETS.items():
            self.stdout.write(f'\nSeeding {year} {etype} ({len(entries)} entries)...')
            created = updated = 0
            for party_code, canonical, alliance, color in entries:
                _, was_created = PartyAllianceYear.objects.update_or_create(
                    party_code=party_code,
                    election_year=year,
                    election_type=etype,
                    defaults={
                        'canonical_code': canonical,
                        'alliance': alliance,
                        'color_code': color,
                    }
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            self.stdout.write(
                self.style.SUCCESS(f'  {created} created, {updated} updated')
            )
            total_created += created
            total_updated += updated

        self.stdout.write(self.style.SUCCESS(
            f'\nDone -- {total_created} created, {total_updated} updated across all elections'
        ))
