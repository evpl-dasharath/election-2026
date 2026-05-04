"""
Unified seed: Alliance, Party, PartyAlias, PartyAllianceYear, Districts, Constituencies.
Usage: python manage.py seed_all --data-dir ../data/
"""
import csv, re
from django.core.management.base import BaseCommand
from core.models import Alliance, District, Constituency, Party, PartyAlias, PartyAllianceYear

# Hardcoded AC# -> (name, district, reserved) — static Kerala data
CONSTITUENCY_DATA = [
    (1,'MANJESHWARAM','Kasaragod','GEN'),    (2,'KASARAGOD','Kasaragod','GEN'),
    (3,'UDMA','Kasaragod','GEN'),    (4,'KANHANGAD','Kasaragod','GEN'),
    (5,'THRIKARIPUR','Kasaragod','GEN'),    (6,'PAYYANUR','Kannur','GEN'),
    (7,'KALLIASSERI','Kannur','GEN'),    (8,'TALIPARAMBA','Kannur','GEN'),
    (9,'IRIKKUR','Kannur','GEN'),    (10,'AZHIKODE','Kannur','GEN'),
    (11,'KANNUR','Kannur','GEN'),    (12,'DHARMADOM','Kannur','GEN'),
    (13,'THALASSERY','Kannur','GEN'),    (14,'MATTANUR','Kannur','GEN'),
    (15,'KUTHUPARAMBA','Kannur','GEN'),    (16,'PERAVOOR','Kannur','GEN'),
    (17,'MANANTHAVADY','Wayanad','ST'),    (18,'SULTHAN BATHERY','Wayanad','ST'),
    (19,'KALPETTA','Wayanad','GEN'),    (20,'VADAKARA','Kozhikode','GEN'),
    (21,'KUTTIADY','Kozhikode','GEN'),    (22,'NADAPURAM','Kozhikode','GEN'),
    (23,'KOYILANDY','Kozhikode','GEN'),    (24,'PERAMBRA','Kozhikode','GEN'),
    (25,'BALUSSERY','Kozhikode','SC'),    (26,'ELATHUR','Kozhikode','GEN'),
    (27,'KOZHIKODE NORTH','Kozhikode','GEN'),    (28,'KOZHIKODE SOUTH','Kozhikode','GEN'),
    (29,'BEYPORE','Kozhikode','GEN'),    (30,'KUNNAMANGALAM','Kozhikode','GEN'),
    (31,'KODUVALLY','Kozhikode','GEN'),    (32,'THIRUVAMBADY','Kozhikode','GEN'),
    (33,'KONDOTTY','Malappuram','GEN'),    (34,'ERANAD','Malappuram','GEN'),
    (35,'NILAMBUR','Malappuram','GEN'),    (36,'WANDOOR','Malappuram','SC'),
    (37,'MANJERI','Malappuram','GEN'),    (38,'PERINTHALMANNA','Malappuram','GEN'),
    (39,'MANKADA','Malappuram','GEN'),    (40,'MALAPPURAM','Malappuram','GEN'),
    (41,'VENGARA','Malappuram','GEN'),    (42,'VALLIKKUNNU','Malappuram','GEN'),
    (43,'TIRURANGADI','Malappuram','GEN'),    (44,'TANUR','Malappuram','GEN'),
    (45,'TIRUR','Malappuram','GEN'),    (46,'KOTTAKKAL','Malappuram','GEN'),
    (47,'THAVANUR','Malappuram','GEN'),    (48,'PONNANI','Malappuram','GEN'),
    (49,'THRITHALA','Palakkad','GEN'),    (50,'PATTAMBI','Palakkad','GEN'),
    (51,'SHORNUR','Palakkad','GEN'),    (52,'OTTAPALAM','Palakkad','GEN'),
    (53,'KONGAD','Palakkad','SC'),    (54,'MANNARKKAD','Palakkad','GEN'),
    (55,'MALAMPUZHA','Palakkad','GEN'),    (56,'PALAKKAD','Palakkad','GEN'),
    (57,'TARUR','Palakkad','SC'),    (58,'CHITTUR','Palakkad','GEN'),
    (59,'NENMARA','Palakkad','GEN'),    (60,'ALATHUR','Palakkad','GEN'),
    (61,'CHELAKKARA','Thrissur','SC'),    (62,'KUNNAMKULAM','Thrissur','GEN'),
    (63,'GURUVAYUR','Thrissur','GEN'),    (64,'MANALUR','Thrissur','GEN'),
    (65,'WADAKKANCHERY','Thrissur','GEN'),    (66,'OLLUR','Thrissur','GEN'),
    (67,'THRISSUR','Thrissur','GEN'),    (68,'NATTIKA','Thrissur','SC'),
    (69,'KAIPAMANGALAM','Thrissur','GEN'),    (70,'IRINJALAKUDA','Thrissur','GEN'),
    (71,'PUTHUKKAD','Thrissur','GEN'),    (72,'CHALAKUDY','Thrissur','GEN'),
    (73,'KODUNGALLUR','Thrissur','GEN'),    (74,'PERUMBAVOOR','Ernakulam','GEN'),
    (75,'ANGAMALY','Ernakulam','GEN'),    (76,'ALUVA','Ernakulam','GEN'),
    (77,'KALAMASSERY','Ernakulam','GEN'),    (78,'PARAVUR','Ernakulam','GEN'),
    (79,'VYPIN','Ernakulam','GEN'),    (80,'KOCHI','Ernakulam','GEN'),
    (81,'THRIPPUNITHURA','Ernakulam','GEN'),    (82,'ERNAKULAM','Ernakulam','GEN'),
    (83,'THRIKKAKARA','Ernakulam','GEN'),    (84,'KUNNATHUNAD','Ernakulam','SC'),
    (85,'PIRAVOM','Ernakulam','GEN'),    (86,'MUVATTUPUZHA','Ernakulam','GEN'),
    (87,'KOTHAMANGALAM','Ernakulam','GEN'),    (88,'DEVIKULAM','Idukki','GEN'),
    (89,'UDUMBANCHOLA','Idukki','GEN'),    (90,'THODUPUZHA','Idukki','GEN'),
    (91,'IDUKKI','Idukki','GEN'),    (92,'PEERUMADE','Idukki','GEN'),
    (93,'PALA','Kottayam','GEN'),    (94,'KADUTHURUTHY','Kottayam','GEN'),
    (95,'VAIKOM','Kottayam','SC'),    (96,'ETTUMANOOR','Kottayam','GEN'),
    (97,'KOTTAYAM','Kottayam','GEN'),    (98,'PUTHUPPALLY','Kottayam','GEN'),
    (99,'CHANGANASSERY','Kottayam','GEN'),    (100,'KANJIRAPPALLY','Kottayam','GEN'),
    (101,'POONJAR','Kottayam','GEN'),    (102,'AROOR','Alappuzha','GEN'),
    (103,'CHERTHALA','Alappuzha','GEN'),    (104,'ALAPPUZHA','Alappuzha','GEN'),
    (105,'AMBALAPPUZHA','Alappuzha','GEN'),    (106,'KUTTANAD','Alappuzha','GEN'),
    (107,'HARIPAD','Alappuzha','GEN'),    (108,'KAYAMKULAM','Alappuzha','GEN'),
    (109,'MAVELIKARA','Alappuzha','GEN'),    (110,'CHENGANNUR','Alappuzha','GEN'),
    (111,'THIRUVALLA','Pathanamthitta','GEN'),    (112,'RANNI','Pathanamthitta','GEN'),
    (113,'ARANMULA','Pathanamthitta','GEN'),    (114,'KONNI','Pathanamthitta','GEN'),
    (115,'ADOOR','Pathanamthitta','GEN'),    (116,'KARUNAGAPALLY','Kollam','GEN'),
    (117,'CHAVARA','Kollam','GEN'),    (118,'KUNNATHUR','Kollam','GEN'),
    (119,'KOTTARAKKARA','Kollam','GEN'),    (120,'PATHANAPURAM','Kollam','GEN'),
    (121,'PUNALUR','Kollam','GEN'),    (122,'CHADAYAMANGALAM','Kollam','GEN'),
    (123,'KUNDARA','Kollam','GEN'),    (124,'KOLLAM','Kollam','GEN'),
    (125,'ERAVIPURAM','Kollam','GEN'),    (126,'CHATHANNOOR','Kollam','GEN'),
    (127,'VARKALA','Thiruvananthapuram','GEN'),    (128,'ATTINGAL','Thiruvananthapuram','GEN'),
    (129,'CHIRAYINKEEZHU','Thiruvananthapuram','GEN'),    (130,'NEDUMANGAD','Thiruvananthapuram','GEN'),
    (131,'VAMANAPURAM','Thiruvananthapuram','GEN'),    (132,'KAZHAKOOTAM','Thiruvananthapuram','GEN'),
    (133,'VATTIYOORKAVU','Thiruvananthapuram','GEN'),    (134,'THIRUVANANTHAPURAM','Thiruvananthapuram','GEN'),
    (135,'NEMOM','Thiruvananthapuram','GEN'),    (136,'ARUVIKKARA','Thiruvananthapuram','GEN'),
    (137,'PARASSALA','Thiruvananthapuram','GEN'),    (138,'KATTAKKADA','Thiruvananthapuram','GEN'),
    (139,'KOVALAM','Thiruvananthapuram','GEN'),    (140,'NEYYATTINKARA','Thiruvananthapuram','GEN'),
]

