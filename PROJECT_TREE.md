# Kerala Election 2026 - Complete Project Structure

```
kerala-election-2026/
│
├── 📄 README.md                    # Project overview & quick start
├── 📄 DEV_GUIDE.md                 # Comprehensive development guide
├── 📄 CLAUDE_CODE_CONTEXT.md       # Context for Claude Code sessions
├── 📄 .gitignore                   # Git ignore rules
├── 📄 firebase.json                # Firebase hosting config
│
├── 📁 backend/                     # Django + PostgreSQL Backend
│   ├── 📄 manage.py               # Django management script
│   ├── 📄 requirements.txt        # Python dependencies
│   ├── 📄 SETUP.md                # Detailed backend setup guide
│   ├── 📄 setup.sh                # Automated setup script ⭐
│   ├── 📄 .env                    # Environment variables (create this)
│   │
│   ├── 📁 config/                 # Django project settings
│   │   ├── __init__.py
│   │   ├── settings.py           # Main settings (DB, CORS, etc.)
│   │   ├── urls.py               # URL routing
│   │   └── wsgi.py               # WSGI config
│   │
│   └── 📁 core/                   # Main Django app
│       ├── __init__.py
│       ├── 📄 models.py           # ⭐ 9 data models
│       ├── 📄 admin.py            # Django admin config
│       │
│       ├── 📁 api/                # REST API
│       │   ├── __init__.py
│       │   ├── serializers.py    # DRF serializers
│       │   └── views.py          # API endpoints
│       │
│       └── 📁 management/         # Custom commands
│           ├── __init__.py
│           └── 📁 commands/
│               ├── __init__.py
│               ├── import_2021_results.py      # ⭐ CSV → DB
│               ├── import_parliament_results.py # ⭐ CSV → DB
│               └── export_json.py              # ⭐ DB → JSON
│
├── 📁 frontend/                   # React + TypeScript Frontend
│   ├── 📄 package.json           # Node dependencies
│   ├── 📄 vite.config.ts         # Vite configuration
│   ├── 📄 tailwind.config.js     # Tailwind + alliance colors
│   ├── 📄 postcss.config.js      # PostCSS config
│   ├── 📄 tsconfig.json          # TypeScript config
│   ├── 📄 tsconfig.node.json     # TypeScript node config
│   ├── 📄 index.html             # HTML entry point
│   │
│   └── 📁 src/
│       ├── 📄 main.tsx           # React entry point
│       ├── 📄 App.tsx            # Router setup
│       ├── 📄 index.css          # Tailwind imports + custom styles
│       │
│       ├── 📁 types/             # TypeScript definitions
│       │   └── index.ts          # ⭐ 12 interfaces
│       │
│       ├── 📁 hooks/             # Custom React hooks
│       │   └── useElectionData.ts # ⭐ Data fetching (dev/prod modes)
│       │
│       ├── 📁 pages/             # Page components
│       │   ├── HomePage.tsx      # ⭐ State summary + constituency list
│       │   ├── ConstituencyPage.tsx # ⭐ Detail view + historical
│       │   └── AdminPanel.tsx    # Protected admin (WIP)
│       │
│       ├── 📁 components/        # Reusable components (TBD)
│       │
│       └── 📁 data/              # ⭐ JSON exports (gitignored)
│           ├── meta.json
│           ├── constituencies.json
│           ├── historical.json
│           ├── parties.json
│           └── 📁 results/
│               ├── 001.json
│               ├── 002.json
│               └── ... (140 files)
│
└── 📁 data/                       # Source CSV files
    ├── election_candidates.csv   # ⭐ 2021 LA (complete)
    ├── 2019_Parliment.csv        # ⭐ 2019 LS
    ├── 2024_Parliment.csv        # ⭐ 2024 LS
    ├── 2016.csv                  # 2016 LA (legacy)
    └── 2021.csv                  # 2021 LA (summary)

```

## Key Files Explained

### Backend Core

**models.py** - 9 Django models:
1. `District` - 14 Kerala districts
2. `Constituency` - 140 LA seats
3. `Party` - Political parties with alliance mapping
4. `Candidate` - 2026 election candidates
5. `LiveResult` - Real-time counting status
6. `HistoricalResult2021` - Complete 2021 candidate data
7. `ConstituencyMeta2021` - 2021 metadata
8. `HistoricalResult2016` - 2016 winner/runner-up
9. `ParliamentResult` - 2019/2024 LS at AC level

