# Claude Code - Kerala Election 2026 Project Context

## Project Overview
Full-stack election results visualization platform for Kerala Legislative Assembly Elections 2026 (May 4, 2026). Built with Django + PostgreSQL backend and React + TypeScript frontend, designed for both live development (API-connected) and production deployment (static JSON on Firebase).

## Quick Start Commands

```bash
# Backend setup
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# Frontend setup
cd frontend
npm install
npm run dev
```

## Project Architecture

### Development Mode
- **Backend:** Django REST API @ localhost:8000
- **Database:** PostgreSQL (live data entry)
- **Frontend:** React + Vite @ localhost:3000 (connects to API)

### Production Mode (Firebase)
- **Frontend only:** Static React build
- **Data:** Pre-exported JSON files (no backend needed)
- **Updates:** Manual export → rebuild → deploy cycle

## File Structure Map

```
kerala-election-2026/
├── backend/
│   ├── core/
│   │   ├── models.py              # 9 models: District, Constituency, Party, Candidate, LiveResult, etc.
│   │   ├── admin.py               # Django admin config
│   │   ├── api/
│   │   │   ├── serializers.py     # DRF serializers
│   │   │   └── views.py           # API endpoints
│   │   └── management/commands/
│   │       ├── import_2021_results.py
│   │       ├── import_parliament_results.py
│   │       └── export_json.py     # KEY: Exports to frontend/src/data/
│   ├── config/
│   │   ├── settings.py
│   │   └── urls.py
│   ├── requirements.txt
│   ├── manage.py
│   └── SETUP.md                   # Detailed backend setup
│
├── frontend/
│   ├── src/
│   │   ├── types/index.ts         # TypeScript types (12 interfaces)
│   │   ├── hooks/
│   │   │   └── useElectionData.ts # Data fetching (dev=API, prod=JSON)
│   │   ├── pages/
│   │   │   ├── HomePage.tsx       # State summary + constituency list
│   │   │   ├── ConstituencyPage.tsx  # Detail view + historical comparison
│   │   │   └── AdminPanel.tsx     # Protected admin interface (WIP)
│   │   ├── App.tsx                # Router setup
│   │   ├── main.tsx
│   │   └── data/                  # JSON exports land here (gitignored)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js         # Alliance colors: UDF=#19AAED, LDF=#ED1E26, NDA=#FF9933
│   └── tsconfig.json
│
├── data/                          # Source CSV files
│   ├── election_candidates.csv    # 2021 LA results (all candidates)
│   ├── 2019_Parliment.csv
│   └── 2024_Parliment.csv
│
├── README.md                      # Project overview
├── DEV_GUIDE.md                   # This file - comprehensive dev guide
├── .gitignore
└── firebase.json
```

## Key Data Models

### Core (2026 Election)
- **Constituency**: 140 LA seats (number, name, district, reserved_category)
- **Party**: Political parties (code, full_name, alliance, color_code)
- **Candidate**: 2026 candidates (name, party, constituency, votes, is_winner, is_leading)
- **LiveResult**: Counting status (status, votes_counted, rounds_completed, last_updated)

### Historical
- **HistoricalResult2021**: Complete 2021 LA candidate data
- **ConstituencyMeta2021**: 2021 metadata (winner, margin)
- **ParliamentResult**: 2019/2024 LS results at AC segment level

## API Endpoints

```
GET /api/summary/                           # State summary
GET /api/constituencies/                    # All 140 constituencies
GET /api/constituencies/{id}/               # Single constituency detail
GET /api/historical/{constituency_number}/  # Historical comparison
GET /api/parties/                           # All parties
```

## Data Flow

### Import Historical Data
```bash
python manage.py import_2021_results data/election_candidates.csv
python manage.py import_parliament_results 2019 data/2019_Parliment.csv
python manage.py import_parliament_results 2024 data/2024_Parliment.csv
```

### Export for Production
```bash
python manage.py export_json --output ../frontend/src/data/
```

Creates:
- `meta.json` - State summary
- `constituencies.json` - All 140 constituencies
- `results/001-140.json` - Individual constituency details
- `historical.json` - 2021 LA + 2019/2024 LS comparison
- `parties.json` - Party master data

### Frontend Data Hook Logic
```typescript
// Auto-detects dev vs production
const USE_API = import.meta.env.DEV;

// Dev: fetch from Django API
// Prod: fetch from /data/*.json files
```

## Common Development Tasks