ALLIANCES = [
    ('LDF', 'Left Democratic Front',       '#ED1E26'),
    ('UDF', 'United Democratic Front',      '#19AAED'),
    ('NDA', 'National Democratic Alliance', '#FF9933'),
    ('OTH', 'Other',                        '#808080'),
]

DISTRICT_ORDER = {
    'Kasaragod':1,'Kannur':2,'Wayanad':3,'Kozhikode':4,'Malappuram':5,
    'Palakkad':6,'Thrissur':7,'Ernakulam':8,'Idukki':9,'Kottayam':10,
    'Alappuzha':11,'Pathanamthitta':12,'Kollam':13,'Thiruvananthapuram':14,
}

# (code, full_name, default_alliance_2026, color)
PARTIES = [
    # LDF
    ('CPI_M',  'Communist Party of India (Marxist)',           'LDF', '#ED1E26'),
    ('CPI',    'Communist Party of India',                     'LDF', '#FF4444'),
    ('KC_M',   'Kerala Congress (M)',                          'LDF', '#8B4513'),
    ('NCP',    'Nationalist Congress Party',                   'LDF', '#00BFFF'),
    ('RJD',    'Rashtriya Janata Dal',                         'LDF', '#336699'),
    ('JD_S',   'Janata Dal (Secular)',                         'LDF', '#006400'),
    ('ISJD',   'Indian Socialist Janata Dal',                  'LDF', '#006400'),
    ('INL',    'Indian National League',                       'LDF', '#2E8B57'),
    ('CON_S',  'Congress (Secular)',                           'LDF', '#87CEEB'),
    ('KC_B',   'Kerala Congress (B)',                          'LDF', '#A0522D'),
    ('JKC',    'Janadhipathya Kerala Congress',                'LDF', '#B8860B'),
    ('KC_AMG', 'Kerala Congress (Anti-merger Group)',           'LDF', '#8B6914'),
    ('NSC',    'National Secular Conference',                   'LDF', '#2E7D32'),
    ('RSP_L',  'Revolutionary Socialist Party (Leninist)',      'LDF', '#B22222'),
    ('KC_KST', 'Kerala Congress (Skaria Thomas)',               'LDF', '#8B6508'),
    ('CMA',    'Communist Marxist Party (Aravindakshan)',       'LDF', '#6A1B9A'),
    ('LJD',    'Loktantrik Janata Dal',                        'LDF', '#5C6BC0'),
    # UDF
    ('INC',    'Indian National Congress',                     'UDF', '#19AAED'),
    ('IUML',   'Indian Union Muslim League',                   'UDF', '#0F8A3C'),
    ('KEC',    'Kerala Congress (P.J. Joseph)',                'UDF', '#1E90FF'),
    ('RSP',    'Revolutionary Socialist Party',                'UDF', '#FF6347'),
    ('RSP_BJ', 'Revolutionary Socialist Party (Baby John)',     'UDF', '#FF6347'),
    ('KC_J',   'Kerala Congress (Jacob)',                      'UDF', '#5F9EA0'),
    ('CMP',    'Communist Marxist Party',                      'UDF', '#6495ED'),
    ('RMPI',   'Revolutionary Marxist Party of India',         'UDF', '#DC143C'),
    ('SJD',    'Socialist Janata (Democratic) Party',          'UDF', '#424242'),
    ('JSS',    'Janathipathiya Samrakshana Samithy',           'UDF', '#8D6E63'),
    ('NCK',    'Nationalist Congress Kerala',                  'UDF', '#4682B4'),
    ('KDP',    'Kerala Democratic Party',                      'UDF', '#4682B4'),
    ('AITC',   'All India Trinamool Congress',                 'UDF', '#1B8A00'),
    ('AIFB',   'All India Forward Bloc',                       'UDF', '#CC0000'),
    # NDA
    ('BJP',    'Bharatiya Janata Party',                       'NDA', '#FF9933'),
    ('BDJS',   'Bharath Dharma Jana Sena',                     'NDA', '#FFD700'),
    ('KC_T',   'Kerala Congress (Thomas)',                     'NDA', '#CD853F'),
    ('JRS',    'Janadhipathya Rashtriya Sabha',                'NDA', '#37474F'),
    ('AIADMK', 'All India Anna Dravida Munnetra Kazhagam',    'NDA', '#D4AC0D'),
    ('KKC',    'Kerala Kamaraj Congress',                      'NDA', '#CD853F'),
    ('TTP',    'Twenty20 Party',                               'NDA', '#FF4500'),
    ('JD_U',   'Janata Dal (United)',                          'NDA', '#1A6B1A'),
    ('JSS_T',  'Janathipathiya Samrakshana Samithy (Thamarakshan)', 'NDA', '#8D6E63'),
    # OTH
    ('IND',    'Independent',                                  'OTH', '#6B7280'),
    ('NOTA',   'None of the Above',                            'OTH', '#9CA3AF'),
    ('SDPI',   'Social Democratic Party of India',             'OTH', '#1B5E20'),
    ('AAP',    'Aam Aadmi Party',                              'OTH', '#0066CC'),
    ('BSP',    'Bahujan Samaj Party',                          'OTH', '#1565C0'),
    ('SUCI',   'Socialist Unity Centre of India',              'OTH', '#B71C1C'),
    ('SHS',    'Shiv Sena',                                    'OTH', '#F57F17'),
    ('PDP',    'Peoples Democratic Party',                      'OTH', '#795548'),
    ('WPOI',   'Welfare Party of India',                       'OTH', '#4A148C'),
    ('SP',     'Samajwadi Party',                              'OTH', '#E53935'),
    ('MCPI',   'Marxist Communist Party of India',             'OTH', '#880E4F'),
    ('CPI_ML_L','CPI(ML) Liberation',                          'OTH', '#CC0000'),
    ('CPI_ML_RS','CPI(ML) Red Star',                           'OTH', '#D50000'),
    ('DSJP',   'Democratic Social Justice Party',              'OTH', '#1B5E20'),
    ('ADHRMPI','ADHRMPI',                                      'OTH', '#558B2F'),
    ('BHUDRP', 'BHUDRP',                                       'OTH', '#827717'),
    ('RPI_A',  'Republican Party of India (Athawale)',          'OTH', '#0288D1'),
    ('KLJP',   'KLJP',                                         'OTH', '#1A237E'),
    ('KCS',    'Kerala Congress Secular',                       'OTH', '#8B6508'),
    ('DPSP',   'DPSP',                                         'OTH', '#37474F'),
    ('KJ',     'KJ',                                           'OTH', '#37474F'),
    ('SLAP',   'SLAP',                                         'OTH', '#37474F'),
    ('LJP',    'LJP',                                          'OTH', '#37474F'),
    ('SWJP',   'SWJP',                                         'OTH', '#37474F'),
    ('AKTP',   'AKTP',                                         'OTH', '#37474F'),
    ('SDP',    'SDP',                                           'OTH', '#37474F'),
    ('APOI',   'APOI',                                          'OTH', '#37474F'),
    ('IGP',    'Indian Gandhiyan Party',                        'OTH', '#37474F'),
    ('PPGP',   'PPGP',                                          'OTH', '#37474F'),
    ('ABHM',   'ABHM',                                          'OTH', '#4527A0'),
    ('DHRMP',  'DHRMP',                                         'OTH', '#37474F'),
    ('ICSP',   'ICSP',                                          'OTH', '#37474F'),
    ('KJPS',   'KJPS',                                          'OTH', '#37474F'),
    ('NALAP',  'NALAP',                                         'OTH', '#37474F'),
    ('NWLBRP', 'NWLBRP',                                        'OTH', '#37474F'),
    ('SDC',    'SDC',                                            'OTH', '#37474F'),
    ('SMFB',   'SMFB',                                           'OTH', '#37474F'),
    ('SWARAJ', 'SWARAJ',                                         'OTH', '#37474F'),
    ('KJP_S',  'Kerala Janapaksham (Secular)',                   'OTH', '#37474F'),
]

