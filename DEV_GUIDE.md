# Kerala Election 2026 - Development Guide

## Table of Contents
1. [Initial Setup](#initial-setup)
2. [Data Import Guide](#data-import-guide)
3. [Development Workflow](#development-workflow)
4. [May 4 Live Day Workflow](#may-4-live-day-workflow)
5. [Deployment Guide](#deployment-guide)
6. [Common Tasks](#common-tasks)

---

## Initial Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Firebase CLI (for deployment)

### 1. Clone and Setup Backend

```bash
# Navigate to backend
cd kerala-election-2026/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create PostgreSQL database
createdb kerala_election_2026

# Create .env file
cat > .env << EOF
DB_NAME=kerala_election_2026
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
EOF

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
# Username: admin
# Email: your_email@example.com
# Password: (secure password)
```

### 2. Setup Frontend

```bash
# Navigate to frontend
cd ../frontend

# Install dependencies
npm install

# Create data directory for exports
mkdir -p src/data/results
```

---

## Data Import Guide

### Step 1: Populate Districts

```bash
cd backend
python manage.py shell
```

```python
from core.models import District

districts = [
    ('Kasaragod', 1),
    ('Kannur', 2),
    ('Wayanad', 3),
    ('Kozhikode', 4),
    ('Malappuram', 5),
    ('Palakkad', 6),
    ('Thrissur', 7),
    ('Ernakulam', 8),
    ('Idukki', 9),
    ('Kottayam', 10),
    ('Alappuzha', 11),
    ('Pathanamthitta', 12),
    ('Kollam', 13),
    ('Thiruvananthapuram', 14),
]

for name, order in districts:
    District.objects.get_or_create(name=name, defaults={'order': order})
    print(f"Created: {name}")

exit()
```

### Step 2: Import Constituencies

You'll need to create a constituencies CSV or use Django shell. Sample for first 5:

```python
from core.models import District, Constituency

constituencies_data = [
    # (number, name, district_name, reserved, parliament_constituency)
    (1, 'Manjeshwar', 'Kasaragod', 'GEN', 'Kasaragod'),
    (2, 'Kasaragod', 'Kasaragod', 'GEN', 'Kasaragod'),
    (3, 'Udma', 'Kasaragod', 'GEN', 'Kasaragod'),
    (4, 'Kanhangad', 'Kasaragod', 'GEN', 'Kasaragod'),
    (5, 'Trikaripur', 'Kasaragod', 'GEN', 'Kasaragod'),
    # ... add all 140
]

for number, name, district_name, reserved, parliament in constituencies_data:
    district = District.objects.get(name=district_name)
    Constituency.objects.get_or_create(
        number=number,
        defaults={
            'name': name,
            'district': district,
            'reserved_category': reserved,
            'parliament_constituency': parliament
        }
    )
    print(f"Created: {number}. {name}")
```

**Note:** You'll need the complete list of 140 constituencies. This can be scraped from ECI website or Kerala government sources.

### Step 3: Import Historical Data

```bash
# 2021 LA results (complete candidate data)
python manage.py import_2021_results ../data/election_candidates.csv

# 2019 Parliament results
python manage.py import_parliament_results 2019 ../data/2019_Parliment.csv

# 2024 Parliament results
python manage.py import_parliament_results 2024 ../data/2024_Parliment.csv
```

### Step 4: Populate Parties

```python
from core.models import Party

parties = [
    # UDF Parties
    ('INC', 'Indian National Congress', 'UDF', '#19AAED'),
    ('IUML', 'Indian Union Muslim League', 'UDF', '#00A650'),
    ('KC(M)', 'Kerala Congress (M)', 'UDF', '#FFA500'),
    ('KC(J)', 'Kerala Congress (Joseph)', 'UDF', '#FFD700'),
    ('RSP', 'Revolutionary Socialist Party', 'UDF', '#FF69B4'),
    
    # LDF Parties
    ('CPI(M)', 'Communist Party of India (Marxist)', 'LDF', '#ED1E26'),
    ('CPI', 'Communist Party of India', 'LDF', '#FF0000'),
    ('JD(S)', 'Janata Dal (Secular)', 'LDF', '#138808'),
    ('NCP', 'Nationalist Congress Party', 'LDF', '#00B2B2'),
    
    # NDA Parties
    ('BJP', 'Bharatiya Janata Party', 'NDA', '#FF9933'),
    ('BDJS', 'Bharath Dharma Jana Sena', 'NDA', '#FF6B6B'),
    
    # Others
    ('SDPI', 'Social Democratic Party of India', 'OTH', '#006400'),
    ('AAP', 'Aam Aadmi Party', 'OTH', '#0066CC'),
    ('IND', 'Independent', 'OTH', '#808080'),
]

for code, name, alliance, color in parties:
    party, created = Party.objects.get_or_create(
        code=code,
        defaults={
            'full_name': name,
            'alliance': alliance,
            'color_code': color
        }
    )
    print(f"{'Created' if created else 'Updated'}: {code}")
```

---

## Development Workflow

### Starting Development Servers

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
python manage.py runserver
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Access:
- Frontend: http://localhost:3000
- Django Admin: http://localhost:8000/admin/
- API: http://localhost:8000/api/

### Hot Reload
- Frontend: Auto-reloads on file changes
- Backend: Auto-reloads on Python file changes

---

## May 4 Live Day Workflow

### Option 1: Django Admin Entry

1. **Login to Django Admin**
   ```
   http://localhost:8000/admin/
   ```

2. **Update Candidate Votes**
   - Navigate to **Candidates**
   - Filter by constituency
   - Update vote counts from TV channels
   - Mark leader: `is_leading = True`
   - Mark winner when final: `is_winner = True`

3. **Update Live Result Status**
   - Navigate to **Live Results**
   - Select constituency
   - Update:
     - Status (IN_PROGRESS → COMPLETED → RESULT_DECLARED)
     - Votes counted
     - Valid votes
     - Rounds completed

4. **Export JSON**
   ```bash
   cd backend
   python manage.py export_json --output ../frontend/src/data/
   ```

5. **Build & Deploy**
   ```bash
   cd ../frontend
   npm run build
   firebase deploy --only hosting
   ```

**Timeline:**
- Update every 15-30 minutes
- Export → Build → Deploy takes ~2-3 minutes

### Option 2: React Admin Panel (Future)

- Protected route: `/admin`
- Password: `admin2026`
- Quick entry forms
- Auto-export on save
- Real-time preview

---

## Deployment Guide

### First-Time Firebase Setup

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login to Firebase
firebase login

# Initialize project
firebase init hosting

# Select:
# - Create new project or use existing
# - Public directory: frontend/dist
# - Single-page app: Yes
# - GitHub deploys: No
```

### Deployment Process

```bash
# 1. Export latest data
cd backend
python manage.py export_json --output ../frontend/src/data/

# 2. Build frontend
cd ../frontend
npm run build

# 3. Deploy to Firebase
firebase deploy --only hosting

# 4. Verify deployment
# Visit: https://your-project.web.app
```

### Quick Redeploy (Data Update Only)

```bash
# From project root
cd backend && python manage.py export_json --output ../frontend/src/data/
cd ../frontend && npm run build && firebase deploy --only hosting
```

---

## Common Tasks

### Add New Candidates for 2026

```python
from core.models import Constituency, Party, Candidate

# Get constituency
constituency = Constituency.objects.get(number=1)  # Manjeshwar

# Get party
party = Party.objects.get(code='INC')

# Create candidate
candidate = Candidate.objects.create(
    name='Candidate Name',
    party=party,
    constituency=constituency,
    votes=0,
    vote_percentage=0.0,
    is_winner=False,
    is_leading=False
)
```

### Update Vote Counts

```python
from core.models import Candidate

# Update single candidate
candidate = Candidate.objects.get(id=1)
candidate.votes = 45000
candidate.vote_percentage = 52.5
candidate.is_leading = True
candidate.save()

# Bulk update for constituency
from core.models import Constituency
constituency = Constituency.objects.get(number=1)

votes_data = [
    ('Candidate A', 45000),
    ('Candidate B', 38000),
    ('Candidate C', 12000),
]

for name, votes in votes_data:
    candidate = constituency.candidates_2026.get(name=name)
    candidate.votes = votes
    candidate.save()
```

### Backup Database

```bash
# Backup
pg_dump -U postgres kerala_election_2026 > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore
psql -U postgres kerala_election_2026 < backup_20260504_120000.sql
```

### Clear All 2026 Results (Reset)

```python
from core.models import Candidate, LiveResult

# Clear votes
Candidate.objects.all().update(
    votes=0,
    vote_percentage=0.0,
    is_winner=False,
    is_leading=False
)

# Reset live results
LiveResult.objects.all().update(
    status='NOT_STARTED',
    votes_counted=0,
    valid_votes=0,
    rounds_completed=0
)
```

### Check Data Import Status

```bash
python manage.py shell
```

```python
from core.models import *

print(f"Districts: {District.objects.count()}")
print(f"Constituencies: {Constituency.objects.count()}")
print(f"Parties: {Party.objects.count()}")
print(f"2021 Results: {HistoricalResult2021.objects.count()}")
print(f"2019 LS Results: {ParliamentResult.objects.filter(year=2019).count()}")
print(f"2024 LS Results: {ParliamentResult.objects.filter(year=2024).count()}")
print(f"2026 Candidates: {Candidate.objects.count()}")
```

Expected output:
```
Districts: 14
Constituencies: 140
Parties: ~15-20
2021 Results: ~900 (all candidates)
2019 LS Results: 140
2024 LS Results: 140
2026 Candidates: 0 (add these manually before May 4)
```

---

## Performance Optimization

### Database Indexes

Already included in models:
- Constituency number (unique)
- Party code (unique)
- Candidate constituency + party (unique together)

### Frontend Bundle Size

```bash
# Analyze bundle
cd frontend
npm run build
npx vite-bundle-visualizer
```

Target: < 300KB gzipped

### JSON File Optimization

Current structure is optimized:
- Small initial load (~55KB)
- Lazy-loaded constituency details
- Efficient caching with Firebase CDN

---

## Troubleshooting

### Backend Issues

**Issue:** `relation "core_constituency" does not exist`
```bash
python manage.py migrate
```

**Issue:** Import fails with "Constituency not found"
```bash
# Check constituency count
python manage.py shell
>>> from core.models import Constituency
>>> print(Constituency.objects.count())
```

### Frontend Issues

**Issue:** API returns 404
```bash
# Check Django server is running
curl http://localhost:8000/api/summary/
```

**Issue:** Empty data in production
```bash
# Re-export JSON
cd backend
python manage.py export_json --output ../frontend/src/data/
```

---

## Next Phase: To Be Built

1. **Complete Constituency List** - Need all 140 with district mapping
2. **React Admin Panel** - Live entry interface
3. **Auto-refresh** - Poll for updates every 30s
4. **Charts** - Vote share pie charts, trend lines
5. **District View** - Aggregate by district
6. **Mobile Optimization** - Touch-friendly UI
7. **PWA Support** - Offline capability
8. **Notifications** - Result alerts

---

## Support & Questions

For issues or questions during development, check:
1. Backend SETUP.md for detailed Django setup
2. README.md for project overview
3. This guide for workflows

Project maintained by Dasharath for Techno Bharat Mission.