### Add 2026 Candidates
```python
from core.models import Constituency, Party, Candidate

constituency = Constituency.objects.get(number=1)
party = Party.objects.get(code='INC')

Candidate.objects.create(
    name='Candidate Name',
    party=party,
    constituency=constituency
)
```

### Update Live Results (May 4)
```python
from core.models import Candidate, LiveResult

# Update votes
candidate = Candidate.objects.get(id=1)
candidate.votes = 45000
candidate.is_leading = True
candidate.save()

# Update status
result = LiveResult.objects.get(constituency_id=1)
result.status = 'IN_PROGRESS'
result.votes_counted = 85000
result.rounds_completed = 12
result.save()
```

### Export & Deploy
```bash
# 1. Export JSON
cd backend && python manage.py export_json --output ../frontend/src/data/

# 2. Build frontend
cd ../frontend && npm run build

# 3. Deploy
firebase deploy --only hosting
```

## Critical Implementation Notes

### Frontend Data Strategy
- **Development:** `useElectionData` hooks fetch from Django API
- **Production:** Same hooks fetch pre-exported JSON files
- **Environment detection:** `import.meta.env.DEV`
- **Lazy loading:** Individual constituency JSONs loaded on demand

### May 4 Live Day Workflow
1. Update data via Django Admin
2. Export JSON: `python manage.py export_json`
3. Build frontend: `npm run build`
4. Deploy to Firebase: `firebase deploy`
5. Repeat every 15-30 minutes

### Color Scheme (Tailwind)
```javascript
colors: {
  udf: { DEFAULT: '#19AAED', dark: '#1589C4', light: '#4AC1F3' },
  ldf: { DEFAULT: '#ED1E26', dark: '#C41820', light: '#F24B51' },
  nda: { DEFAULT: '#FF9933', dark: '#E67E00', light: '#FFB366' },
}
```

## Missing/To Be Built

1. **Complete constituency list** - Need all 140 with district mapping
2. **React admin panel** - Live entry forms (currently Django admin only)
3. **Auto-refresh** - Poll for updates every 30s
4. **Charts/visualizations** - Vote share, trends
5. **Mobile optimization** - Touch-friendly UI
6. **2026 candidate data** - Add before May 4

## Environment Variables

### Backend (.env)
```
DB_NAME=kerala_election_2026
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

### Frontend (auto-detected)
```
DEV mode: Uses http://localhost:8000/api/
PROD mode: Uses /data/*.json files
```

## Tech Stack Summary

- **Backend:** Django 5.0 + PostgreSQL + DRF
- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS
- **Deployment:** Firebase Hosting (static)
- **Data Transfer:** JSON export mechanism

## Key Files to Reference

- **Backend setup:** `backend/SETUP.md`
- **Development guide:** `DEV_GUIDE.md`
- **Project overview:** `README.md`
- **Data models:** `backend/core/models.py`
- **API views:** `backend/core/api/views.py`
- **Data hooks:** `frontend/src/hooks/useElectionData.ts`
- **Type definitions:** `frontend/src/types/index.ts`

## Current Status

✅ **Complete:**
- Django models + migrations
- CSV import commands
- JSON export command
- DRF API endpoints
- React app structure
- TypeScript types
- Data hooks (dev + prod modes)
- Homepage (state summary + list)
- Constituency detail page
- Historical comparison
- Tailwind styling

⏳ **In Progress:**
- Constituency master data (need all 140)
- Party master data
- React admin panel

🔜 **Next Phase:**
- 2026 candidate data entry
- Live results testing
- Firebase deployment
- Mobile UI polish

## Support Resources

- Django docs: https://docs.djangoproject.com/
- React docs: https://react.dev/
- Vite docs: https://vitejs.dev/
- Tailwind docs: https://tailwindcss.com/
- Firebase docs: https://firebase.google.com/docs/hosting

## Working with This Project in Claude Code

**Suggested workflow:**
1. Start both dev servers (backend + frontend)
2. Test API endpoints first
3. Import historical data
4. Add constituencies + parties
5. Test frontend data loading
6. Build admin panel features
7. Test export → deploy cycle

**Common commands to run:**
```bash
# Check data status
cd backend && python manage.py shell
>>> from core.models import *
>>> print(f"Constituencies: {Constituency.objects.count()}")

# Export fresh JSON
python manage.py export_json --output ../frontend/src/data/

# Check frontend
cd frontend && npm run dev
```

This project is fully scaffolded and ready for development. All core infrastructure is in place.