# ECI CSV code -> canonical code. Year-specific where needed.
ALIASES = [
    # 2011 ECI codes
    ('CPM',      'CPI_M',  2011),
    ('MUL',      'IUML',   2011),
    ('JPSS',     'JSS',    2011),
    ('KEC(M)',   'KC_M',   2011),
    ('CMPKSC',   'CMP',    2011),
    ('KEC(J)',   'KC_J',   2011),
    ('KEC(B)',   'KC_B',   2011),
    ('KRSP',     'RSP_BJ', 2011),
    ('KC(AMG)',  'KC_AMG', 2011),
    ('CPI(ML)(L)','CPI_ML_L',2011),
    # 2016 ECI codes
    ('CPM',      'CPI_M',  2016),
    ('KEC(M)',   'KC_M',   2016),
    ('CMPKSC',   'CMP',    2016),
    ('KEC(J)',   'KC_J',   2016),
    ('KEC(B)',   'KC_B',   2016),
    ('C(S)',     'CON_S',  2016),
    ('KCST',     'KC_KST', 2016),
    ('CPI(ML)(L)','CPI_ML_L',2016),
    # 2021 ECI codes
    ('CPI(M)',   'CPI_M',  2021),
    ('KEC(M)',   'KC_M',   2021),
    ('CMPKSC',   'CMP',    2021),
    ('KEC(J)',   'KC_J',   2021),
    ('KEC(B)',   'KC_B',   2021),
    ('C(S)',     'CON_S',  2021),
    ('RMPOI',    'RMPI',   2021),
    ('ADMK',     'AIADMK', 2021),
    # Universal aliases (all years)
    ('CPI(M)',   'CPI_M',  None),
    ('CPIM',     'CPI_ML_RS',  None),
    ('KC(M)',    'KC_M',   None),
    ('KC(B)',    'KC_B',   None),
    ('KC(J)',    'KC_J',   None),
    ('CON(S)',   'CON_S',  None),
    ('CONG(S)',  'CON_S',  None),
    ('RSP(L)',   'RSP_L',  None),
    ('KC(T)',    'KC_T',   None),
    ('NCP(SP)',  'NCP',    None),
    ('JD(S)-LDF','JD_S',   None),
    ('SP (I)',   'SP',     None),
    ('IND-LDF',  'IND',   None),
    ('IND-UDF',  'IND',   None),
    ('IND-NDA',  'IND',   None),
    ('IND (CPI(M))','IND', None),
    ('IND (CPI)','IND',    None),
    ('IND (INL)','IND',    None),
    # ECI codes present in 2006/2011/2021 CSVs
    ('MUL',      'IUML',   None),
    ('JD(S)',    'JD_S',   None),
    ('JD(U)',    'JD_U',   None),
    ('KEC(M)',   'KC_M',   None),
    ('KEC(B)',   'KC_B',   None),
    ('KEC(J)',   'KC_J',   None),
    ('JPSS',     'JSS',    None),
    ('C(S)',     'CON_S',  None),
    ('CMPKSC',   'CMP',    None),
    ('ADMK',     'AIADMK', None),
    ('RSPK(B)',  'RSP_BJ', None),
    ('RPI(A)',   'RPI_A',  None),
    ('KRSP',     'RSP_BJ', None),
    ('KC(AMG)',  'KC_AMG', None),
    ('CPI(ML)(L)','CPI_ML_L', None),
]

