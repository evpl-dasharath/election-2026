# Architecture

The Kerala Election 2026 project employs a hybrid architecture designed for both active development and robust production deployment on election day.

## Components

### 1. Backend (Django + PostgreSQL)
- **Framework:** Django 5.0
- **Database:** PostgreSQL
- **Purpose:** Acts as the source of truth during development and data entry.
- **Functionality:**
  - Manages complex relational data (Districts, Constituencies, Parties, Candidates, Historical Results).
  - Provides a REST API (via Django REST Framework) for the frontend during development.
  - Offers a Django Admin interface for easy data entry and correction.
  - Includes management commands for importing CSV data and exporting static JSON files.

### 2. Frontend (React + TypeScript + Vite)
- **Framework:** React 18
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **Purpose:** The user-facing application displaying live election results.
- **Functionality:**
  - Connects to the Django API during development.
  - In production, it operates completely independent of the Django backend, fetching pre-exported static JSON files instead.
  - This "static site" approach ensures high performance and reliability under heavy traffic on election day.

## Deployment Strategy (Production)

The production deployment strategy relies on Firebase Hosting and a static site architecture:

1. **Data Export:** The Django backend is used to generate static JSON files representing the current state of the database (`meta.json`, `constituencies.json`, `historical.json`, etc.).
2. **Build:** The React frontend is built (`npm run build`). The build process bundles the application and includes the exported JSON data within the static assets.
3. **Deploy:** The static bundle is deployed to Firebase Hosting.
4. **Live Updates:** As new results come in, data is updated in the Django backend (e.g., via the admin panel). The JSON export process is re-run, the frontend is rebuilt, and the new static bundle is deployed to Firebase.

This architecture decouples the database from the live web traffic, ensuring the application remains fast and available even with millions of simultaneous users.
