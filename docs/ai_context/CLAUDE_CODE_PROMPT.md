# 🤖 Claude Code - Project Onboarding Prompt

Copy and paste this entire prompt when starting a new Claude Code session on this project:

---

**Project:** Kerala Assembly Elections 2026 - Live Results Platform

**Context:** Full-stack web app for displaying live election results on May 4, 2026. Django + PostgreSQL backend with React + TypeScript frontend. Designed for dual-mode operation: development (API-connected) and production (static JSON on Firebase).

**Tech Stack:**
- Backend: Django 5.0, PostgreSQL, Django REST Framework
- Frontend: React 18, TypeScript, Vite, Tailwind CSS
- Deploy: Firebase Hosting (static)
- Data: CSV import → Django DB → JSON export → React

**Project Status:** ✅ Fully scaffolded and ready for development. All core infrastructure complete.

**Key Architecture:**
```
CSV Files → Django Import Commands → PostgreSQL Database
                                           ↓
                                    Django Admin (live entry)
                                           ↓
                                    JSON Export Command
                                           ↓
                              frontend/src/data/*.json
                                           ↓
                                     React App
                                           ↓
                                   Firebase Hosting
```

**File Locations:**
- Backend: `backend/core/models.py` (9 models), `backend/core/api/` (REST API)
- Frontend: `frontend/src/pages/` (3 pages), `frontend/src/hooks/useElectionData.ts` (smart data fetching)
- Data: `data/*.csv` (historical results), `frontend/src/data/` (JSON exports - gitignored)
- Docs: `README.md`, `DEV_GUIDE.md`, `QUICK_REFERENCE.md`, `PROJECT_TREE.md`

**Current Data:**
- ✅ 2021 LA results (complete candidate data)
- ✅ 2019/2024 Parliament results (AC-level)
- ⏳ Need: 140 constituencies with district mapping
- ⏳ Need: 2026 candidate data (add before May 4)

**Smart Data Hook (useElectionData.ts):**
- Development: Fetches from Django API (http://localhost:8000/api/)
- Production: Fetches from static JSON (/data/*.json)
- Auto-detects environment via `import.meta.env.DEV`

**Common Tasks:**

1. **Start dev servers:**
```bash
# Terminal 1
cd backend && source venv/bin/activate && python manage.py runserver

# Terminal 2
cd frontend && npm run dev
```

2. **Add 2026 candidates:**
```python
from core.models import Constituency, Party, Candidate
constituency = Constituency.objects.get(number=1)
party = Party.objects.get(code='INC')
Candidate.objects.create(name='Name', party=party, constituency=constituency)
```

3. **Export for production:**
```bash
cd backend
python manage.py export_json --output ../frontend/src/data/
cd ../frontend
npm run build
firebase deploy --only hosting
```

**May 4 Workflow:**
1. Update votes in Django Admin
2. Export JSON: `python manage.py export_json`
3. Build: `npm run build`
4. Deploy: `firebase deploy`
5. Repeat every 15-30 minutes

**What needs to be built:**
- Complete constituency master list (140 entries with district mapping)
- React admin panel with live entry forms
- Auto-refresh mechanism (poll every 30s)
- Charts/visualizations (vote share, trends)
- Mobile UI optimization
- 2026 candidate data entry

**Important Files to Reference:**
- Models: `backend/core/models.py`
- API: `backend/core/api/views.py`
- Export: `backend/core/management/commands/export_json.py`
- Data Hook: `frontend/src/hooks/useElectionData.ts`
- Types: `frontend/src/types/index.ts`
- Homepage: `frontend/src/pages/HomePage.tsx`

**Dependencies Already Installed:**
- Backend: Django, DRF, CORS, psycopg2, python-dotenv
- Frontend: React, React Router, Recharts, TypeScript, Tailwind

**Database Models (9):**
1. District (14 Kerala districts)
2. Constituency (140 LA seats)
3. Party (UDF/LDF/NDA parties with colors)
4. Candidate (2026 candidates)
5. LiveResult (counting status)
6. HistoricalResult2021 (complete 2021 data)
7. ConstituencyMeta2021 (2021 metadata)
8. HistoricalResult2016 (winner/runner-up)
9. ParliamentResult (2019/2024 LS)

**Alliance Colors:**
- UDF: #19AAED (Blue)
- LDF: #ED1E26 (Red)
- NDA: #FF9933 (Saffron)

**Key Commands:**
```bash
# Check data status
python manage.py shell
>>> from core.models import *
>>> print(f"Constituencies: {Constituency.objects.count()}")

# Import historical data
python manage.py import_2021_results data/election_candidates.csv
python manage.py import_parliament_results 2024 data/2024_Parliment.csv

# Export to JSON
python manage.py export_json --output ../frontend/src/data/

# Build frontend
npm run build

# Deploy
firebase deploy --only hosting
```

**URLs:**
- Frontend Dev: http://localhost:3000
- Django Admin: http://localhost:8000/admin/
- API: http://localhost:8000/api/summary/

**Read these for full context:**
- `README.md` - Project overview
- `DEV_GUIDE.md` - Comprehensive workflows
- `QUICK_REFERENCE.md` - Command cheat sheet
- `PROJECT_TREE.md` - Complete file structure

**Current Session Goal:** [State what you want to work on]

---

Ready to start coding! What would you like to build or fix?
