import csv

# For 2016, find constituencies where NO LDF party candidate exists
ldf_parties_2016 = {'CPM','CPI','JD(S)','NCP','INL','KEC(B)','C(S)','NSC','KCST','KCS'}
nda_parties_2016 = {'BJP','BDJS'}
udf_parties_2016 = {'INC','IUML','KEC(M)','JD(U)','RSP','CMPKSC','KEC(J)'}

# Non-alliance noise parties to filter out
noise = {'NOTA','BSP','SDPI','PDP','SUCI','SHS','WPOI','SP','ADMK','CPIM',
         'CPI(ML)(L)','AKTP','APOI','IGP','PPGP','SDP','MCPI','KLJP','KEC'}

f = open('../2016_candinates.csv', 'r', encoding='utf-8-sig')
r = csv.DictReader(f)
const_parties = {}
const_names = {}
const_candidates = {}  # (const, party) -> candidate name

for row in r:
    p = row[' Party Name'].strip()
    c = int(row['Constituency No.'].strip())
    n = row['Constituency Name'].strip()
    cand = row['Candidate Name'].strip()
    const_names[c] = n
    if c not in const_parties:
        const_parties[c] = set()
    const_parties[c].add(p)
    const_candidates[(c, p)] = cand
f.close()

all_alliance = ldf_parties_2016 | nda_parties_2016 | udf_parties_2016

print('=== 2016: Constituencies with NO recognized LDF party ===')
missing_ldf = []
for c in sorted(const_parties.keys()):
    parties = const_parties[c]
    has_ldf = bool(parties & ldf_parties_2016)
    if not has_ldf:
        has_ind = 'IND' in parties
        # Show non-noise, non-alliance parties present
        interesting = parties - noise - all_alliance - {'IND'}
        ind_note = "IND" if has_ind else "---"
        print(f"  #{c:3d} {const_names[c]:25s} [{ind_note}]  other: {interesting if interesting else '{}'}")
        missing_ldf.append(c)
print(f"Total: {len(missing_ldf)}")

print()
print('=== 2016: Constituencies with NO recognized NDA party ===')
missing_nda = []
for c in sorted(const_parties.keys()):
    parties = const_parties[c]
    has_nda = bool(parties & nda_parties_2016)
    if not has_nda:
        interesting = parties - noise - all_alliance - {'IND'}
        ind_note = "IND" if 'IND' in parties else "---"
        print(f"  #{c:3d} {const_names[c]:25s} [{ind_note}]  other: {interesting if interesting else '{}'}")
        missing_nda.append(c)
print(f"Total: {len(missing_nda)}")

print()
print('=== 2016: Constituencies with NO recognized UDF party ===')
missing_udf = []
for c in sorted(const_parties.keys()):
    parties = const_parties[c]
    has_udf = bool(parties & udf_parties_2016)
    if not has_udf:
        interesting = parties - noise - all_alliance - {'IND'}
        ind_note = "IND" if 'IND' in parties else "---"
        print(f"  #{c:3d} {const_names[c]:25s} [{ind_note}]  other: {interesting if interesting else '{}'}")
        missing_udf.append(c)
print(f"Total: {len(missing_udf)}")

# Now for 2011
print()
print('=' * 60)
ldf_2011 = {'CPM','CPI','JD(S)','NCP','INL','KC(AMG)'}
udf_2011 = {'INC','MUL','KEC(M)','SJD','JPSS','RSP','CMPKSC','KEC(J)','KEC(B)','KRSP'}
nda_2011 = {'BJP','JD(U)'}

f = open('../2011_candidates.csv', 'r', encoding='utf-8-sig')
r = csv.DictReader(f)
const_parties_2011 = {}
const_names_2011 = {}
for row in r:
    p = row['party'].strip()
    c = int(row['constituency_no'].strip())
    n = row['constituency_name'].strip()
    const_names_2011[c] = n
    if c not in const_parties_2011:
        const_parties_2011[c] = set()
    const_parties_2011[c].add(p)