# year -> alliance -> [(party_code, color)]
ALLIANCE_YEARS = {
    2011: {
        'UDF': [('INC','#19AAED'),('IUML','#0F8A3C'),('KC_M','#8B4513'),('SJD','#424242'),
                ('JSS','#8D6E63'),('RSP','#FF6347'),('KC_J','#5F9EA0'),('CMP','#6495ED'),
                ('KC_B','#A0522D'),('RSP_BJ','#FF6347')],
        'LDF': [('CPI_M','#ED1E26'),('CPI','#FF4444'),('JD_S','#006400'),('NCP','#00BFFF'),
                ('INL','#2E8B57'),('KC_AMG','#8B6914')],
        'NDA': [('BJP','#FF9933'),('JD_U','#1A6B1A')],
    },
    2016: {
        'UDF': [('INC','#19AAED'),('IUML','#0F8A3C'),('KC_M','#8B4513'),('JD_U','#1A6B1A'),
                ('RSP','#FF6347'),('CMP','#6495ED'),('KC_J','#5F9EA0')],
        'LDF': [('CPI_M','#ED1E26'),('CPI','#FF4444'),('JD_S','#006400'),('NCP','#00BFFF'),
                ('INL','#2E8B57'),('NSC','#2E7D32'),('CON_S','#87CEEB'),('KC_KST','#8B6508'),
                ('KC_B','#A0522D'),('JKC','#B8860B'),('JSS','#8D6E63'),('CMA','#6A1B9A'),
                ('RSP_L','#B22222')],
        'NDA': [('BJP','#FF9933'),('BDJS','#FFD700'),('KC_T','#CD853F'),('JRS','#37474F')],
    },
    2021: {
        'UDF': [('INC','#19AAED'),('IUML','#0F8A3C'),('KEC','#1E90FF'),('RSP','#FF6347'),
                ('KC_J','#5F9EA0'),('CMP','#6495ED'),('RMPI','#DC143C'),('NCK','#4682B4')],
        'LDF': [('CPI_M','#ED1E26'),('CPI','#FF4444'),('KC_M','#8B4513'),('JD_S','#006400'),
                ('NCP','#00BFFF'),('INL','#2E8B57'),('RJD','#336699'),('LJD','#5C6BC0'),
                ('CON_S','#87CEEB'),('KC_B','#A0522D'),('JKC','#B8860B')],
        'NDA': [('BJP','#FF9933'),('BDJS','#FFD700'),('AIADMK','#D4AC0D'),('KKC','#CD853F')],
    },
    2026: {
        'UDF': [('INC','#19AAED'),('IUML','#0F8A3C'),('KEC','#1E90FF'),('RSP','#FF6347'),
                ('KC_J','#5F9EA0'),('CMP','#6495ED'),('RMPI','#DC143C'),('KDP','#4682B4'),
                ('AITC','#1B8A00'),('AIFB','#CC0000'),('JSS','#8D6E63'),('JRS','#37474F')],
        'LDF': [('CPI_M','#ED1E26'),('CPI','#FF4444'),('KC_M','#8B4513'),('ISJD','#006400'),
                ('NCP','#00BFFF'),('INL','#2E8B57'),('RJD','#336699'),('CON_S','#87CEEB'),
                ('KC_B','#A0522D'),('JKC','#B8860B')],
        'NDA': [('BJP','#FF9933'),('BDJS','#FFD700'),('AIADMK','#D4AC0D'),('KKC','#CD853F'),
                ('TTP','#FF4500'),('JSS_T','#8D6E63')],
    },
}

