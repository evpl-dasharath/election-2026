# GEMINI.MD: AI Collaboration Guide

This document provides essential context for AI models interacting with this project. Adhering to these guidelines will ensure consistency and maintain code quality.

## 1. Project Overview & Purpose

* **Primary Goal:** A live results platform for the Kerala Assembly Elections 2026. It is designed to handle high-traffic results on election day (May 4, 2026) by using a hybrid architecture that transitions from a dynamic Django backend to a static JSON-driven frontend for production.
* **Business Domain:** Election Analytics & Real-time Data Visualization.

## 2. Core Technologies & Stack

* **Languages:** Python 3.11+, TypeScript 5.2+, Shell (PowerShell/Bash).
* **Frameworks & Runtimes:** Django 5.0 (Backend), React 18 (Frontend), Vite (Build Tool), Node.js 18+.
* **Databases:** PostgreSQL (Development & Data Entry), Static JSON Files (Production Delivery).
* **Key Libraries/Dependencies:** 
    * **Backend:** Django REST Framework, psycopg2-binary, django-cors-headers, firebase-admin.
    * **Frontend:** Tailwind CSS, Recharts, React Router v6, Firebase SDK.
* **Package Manager(s):** npm (Frontend), pip (Backend).

## 3. Architectural Patterns

* **Overall Architecture:** Hybrid Full-Stack/Static approach. 
    * **Development/Entry Phase:** Traditional MVC/REST architecture using Django and PostgreSQL. 
    * **Production Phase:** Static site architecture where the frontend consumes pre-exported JSON files, deployed on Firebase Hosting for maximum scalability and low latency.
    * **Data Export:** The project uses a unique "View-to-JSON" export mechanism via `backend/core/management/commands/export_json.py`. It utilizes Django's `RequestFactory` to call DRF views and save the serialized responses directly to JSON files, ensuring total consistency between API and static data.
* **Directory Structure Philosophy:**
    * `backend/`: Django project containing the data models (`core/models.py`), REST API (`core/api/`), and administrative tools.
    * `frontend/`: React/Vite project containing the UI components (`src/components/`), pages (`src/pages/`), and TypeScript definitions (`src/types/`).
    * `data/`: Raw historical and source data files (CSV, XLSX).
    * `backend/core/management/commands/`: Critical scripts for importing historical data and exporting production JSON files.

## 4. Coding Conventions & Style Guide

* **Formatting:** 
    * **Backend:** Follows PEP 8 standards. Indentation: 4 spaces.
    * **Frontend:** Adheres to standard React/TypeScript patterns. Indentation: 2 spaces. Tailwind CSS is used for styling.
* **Naming Conventions:**
    * `Python (Backend)`: snake_case for variables, functions, and file names; PascalCase for classes.
    * `TypeScript (Frontend)`: camelCase for variables and functions; PascalCase for components and types.
* **API Design:** RESTful principles using Django REST Framework. Endpoints return JSON. Main endpoints include `/api/summary/`, `/api/constituencies/`, and `/api/historical/`.
* **Error Handling:** Backend uses standard Django/DRF exception handling. Frontend uses functional components with hooks, typically handling data states (loading, error) via `useElectionData.ts`.

## 5. Key Files & Entrypoints

* **Main Entrypoint(s):** 
    * `backend/manage.py`: Django entrypoint.
    * `frontend/src/main.tsx`: React entrypoint.
    * `frontend/src/App.tsx`: Frontend routing configuration.
* **Configuration:**
    * `backend/config/settings.py`: Django application settings.
    * `backend/.env`: Environment variables (secrets, DB credentials).
    * `frontend/tailwind.config.js`: Styling configuration.
    * `firebase.json`: Deployment configuration for Firebase.
* **CI/CD Pipeline:** Deployment is primarily manual via `run.ps1` or `deploy.ps1` scripts, which automate the export-build-deploy cycle.

## 6. Development & Testing Workflow

* **Local Development Environment:**
    * Backend: `python manage.py runserver` (Port 8001).
    * Frontend: `npm run dev` (Port 3000).
* **Testing:** Primarily manual and script-based. Key verification scripts include `backend/_test_direct.py` and root-level `scrape_eci_test.py`. No formal unit testing suite (Pytest/Jest) is currently active.
* **Data Workflow:** 
    1. Import source CSVs using management commands.
    2. Update live results via Django Admin or scraping scripts.
    3. Run `python manage.py export_json` to sync data to the frontend.
    4. Build and deploy the frontend.

## 7. Specific Instructions for AI Collaboration

* **Data Integrity:** Historical data (2011, 2016, 2021) and Parliament results (2019, 2024) are foundational. Any changes to data models or import scripts must preserve these historical mappings.
* **Type Safety:** Maintain strict TypeScript definitions in `frontend/src/types/index.ts`. All API responses should have corresponding TypeScript interfaces.
* **Infrastructure (IaC):** Firebase is the primary hosting provider. Changes to `firebase.json` or `database.rules.json` affect production delivery.
* **Security:** Never hardcode database credentials or Firebase API keys. Use `.env` files for backend secrets.
* **Commit Messages:** Patterns suggest descriptive messages focused on specific features or data imports (e.g., "Add 2026 candidates," "Fix party alliance mapping").
* **Performance:** Ensure that JSON exports remain optimized for size, as the production site relies on these for all real-time data.