f.close()

noise_2011 = {'BSP','SDPI','PDP','SUCI','SHS','AIADMK','LJP','DPSP','KJ','SLAP','SWJP','CPI(ML)(L)'}

print('=== 2011: Constituencies with NO recognized LDF party ===')
for c in sorted(const_parties_2011.keys()):
    parties = const_parties_2011[c]
    if not (parties & ldf_2011):
        interesting = parties - noise_2011 - ldf_2011 - udf_2011 - nda_2011 - {'IND'}
        ind_note = "IND" if 'IND' in parties else "---"
        print(f"  #{c:3d} {const_names_2011[c]:25s} [{ind_note}]  other: {interesting if interesting else '{}'}")

print()
print('=== 2011: Constituencies with NO recognized UDF party ===')
for c in sorted(const_parties_2011.keys()):
    parties = const_parties_2011[c]
    if not (parties & udf_2011):
        interesting = parties - noise_2011 - ldf_2011 - udf_2011 - nda_2011 - {'IND'}
        ind_note = "IND" if 'IND' in parties else "---"
        print(f"  #{c:3d} {const_names_2011[c]:25s} [{ind_note}]  other: {interesting if interesting else '{}'}")

# 2021
print()
print('=' * 60)
ldf_2021 = {'CPI(M)','CPI','KEC(M)','JD(S)','NCP','RJD','INL','C(S)','KEC(B)','JKC'}
udf_2021 = {'INC','IUML','KEC','RSP','KEC(J)','CMPKSC','RMPOI'}
nda_2021 = {'BJP','BDJS','ADMK'}

f = open('../2021_candinates.csv', 'r', encoding='utf-8-sig')
r = csv.DictReader(f)
const_parties_2021 = {}
const_names_2021 = {}
for row in r:
    p = row['party'].strip()
    c = int(row['constituency_no'].strip())
    n = row['constituency_name'].strip()
    const_names_2021[c] = n
    if c not in const_parties_2021:
        const_parties_2021[c] = set()
    const_parties_2021[c].add(p)
f.close()

noise_2021 = {'NOTA','BSP','SDPI','SUCI','SHS','WPOI','ABHM','ADHRMPI','BHUDRP','CPIM',
              'DHRMP','DSJP','ICSP','JD(U)','KJPS','KLJP','LJD','MCPI','NALAP','NSC',
              'NWLBRP','RPI(A)','SDC','SMFB','SWARAJ','SWJP'}

print('=== 2021: Constituencies with NO recognized LDF party ===')
for c in sorted(const_parties_2021.keys()):
    parties = const_parties_2021[c]
    if not (parties & ldf_2021):
        interesting = parties - noise_2021 - ldf_2021 - udf_2021 - nda_2021 - {'IND'}
        ind_note = "IND" if 'IND' in parties else "---"
        print(f"  #{c:3d} {const_names_2021[c]:25s} [{ind_note}]  other: {interesting if interesting else '{}'}")

print()
print('=== 2021: Constituencies with NO recognized UDF party ===')
for c in sorted(const_parties_2021.keys()):
    parties = const_parties_2021[c]
    if not (parties & udf_2021):
        interesting = parties - noise_2021 - ldf_2021 - udf_2021 - nda_2021 - {'IND'}
        ind_note = "IND" if 'IND' in parties else "---"
        print(f"  #{c:3d} {const_names_2021[c]:25s} [{ind_note}]  other: {interesting if interesting else '{}'}")

print()
print('=== 2021: Constituencies with NO recognized NDA party ===')
for c in sorted(const_parties_2021.keys()):
    parties = const_parties_2021[c]
    if not (parties & nda_2021):
        interesting = parties - noise_2021 - ldf_2021 - udf_2021 - nda_2021 - {'IND'}
        ind_note = "IND" if 'IND' in parties else "---"
        print(f"  #{c:3d} {const_names_2021[c]:25s} [{ind_note}]  other: {interesting if interesting else '{}'}")
