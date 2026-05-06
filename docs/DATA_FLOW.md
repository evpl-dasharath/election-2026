# Data Flow

Understanding how data moves through the Kerala Election 2026 application is key to operating the platform, especially on election day.

## 1. Initial Data Seeding

Historical and master data is initially loaded into the PostgreSQL database using Django management commands:

- **Source:** CSV files located in the `data/` directory.
- **Process:**
  - `python manage.py import_2021_results` (Imports historical assembly data)
  - `python manage.py import_parliament_results` (Imports historical parliament data)
- **Destination:** Core Django models (`Constituency`, `Party`, `HistoricalResult2021`, etc.).

## 2. Development Data Flow

During development, the frontend interacts dynamically with the backend API:

- The React application sends GET requests to Django REST Framework endpoints (e.g., `/api/summary/`, `/api/constituencies/`).
- Django queries the live PostgreSQL database.
- Data is serialized and returned to the frontend.

## 3. Production Data Flow (Static Export Mechanism)

The production environment operates differently to handle high traffic efficiently. It bypasses the live API entirely.

**The Export Process:**

1. **Data Entry:** Live election results are entered into the system (typically via the Django Admin interface).
2. **Export Trigger:** An administrator runs the export command: `python manage.py export_json --output ../frontend/src/data/`
3. **JSON Generation:** Django reads the current state of the PostgreSQL database and generates several static JSON files:
   - `meta.json`: High-level state summary.
   - `constituencies.json`: Master list of all constituencies.
   - `historical.json`: Historical comparison data.
   - `parties.json`: Party master data.
   - `results/{id}.json`: Individual files for the detailed live results of each constituency.
4. **Build & Deploy:** The frontend is rebuilt. The Vite build process packages these generated JSON files into the static distribution. The result is deployed to Firebase Hosting.

**Frontend Consumption:**

When a user visits the live site:
1. The initial load fetches `meta.json` and `constituencies.json` from the static file server (Firebase).
2. When a user clicks on a specific constituency, the frontend lazy-loads the corresponding `results/{id}.json` file.
3. Because all data is served statically from a CDN, response times are extremely fast, and the database load is zero.
