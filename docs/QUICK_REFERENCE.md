# Kerala Election 2026 - Quick Reference Card

## 🚀 Quick Start (First Time)

```bash
# 1. Extract project
tar -xzf kerala-election-2026.tar.gz
cd kerala-election-2026

# 2. Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Create database
createdb kerala_election_2026

# 4. Create .env file
cat > .env << 'EOF'
DB_NAME=kerala_election_2026
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
EOF

# 5. Run migrations and setup
python manage.py migrate
python manage.py createsuperuser
./setup.sh

# 6. Frontend setup
cd ../frontend
npm install

# 7. Start dev servers
# Terminal 1: cd backend && python manage.py runserver
# Terminal 2: cd frontend && npm run dev
```

---

## 📋 Daily Development Commands

### Backend (Django)

```bash
cd backend
source venv/bin/activate

# Start server
python manage.py runserver

# Access Django admin
open http://localhost:8000/admin/

# Database shell
python manage.py shell

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Import historical data
python manage.py import_2021_results ../data/election_candidates.csv
python manage.py import_parliament_results 2019 ../data/2019_Parliment.csv
python manage.py import_parliament_results 2024 ../data/2024_Parliment.csv

# Export to JSON (for production)
python manage.py export_json --output ../frontend/src/data/

# Backup database
pg_dump -U postgres kerala_election_2026 > backup_$(date +%Y%m%d).sql

# Restore database
psql -U postgres kerala_election_2026 < backup_20260504.sql
```

### Frontend (React)

```bash
cd frontend

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type checking
npm run lint

# Install new package
npm install package-name
```

---

## 🗃️ Common Database Tasks

### Check Data Status

```python
# python manage.py shell

from core.models import *

print(f"Districts: {District.objects.count()}")
print(f"Constituencies: {Constituency.objects.count()}")
print(f"Parties: {Party.objects.count()}")
print(f"2021 Results: {HistoricalResult2021.objects.count()}")
print(f"2019 LS: {ParliamentResult.objects.filter(year=2019).count()}")
print(f"2024 LS: {ParliamentResult.objects.filter(year=2024).count()}")
print(f"2026 Candidates: {Candidate.objects.count()}")
```

### Add 2026 Candidate

```python
from core.models import Constituency, Party, Candidate

constituency = Constituency.objects.get(number=1)
party = Party.objects.get(code='INC')

Candidate.objects.create(
    name='Candidate Name',
    party=party,
    constituency=constituency,
    votes=0
)
```

### Update Live Votes

```python
from core.models import Candidate, LiveResult

# Update candidate
candidate = Candidate.objects.get(id=1)
candidate.votes = 45000
candidate.vote_percentage = 52.5
candidate.is_leading = True
candidate.save()

# Update status
result = LiveResult.objects.get(constituency_id=1)
result.status = 'IN_PROGRESS'
result.votes_counted = 85000
result.rounds_completed = 12
result.save()
```

---

## 📊 May 4, 2026 Live Day Workflow

### Option 1: Django Admin (Recommended)

```bash
# 1. Open Django admin
open http://localhost:8000/admin/

# 2. Update votes in Candidates section
# 3. Update status in Live Results section

# 4. Export JSON
cd backend
python manage.py export_json --output ../frontend/src/data/

# 5. Build & deploy
cd ../frontend
npm run build
firebase deploy --only hosting

# Repeat every 15-30 minutes
```

### Option 2: React Admin Panel (Future)

```bash
# Access protected admin panel
open http://localhost:3000/admin
# Password: admin2026

# Quick entry → Auto-export → Redeploy
```

---

## 🔥 Firebase Commands

```bash
# First time setup
npm install -g firebase-tools
firebase login
firebase init hosting

# Deploy
firebase deploy --only hosting

# View logs
firebase hosting:channel:list

# Rollback to previous version
firebase hosting:channel:deploy <channel-name>
```

---

## 🛠️ Troubleshooting

### Backend won't start

```bash
# Check PostgreSQL is running
pg_isready

# Check database exists
psql -l | grep kerala_election

# Reset migrations (WARNING: destroys data)
python manage.py migrate core zero
python manage.py migrate
```

### Frontend won't start

```bash
# Clear node modules
rm -rf node_modules package-lock.json
npm install

# Clear cache
rm -rf .vite
npm run dev
```

### Data not showing

```bash
# Check API response
curl http://localhost:8000/api/summary/

# Check JSON exists
ls -lh frontend/src/data/

# Re-export
cd backend
python manage.py export_json --output ../frontend/src/data/
```

---

## 📁 Important Paths

```
Backend:
  Models: backend/core/models.py
  Admin: backend/core/admin.py
  API: backend/core/api/views.py
  Commands: backend/core/management/commands/

Frontend:
  Pages: frontend/src/pages/
  Hooks: frontend/src/hooks/useElectionData.ts
  Types: frontend/src/types/index.ts
  Data: frontend/src/data/ (gitignored)

Data:
  CSV files: data/*.csv
  Backups: *.sql (create manually)

Docs:
  Overview: README.md
  Development: DEV_GUIDE.md
  Backend: backend/SETUP.md
  Structure: PROJECT_TREE.md
  Claude Code: CLAUDE_CODE_CONTEXT.md
```

---

## 🌐 URLs

```
Development:
  Frontend: http://localhost:3000
  Backend API: http://localhost:8000/api/
  Django Admin: http://localhost:8000/admin/

Production:
  Firebase: https://your-project.web.app
```

---

## 📊 API Endpoints

```
GET /api/summary/                           # State overview
GET /api/constituencies/                    # All 140 constituencies
GET /api/constituencies/{id}/               # Single constituency
GET /api/historical/{constituency_number}/  # Historical comparison
GET /api/parties/                           # All parties
GET /api/districts/                         # All districts
```

---

## 🎨 Alliance Colors

```css
UDF: #19AAED (Blue)
LDF: #ED1E26 (Red)
NDA: #FF9933 (Saffron/Orange)
OTH: #808080 (Gray)
```

---

## ✅ Pre-Launch Checklist

- [ ] All 140 constituencies imported
- [ ] All parties with correct colors
- [ ] 2021 LA data imported (check: ~900 records)
- [ ] 2019 LS data imported (check: 140 records)
- [ ] 2024 LS data imported (check: 140 records)
- [ ] 2026 candidates added
- [ ] Test live entry workflow
- [ ] Test export → build → deploy cycle
- [ ] Firebase project created
- [ ] Domain configured (optional)
- [ ] Backup strategy ready

---

## 🆘 Emergency Contacts

**Project:** Kerala Election 2026 Results Platform  
**Owner:** Dasharath (Techno Bharat Mission)  
**Stack:** Django + PostgreSQL + React + Firebase  
**Launch:** May 4, 2026

**Support Resources:**
- Django docs: https://docs.djangoproject.com/
- React docs: https://react.dev/
- Vite docs: https://vitejs.dev/
- Firebase docs: https://firebase.google.com/docs/hosting
