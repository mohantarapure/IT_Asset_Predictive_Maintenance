# IT Asset & Predictive Maintenance Management System

A medium-sized BTech AI & Data Science mini project for managing IT infrastructure assets, maintenance activity, failures, schedules, readings, reports, and estimated failure risk.

## Problem and objectives

IT teams need a single view of assets and maintenance history. This project stores normalized records in SQLite, produces SQL/Python analytics, and demonstrates a simple predictive-maintenance workflow so that inspection can be planned before a possible failure.

## Technology

Python, Flask, SQLite, HTML/CSS/JavaScript, pandas, and scikit-learn. Chart.js is optional: the dashboard also displays textual tables if the CDN is unavailable. After installing dependencies, normal application usage is local and does not require an external API.

## Features and pages

Authentication (`/login`, `/register`) uses Flask sessions and Werkzeug password hashes. Protected routes enforce ownership, so each user sees only their own assets and related records. The application includes the dashboard, asset CRUD, maintenance records, failure records, schedules, manually entered readings, SQL/Python analytics, category master data, CSV exports, and an asset detail page with predicted risk.

## Database design

The database file is `it_asset_maintenance.db`. `schema.sql` enables foreign keys, constraints, indexes, the `asset_maintenance_summary` view, and the `log_deleted_asset` audit trigger. The database is in 3NF: values are atomic (1NF), tables use single-column keys with no partial dependency (2NF), and descriptive category/user information is stored separately to avoid transitive dependency (3NF). Repeating groups such as multiple maintenance records are represented as related rows, not repeated columns.

The ER diagram and relational schema are in [`docs/er_diagram.md`](docs/er_diagram.md). `queries.sql` contains more than 15 runnable SQLite examples covering filtering, aggregates, joins, subqueries, dates, cost, failures, the view, and grouping. SQLite has no stored-procedure language; `mysql_version.sql` therefore contains clearly marked academic MySQL examples only. The running application never uses MySQL.

## Analytics and ML

The reports page calculates totals, average/minimum/maximum costs, downtime, failure counts, category comparisons, monthly maintenance cost, and top assets using SQL aggregates and pandas. The model pipeline builds features from asset readings plus maintenance/failure history, handles missing values, creates a transparent target, performs a stratified train/test split, trains `RandomForestClassifier`, saves `model.pkl`, and reports actual accuracy, precision, recall, F1, and confusion matrix values. Metrics are never invented.

**The predictive model is an academic demonstration using available historical/sample asset data.** It does not guarantee failure. If training data is insufficient or a model cannot be loaded, the asset detail page clearly labels its result **Rule-based fallback** and scores high temperature, error count, downtime, repeated failures, and maintenance frequency.

## Installation and running

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python reset_db.py
python seed.py
python train_model.py
python app.py
```

Open `http://127.0.0.1:5000`. Demo credentials are `demo@example.com` and `demo123`. A second seeded user is `student@example.com` / `student123`. To reset only the database, run `python reset_db.py`; it does not delete source files.

## Project structure

`app.py` is the Flask application. `database.py` manages SQLite connections. `analytics.py` contains report queries. `ml_model.py` contains feature creation, training, metrics, prediction, and fallback. `seed.py` creates approximately 12 assets, 30 maintenance rows, 6 failures, 24 readings, and schedules. `templates/` and `static/` contain the UI. `schema.sql`, `queries.sql`, `mysql_version.sql`, and `docs/` support DBMS presentation and viva discussion.

## Validation and limitations

Input validation covers required fields, duplicate tags, numeric ranges, ownership, foreign-key-safe categories, and invalid ML states. The sample data is deliberately small and academic; real operations would require more observations, better temporal target construction, authentication hardening, CSRF protection, and a production database. The current model is for risk estimation and recommended inspection only.

## Suggested presentation flow

Explain the normalized schema and relationships, demonstrate login and user isolation, add an asset and reading, show the dashboard and SQL report, open an asset detail page to explain model features/fallback, and finish by showing `queries.sql`, the trigger log, the view, and the MySQL limitation reference.
