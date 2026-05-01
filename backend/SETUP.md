# Kerala Election 2026 - Backend Setup Guide

## Project Structure

```
backend/
├── manage.py
├── requirements.txt
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── __init__.py
└── core/
    ├── models.py
    ├── admin.py
    ├── api/
    │   ├── serializers.py
    │   └── views.py
    └── management/
        └── commands/
            ├── import_2021_results.py
            ├── import_parliament_results.py
            └── export_json.py
```

---

## Initial Setup

### 1. Install PostgreSQL

```bash
# macOS
brew install postgresql@16
brew services start postgresql@16

# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### 2. Create Database

```bash
# Login to PostgreSQL
psql postgres

# Create database and user
CREATE DATABASE kerala_election_2026;
CREATE USER election_user WITH PASSWORD 'your_password_here';
ALTER ROLE election_user SET client_encoding TO 'utf8';
ALTER ROLE election_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE election_user SET timezone TO 'Asia/Kolkata';
GRANT ALL PRIVILEGES ON DATABASE kerala_election_2026 TO election_user;
\q
```

### 3. Install Python Dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in `backend/` directory:

```env
DB_NAME=kerala_election_2026
DB_USER=election_user
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
```

### 5. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create Superuser (for Django Admin)

```bash
python manage.py createsuperuser
# Username: admin
# Email: your_email@example.com
# Password: (choose a strong password)
```

---

## Data Import Workflow

### Step 1: Populate Districts

Create this manually in Django admin or via Django shell:

```python
python manage.py shell

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

exit()
```

### Step 2: Import Constituencies

You'll need to create a constituencies.csv or import via Django shell. Here's a sample:

```python
python manage.py shell

from core.models import District, Constituency

# Sample - you'll need to complete this for all 140
constituencies = [
    (1, 'Manjeshwar', 'Kasaragod', 'GEN', 'Kasaragod'),
    (2, 'Kasaragod', 'Kasaragod', 'GEN', 'Kasaragod'),
    # ... add all 140
]

for number, name, district_name, reserved, parliament in constituencies:
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

exit()
```

### Step 3: Import Historical Data

```bash
# Import 2021 LA results (complete candidate data)
python manage.py import_2021_results /path/to/election_candidates.csv

# Import 2019 LS results
python manage.py import_parliament_results 2019 /path/to/2019_Parliment.csv

# Import 2024 LS results
python manage.py import_parliament_results 2024 /path/to/2024_Parliment.csv
```

### Step 4: Populate Parties

Create in Django admin or shell:

```python
from core.models import Party

parties = [
    ('INC', 'Indian National Congress', 'UDF', '#19AAED'),
    ('IUML', 'Indian Union Muslim League', 'UDF', '#00A650'),
    ('KC(M)', 'Kerala Congress (M)', 'UDF', '#FFA500'),
    ('CPI(M)', 'Communist Party of India (Marxist)', 'LDF', '#FF0000'),
    ('CPI', 'Communist Party of India', 'LDF', '#ED1E26'),
    ('BJP', 'Bharatiya Janata Party', 'NDA', '#FF9933'),
    # ... add all parties
]

for code, name, alliance, color in parties:
    Party.objects.get_or_create(
        code=code,
        defaults={'full_name': name, 'alliance': alliance, 'color_code': color}
    )
```

---

## Running the Development Server

```bash
# Start Django development server
python manage.py runserver

# Access at:
# - API: http://localhost:8000/api/
# - Admin: http://localhost:8000/admin/
```

---

## API Endpoints (Development Mode)

### State Summary
```
GET /api/summary/
```
Returns state-level aggregates: total seats, alliance breakdown, votes counted

### All Constituencies (List)
```
GET /api/constituencies/
```
Returns lightweight data for all 140 constituencies

### Single Constituency (Detail)
```
GET /api/constituencies/{id}/
```
Returns full data: candidates, live results, 2021 historical data

### Historical Comparison
```
GET /api/historical/{constituency_number}/
```
Returns 2021 LA + 2019/2024 LS comparison

### Parties
```
GET /api/parties/
```
Returns all parties with alliance and color data

### Districts
```
GET /api/districts/
```
Returns all districts

---

## Managing Live Results (May 4, 2026)

### Django Admin Workflow

1. Go to http://localhost:8000/admin/
2. Login with superuser credentials
3. Navigate to **Live Results** section
4. For each constituency:
   - Select constituency
   - Update status (NOT_STARTED → IN_PROGRESS → COMPLETED → RESULT_DECLARED)
   - Enter votes counted, valid votes, rounds completed
   - Click Save

5. Navigate to **Candidates** section
6. Update vote counts for each candidate
7. Mark leader with `is_leading = True`
8. When final: mark winner with `is_winner = True`

### Export to JSON (for Firebase)

After updating data in Django admin:

```bash
python manage.py export_json --output ../frontend/src/data/
```

This creates:
- `meta.json` - State summary
- `constituencies.json` - All constituencies list
- `results/{001-140}.json` - Individual constituency details
- `historical.json` - 2021 LA + 2019/2024 LS data
- `parties.json` - Party master data

---

## Firebase Deployment Workflow

### 1. Update Data in Django Admin
- Add/update live results
- Update candidate vote counts
- Mark leaders/winners

### 2. Export JSON
```bash
python manage.py export_json --output ../frontend/src/data/
```

### 3. Build React App
```bash
cd ../frontend
npm run build
```

### 4. Deploy to Firebase
```bash
firebase deploy --only hosting
```

---

## Database Backup & Restore

### Backup
```bash
pg_dump -U election_user kerala_election_2026 > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore
```bash
psql -U election_user kerala_election_2026 < backup_20260504_120000.sql
```

---

## Troubleshooting

### Issue: "relation does not exist"
**Solution:** Run migrations
```bash
python manage.py migrate
```

### Issue: "FATAL: password authentication failed"
**Solution:** Check .env file credentials match PostgreSQL user

### Issue: Import fails with "Constituency not found"
**Solution:** Ensure constituencies are imported before historical results

### Issue: API returns empty data
**Solution:** Check if data was actually imported via Django admin

---

## Next Steps

1. ✅ Backend setup complete
2. 🔄 **NOW:** Build React frontend
3. 📊 Create constituency master list (all 140 with district mapping)
4. 🎨 Design UI components
5. 🧪 Test with sample data
6. 🚀 Deploy to Firebase

---

## Notes

- **Development:** Django serves API + frontend connects via fetch
- **Production:** Firebase hosts static frontend with pre-exported JSON (no Django needed)
- **May 4, 2026:** You'll manually update Django admin → export JSON → redeploy Firebase every 15-30 minutes