**management/commands/** - 3 critical scripts:
- `import_2021_results.py` - Imports election_candidates.csv
- `import_parliament_results.py` - Imports 2019/2024 LS data
- `export_json.py` - **KEY**: Exports DB → JSON for production

### Frontend Core

**useElectionData.ts** - Smart data fetching:
```typescript
// Auto-detects environment
const USE_API = import.meta.env.DEV;

// Dev: fetches from Django API
// Prod: fetches from /data/*.json
```

**types/index.ts** - 12 TypeScript interfaces:
- Alliance, CountingStatus, ReservedCategory
- Party, Candidate, LiveResult
- ConstituencyListItem, ConstituencyDetail
- Historical2021Candidate, ParliamentResult
- HistoricalComparison, StateSummary, District

**Pages:**
- `HomePage.tsx` - State summary, filters, constituency cards
- `ConstituencyPage.tsx` - Live results + historical comparison
- `AdminPanel.tsx` - Protected admin interface (WIP)

## Data Flow Diagram

```
CSV Files              Django DB              JSON Files              React App
─────────              ─────────              ──────────              ─────────
                          
election_candidates.csv                                                
    │                     │                       │                     │
    ├─[import_2021]──────>│                       │                     │
    │                     │                       │                     │
2019_Parliment.csv        │                       │                     │
    │                     │                       │                     │
    ├─[import_parliament]>│                       │                     │
    │                     │                       │                     │
2024_Parliment.csv        │                       │                     │
    │                     │                       │                     │
    └─[import_parliament]>│                       │                     │
                          │                       │                     │
                          │◄──[Django Admin]      │                     │
                          │   (Live entry)        │                     │
                          │                       │                     │
                          ├─[export_json]────────>│                     │
                          │                       │                     │
                          │                       ├─meta.json           │
                          │                       ├─constituencies.json │
                          │                       ├─historical.json     │
                          │                       ├─parties.json        │
                          │                       └─results/*.json      │
                          │                       │                     │
                          │                       │                     │
    DEV MODE:             │                       │       PROD MODE:    │
    Frontend ◄────[API]───┤                       │       Frontend ◄────┤
    (localhost:3000)      │                       │       (Firebase)    │
```

## Setup Checklist

### Initial Setup
- [ ] Clone project
- [ ] Install Python 3.11+ & Node.js 18+
- [ ] Install PostgreSQL 14+
- [ ] Create database: `createdb kerala_election_2026`

### Backend Setup
- [ ] `cd backend`
- [ ] `python3 -m venv venv && source venv/bin/activate`
- [ ] `pip install -r requirements.txt`
- [ ] Create `.env` file with DB credentials
- [ ] `python manage.py migrate`
- [ ] `python manage.py createsuperuser`
- [ ] `./setup.sh` (populates districts & parties)
- [ ] Import constituencies (manual - see DEV_GUIDE.md)
- [ ] Historical data already imported by setup.sh

### Frontend Setup
- [ ] `cd frontend`
- [ ] `npm install`
- [ ] `mkdir -p src/data/results`
- [ ] `npm run dev`

### Test
- [ ] Backend: http://localhost:8000/admin/
- [ ] API: http://localhost:8000/api/summary/
- [ ] Frontend: http://localhost:3000

### Production Prep
- [ ] Add 2026 candidates
- [ ] Test live entry workflow
- [ ] `python manage.py export_json --output ../frontend/src/data/`
- [ ] `npm run build`
- [ ] Firebase setup: `firebase init hosting`
- [ ] `firebase deploy --only hosting`

## File Sizes (Approximate)

```
Backend:
  models.py               ~8 KB
  admin.py                ~3 KB
  api/serializers.py      ~3 KB
  api/views.py            ~4 KB
  import_2021_results.py  ~3 KB
  export_json.py          ~7 KB

Frontend:
  useElectionData.ts      ~4 KB
  types/index.ts          ~2 KB
  HomePage.tsx            ~7 KB
  ConstituencyPage.tsx    ~8 KB

Data:
  election_candidates.csv  97 KB
  2019_Parliment.csv       8 KB
  2024_Parliment.csv       10 KB

JSON Exports (production):
  meta.json               ~5 KB
  constituencies.json     ~50 KB
  historical.json         ~100 KB
  parties.json            ~5 KB
  results/*.json          ~2 KB each × 140 = 280 KB
  TOTAL                   ~440 KB (gzipped: ~120 KB)
```

## Dependencies Summary

### Backend (Python)
```
Django==5.0.3
djangorestframework==3.15.0
django-cors-headers==4.3.1
psycopg2-binary==2.9.9
python-dotenv==1.0.1
```

### Frontend (Node)
```
react: ^18.2.0
react-router-dom: ^6.22.0
recharts: ^2.12.0
typescript: ^5.2.2
vite: ^5.1.4
tailwindcss: ^3.4.1
```

## Git Strategy

### Tracked
- All source code
- Configuration files
- Documentation
- CSV data files (source)
- Setup scripts

### Ignored (.gitignore)
- `venv/`, `node_modules/`
- `*.pyc`, `__pycache__/`
- `db.sqlite3` (use PostgreSQL)
- `.env` (sensitive credentials)
- `frontend/dist/` (build output)
- `frontend/src/data/*.json` (exported data)
- `.firebase/`, `firebase-debug.log`

## Support Files

- **README.md** - Project overview, quick start
- **DEV_GUIDE.md** - Comprehensive development workflows
- **CLAUDE_CODE_CONTEXT.md** - Context for AI coding sessions
- **backend/SETUP.md** - Detailed backend setup
- **backend/setup.sh** - Automated initial setup
- **firebase.json** - Hosting config

---

**Project Status:** ✅ Fully scaffolded, ready for development

**Next Phase:** Import constituencies, add 2026 candidates, build admin UI