# Also seed OTH parties into PartyAllianceYear for each year they appear in CSVs
OTH_PARTIES_BY_YEAR = {
    2011: ['AIADMK','BSP','CPI_ML_L','DPSP','KJ','LJP','PDP','SDPI','SHS','SLAP','SUCI','SWJP'],
    2016: ['AIADMK','AKTP','BSP','CPI_ML_L','CPI_ML_RS','KCS','KEC','KLJP','MCPI','PDP','SDP',
           'SDPI','SHS','SP','SUCI','WPOI','APOI','IGP','PPGP'],
    2021: ['ABHM','ADHRMPI','BHUDRP','BSP','CPI_ML_RS','DHRMP','DSJP','ICSP','JD_U','KJPS',
           'KLJP','MCPI','NALAP','NSC','NWLBRP','RPI_A','SDC','SDPI','SHS','SMFB',
           'SUCI','SWARAJ','SWJP','WPOI'],
}


class Command(BaseCommand):
    help = 'Seed alliances, parties, aliases, alliance-year mappings, districts, constituencies'

    def add_arguments(self, parser):
        parser.add_argument('--data-dir', type=str, default='../data/')

    def handle(self, *args, **options):
        data_dir = options['data_dir']

        # 1. Alliances
        self.stdout.write("Creating alliances...")
        alliance_objs = {}
        for code, name, color in ALLIANCES:
            obj, _ = Alliance.objects.update_or_create(code=code, defaults={'full_name': name, 'color_code': color})
            alliance_objs[code] = obj
        self.stdout.write(self.style.SUCCESS(f"  {len(alliance_objs)} alliances"))

        # 2. Parties
        self.stdout.write("Creating parties...")
        party_objs = {}
        for code, name, al, color in PARTIES:
            obj, _ = Party.objects.update_or_create(
                code=code,
                defaults={'full_name': name, 'alliance': alliance_objs[al], 'color_code': color}
            )
            party_objs[code] = obj
        self.stdout.write(self.style.SUCCESS(f"  {len(party_objs)} parties"))

        # 3. Party Aliases
        self.stdout.write("Creating party aliases...")
        count = 0
        for alias, canonical, year in ALIASES:
            if canonical not in party_objs:
                self.stdout.write(self.style.WARNING(f"  SKIP alias {alias}->{canonical}: party not found"))
                continue
            PartyAlias.objects.update_or_create(
                alias_code=alias, election_year=year,
                defaults={'party': party_objs[canonical]}
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"  {count} aliases"))

        # 4. PartyAllianceYear
        self.stdout.write("Creating party-alliance-year mappings...")
        count = 0
        for year, alliances in ALLIANCE_YEARS.items():
            for al_code, parties in alliances.items():
                for pcode, color in parties:
                    if pcode not in party_objs:
                        self.stdout.write(self.style.WARNING(f"  SKIP {pcode} for {year}: not found"))
                        continue
                    PartyAllianceYear.objects.update_or_create(
                        party=party_objs[pcode], election_year=year, election_type='LA',
                        defaults={'alliance': alliance_objs[al_code], 'color_code': color}
                    )
                    count += 1
        # OTH parties
        for year, codes in OTH_PARTIES_BY_YEAR.items():
            for pcode in codes:
                if pcode not in party_objs:
                    continue
                PartyAllianceYear.objects.update_or_create(
                    party=party_objs[pcode], election_year=year, election_type='LA',
                    defaults={'alliance': alliance_objs['OTH'], 'color_code': party_objs[pcode].color_code}
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f"  {count} party-alliance-year entries"))

        # 5. Districts
        self.stdout.write("Creating districts...")
        for name, order in DISTRICT_ORDER.items():
            District.objects.update_or_create(name=name, defaults={'order': order})
        self.stdout.write(self.style.SUCCESS(f"  {District.objects.count()} districts"))

        # 6. Constituencies — from hardcoded static data
        self.stdout.write("Creating constituencies...")
        # Build parliament constituency map from 2024 CSV
        parliament_map = {}  # AC name (uppercase) -> PC name
        try:
            with open(f"{data_dir}/2024_Parliment.csv", 'r', encoding='utf-8-sig') as f:
                for row in csv.DictReader(f):
                    ac_name = row['State assembly constituency'].strip().upper()
                    pc_name = row['Constituency'].strip()
                    parliament_map[ac_name] = pc_name
        except FileNotFoundError:
            self.stdout.write(self.style.WARNING("2024_Parliment.csv not found, skipping PC mapping"))

        created = 0
        for number, name, district_name, reserved in CONSTITUENCY_DATA:
            district = District.objects.get(name=district_name)
            pc = parliament_map.get(name.upper(), '')
            _, was_created = Constituency.objects.update_or_create(
                number=number,
                defaults={
                    'name': name,
                    'district': district,
                    'reserved_category': reserved,
                    'parliament_constituency': pc,
                }
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"  {Constituency.objects.count()} constituencies ({created} new)"))

        self.stdout.write(self.style.SUCCESS(
            f"\nSEED COMPLETE: {Alliance.objects.count()} alliances, "
            f"{Party.objects.count()} parties, {PartyAlias.objects.count()} aliases, "
            f"{PartyAllianceYear.objects.count()} alliance-year entries, "
            f"{Constituency.objects.count()} constituencies"
        ))
