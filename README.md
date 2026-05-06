# Kerala Assembly Elections 2026 - Live Results Platform

A full-stack web application for displaying live election results as they come in on May 4, 2026.

## Architecture

**Development Mode:**
- Backend: Django + PostgreSQL (live database)
- Frontend: React + TypeScript + Vite (connects to Django API)

**Production Mode (Firebase):**
- Frontend only: Static React app
- Data: Pre-exported JSON files (no backend needed)
- Updates: Manual JSON export + redeploy

---

## Project Structure

```
kerala-election-2026/
├── backend/                    # Django + PostgreSQL
│   ├── core/                   # Main app
│   │   ├── models.py          # Data models
│   │   ├── admin.py           # Django admin interface
│   │   ├── api/               # REST API
│   │   └── management/        # Import/export commands
│   │       └── commands/
│   │           ├── import_2021_results.py
│   │           ├── import_parliament_results.py
│   │           └── export_json.py
│   ├── config/                # Django settings
│   ├── scripts/               # Backend utility scripts
│   ├── requirements.txt       # Python dependencies
│   ├── manage.py
│   └── SETUP.md              # Detailed backend setup guide
│
├── frontend/                  # React + TypeScript + Vite
│   ├── src/
│   │   ├── components/       # Reusable components
│   │   ├── pages/            # Page components
│   │   ├── hooks/            # Custom hooks
│   │   ├── types/            # TypeScript types
│   │   ├── data/             # Exported JSON (for production)
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── data/                      # Source CSV files
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md        # System architecture details
│   ├── DATA_FLOW.md           # Data import/export flows
│   ├── plans/                 # Planning and implementation documents
│   ├── ai_context/            # AI generation context and prompts
│   ├── reports/               # Project delivery and handoff reports
│   └── DEV_GUIDE.md           # Developer guidelines
├── scripts/                   # Root utility and scraping scripts
│   ├── scraping/
│   ├── data_management/
│   └── utils/
└── archive/                   # Archived artifacts and old files
```

For more details on the system, see the documentation in `docs/`:
- [Architecture Details](docs/ARCHITECTURE.md)
- [Data Flow Details](docs/DATA_FLOW.md)

---

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Install Python dependencies
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup PostgreSQL database
createdb kerala_election_2026

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Import data (see SETUP.md for detailed instructions)
python manage.py import_2021_results ../data/election_candidates.csv
python manage.py import_parliament_results 2019 ../data/2019_Parliment.csv
python manage.py import_parliament_results 2024 ../data/2024_Parliment.csv

# Start development server
python manage.py runserver
```

Backend will be available at: http://localhost:8000

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: http://localhost:3000

---

## Data Models

### Core Models

- **District**: 14 Kerala districts
- **Constituency**: 140 Legislative Assembly constituencies
- **Party**: Political parties with alliance mapping (UDF/LDF/NDA)
- **Candidate**: 2026 election candidates
- **LiveResult**: Real-time counting status per constituency

### Historical Models

- **HistoricalResult2021**: Complete candidate-level 2021 LA results
- **ConstituencyMeta2021**: 2021 constituency metadata (winner, margin)
- **ParliamentResult**: 2019 & 2024 LS results at AC segment level

---

## Workflows

### Development Workflow (Before May 4)

1. Work on Django backend
2. Frontend connects to Django API
3. Test with sample data
4. Iterate on UI/UX

### Live Results Day (May 4, 2026)

**Option 1: Django Admin Entry**
1. Open http://localhost:8000/admin/
2. Navigate to **Candidates** → Update vote counts
3. Navigate to **Live Results** → Update counting status
4. Run: `python manage.py export_json --output ../frontend/src/data/`
5. Rebuild frontend: `npm run build`
6. Deploy to Firebase: `firebase deploy`

**Option 2: React Admin Panel** (to be built)
- Protected admin route in React app
- Live entry forms
- Auto-export JSON on save

### Firebase Deployment

```bash
# Build production bundle
cd frontend
npm run build

# Deploy to Firebase
firebase deploy --only hosting
```

---

## API Endpoints (Development)

### State Summary
```
GET /api/summary/
```

### All Constituencies
```
GET /api/constituencies/
```

### Constituency Detail
```
GET /api/constituencies/{id}/
```

### Historical Comparison
```
GET /api/historical/{constituency_number}/
```

### Parties
```
GET /api/parties/
```

---

## JSON Export Structure (Production)

After running `python manage.py export_json`, creates:

```
frontend/src/data/
├── meta.json                    # State summary (~5KB)
├── constituencies.json          # All 140 constituencies (~50KB)
├── historical.json              # 2021 + 2019/2024 comparison (~100KB)
├── parties.json                 # Party master data (~5KB)
└── results/                     # Individual constituency details
    ├── 001.json                 # Manjeshwar
    ├── 002.json                 # Kasaragod
    └── ...
    └── 140.json                 # Neyyattinkara
```

**Loading Strategy:**
1. Load `meta.json` + `constituencies.json` first → instant state overview
2. Lazy-load individual `results/{number}.json` on constituency click
3. Load `historical.json` only when comparison view opened

---

## Key Features

### Homepage
- State-level summary (total seats, alliance breakdown)
- Filterable constituency list (by alliance, status, search)
- Real-time status badges

### Constituency Detail Page
- Live counting progress
- Candidate-wise results with leading/winner indicators
- Historical comparison (2021 LA, 2019/2024 LS)
- Alliance vote share visualization

### Admin Panel
- Password-protected access
- Quick entry forms (to be built)
- JSON export trigger

---

## Technology Stack

### Backend
- **Framework:** Django 5.0
- **Database:** PostgreSQL
- **API:** Django REST Framework
- **CORS:** django-cors-headers

### Frontend
- **Framework:** React 18
- **Language:** TypeScript
- **Build Tool:** Vite
- **Routing:** React Router v6
- **Styling:** Tailwind CSS
- **Charts:** Recharts

### Deployment
- **Hosting:** Firebase Hosting
- **Strategy:** Static site with pre-exported JSON

---

## Color Scheme

- **UDF:** `#19AAED` (Blue)
- **LDF:** `#ED1E26` (Red)
- **NDA:** `#FF9933` (Saffron)
- **Neutral:** Gray scale

---

## Browser Support

- Chrome/Edge: Latest 2 versions
- Firefox: Latest 2 versions
- Safari: Latest 2 versions
- Mobile: iOS Safari, Chrome Mobile

---

## Performance Targets

- **Initial Load:** < 2s on 3G
- **State Overview:** < 500ms
- **Constituency Detail:** < 1s (including lazy-loaded data)
- **JSON File Sizes:** Total < 500KB (gzipped)

---

## Next Steps

### Before Launch (April 2026)
- [ ] Complete constituency master list (all 140 with districts)
- [ ] Populate party master data with colors
- [ ] Import all historical data
- [ ] Build React admin panel
- [ ] Add charts/visualizations
- [ ] Mobile UI optimization
- [ ] Firebase setup

### May 4, 2026 (Election Day)
- [ ] Test live entry workflow
- [ ] Set up auto-refresh mechanism
- [ ] Monitor Firebase quotas
- [ ] Prepare backup export scripts

---

## Troubleshooting

See `backend/SETUP.md` for detailed backend troubleshooting.

Common issues:
- **PostgreSQL connection failed:** Check credentials in `.env`
- **API returns empty:** Ensure data is imported
- **Frontend 404s:** Check Vite dev server is running
- **Production data stale:** Re-run `export_json` command

---

## License

Private project for Kerala Election 2026 results tracking.

---

## Contact

Project maintained by Dasharath for Techno Bharat Mission.
