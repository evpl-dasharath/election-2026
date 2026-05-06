# 🚀 COPY-PASTE THIS INTO CLAUDE CODE

When you open this project in Claude Code, paste the following prompt to get started immediately:

---

## PROMPT START ⬇️

I'm working on the **Kerala Election 2026 Live Results Platform** - a full-stack web app for displaying real-time election results on May 4, 2026.

### 🏗️ Tech Stack
- **Backend:** Django 5.0 + PostgreSQL + Django REST Framework
- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS
- **Deploy:** Firebase Hosting (static site)
- **Data Strategy:** CSV → Django DB → JSON export → React

### 📁 Project Structure
```
kerala-election-2026/
├── backend/
│   ├── core/
│   │   ├── models.py              # 9 models (District, Constituency, Party, etc.)
│   │   ├── admin.py               # Django admin config
│   │   ├── api/                   # REST API (6 endpoints)
│   │   └── management/commands/
│   │       ├── import_2021_results.py
│   │       ├── import_parliament_results.py
│   │       └── export_json.py     # KEY: DB → JSON for production
│   └── requirements.txt
│
└── frontend/
    └── src/
        ├── hooks/
        │   └── useElectionData.ts # Smart hook (dev=API, prod=JSON)
        ├── pages/
        │   ├── HomePage.tsx       # State summary + constituency list
        │   ├── ConstituencyPage.tsx # Detail + historical comparison
        │   └── AdminPanel.tsx     # Live entry (WIP)
        └── types/index.ts         # 12 TypeScript interfaces
```

### 🎯 Current Status
✅ **Complete:**
- Django models & migrations
- REST API with 6 endpoints
- React app with 3 pages
- Smart data hook (auto-switches dev/prod)
- CSV import commands
- JSON export command
- Historical data (2021 LA, 2019/2024 LS)
- Tailwind styling with alliance colors

⏳ **Need to Build:**
- Complete constituency list (all 140 with district mapping)
- 2026 candidate data entry
- React admin panel for live entry
- Charts/visualizations
- Auto-refresh mechanism

### 🔑 Key Files
- **Models:** `backend/core/models.py` (9 models)
- **API:** `backend/core/api/views.py` (6 endpoints)
- **Export:** `backend/core/management/commands/export_json.py`
- **Data Hook:** `frontend/src/hooks/useElectionData.ts` (auto-switches)
- **Types:** `frontend/src/types/index.ts` (12 interfaces)

### 💡 Smart Architecture
The `useElectionData.ts` hook automatically detects environment:
- **Development:** Fetches from Django API (`localhost:8000/api/`)
- **Production:** Fetches from static JSON files (`/data/*.json`)
- **Detection:** Uses `import.meta.env.DEV`

### 🎨 Alliance Colors (Tailwind)
- **UDF:** `#19AAED` (Blue)
- **LDF:** `#ED1E26` (Red)
- **NDA:** `#FF9933` (Saffron)
- **OTH:** `#808080` (Gray)

### 📊 Database Models (9)
1. `District` - 14 Kerala districts
2. `Constituency` - 140 LA seats
3. `Party` - Political parties (UDF/LDF/NDA)
4. `Candidate` - 2026 candidates
5. `LiveResult` - Real-time counting status
6. `HistoricalResult2021` - Complete 2021 candidate data
7. `ConstituencyMeta2021` - 2021 metadata
8. `HistoricalResult2016` - 2016 winner/runner-up
9. `ParliamentResult` - 2019/2024 LS at AC level

### 🔄 May 4, 2026 Workflow
1. Update results in Django Admin
2. Export: `python manage.py export_json --output ../frontend/src/data/`
3. Build: `npm run build`
4. Deploy: `firebase deploy --only hosting`
5. Repeat every 15-30 minutes

### 📚 Documentation
- `README.md` - Quick start
- `DEV_GUIDE.md` - Comprehensive workflows
- `QUICK_REFERENCE.md` - Command cheat sheet
- `PROJECT_TREE.md` - File structure
- `backend/SETUP.md` - Backend setup

### 🎯 Today's Goal
[Replace this with what you want to work on]

Example goals:
- "Build the complete constituency list with district mapping"
- "Create React admin panel for live vote entry"
- "Add charts showing alliance vote share trends"
- "Import 2026 candidate data"
- "Optimize JSON export for faster loading"
- "Build auto-refresh mechanism"

---

Ready to start! What should we work on first?

## PROMPT END ⬆️

---

# 🎓 Quick Tips for Claude Code

### First Time Setup Commands
```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
./setup.sh

# Frontend
cd frontend
npm install
```

### Development Servers
```bash
# Terminal 1 - Backend
cd backend && python manage.py runserver

# Terminal 2 - Frontend
cd frontend && npm run dev
```

### Quick Database Check
```python
# python manage.py shell
from core.models import *
print(f"Constituencies: {Constituency.objects.count()}")
print(f"Parties: {Party.objects.count()}")
print(f"2021 Results: {HistoricalResult2021.objects.count()}")
```

### Common Tasks

**Add a candidate:**
```python
from core.models import Constituency, Party, Candidate
c = Constituency.objects.get(number=1)
p = Party.objects.get(code='INC')
Candidate.objects.create(name='Name', party=p, constituency=c)
```

**Export JSON:**
```bash
python manage.py export_json --output ../frontend/src/data/
```

**Build for production:**
```bash
cd frontend
npm run build
firebase deploy --only hosting
```

### Useful References
- Keep `QUICK_REFERENCE.md` open for commands
- Check `backend/core/models.py` for database schema
- Review `frontend/src/hooks/useElectionData.ts` for data logic
- See `DEV_GUIDE.md` for detailed workflows

### File You'll Edit Most
- `backend/core/models.py` - Adding/modifying data models
- `frontend/src/pages/*.tsx` - UI components
- `backend/core/admin.py` - Django admin customization
- `frontend/src/hooks/useElectionData.ts` - Data fetching logic

---

# 🔥 Power User Tips

### Speed Up Development
1. Keep both dev servers running in separate terminals
2. Use Django admin for quick data entry: `http://localhost:8000/admin/`
3. Test API directly: `http://localhost:8000/api/summary/`
4. Use React DevTools for component debugging

### Debugging
- **Backend errors:** Check Django server terminal
- **Frontend errors:** Check browser console (F12)
- **API issues:** Use `curl http://localhost:8000/api/summary/`
- **Database issues:** `python manage.py dbshell`

### Before May 4
- [ ] Import all 140 constituencies
- [ ] Add 2026 candidates
- [ ] Test full export → build → deploy cycle
- [ ] Set up Firebase project
- [ ] Create backup strategy

---

**Ready to build! 🚀**
