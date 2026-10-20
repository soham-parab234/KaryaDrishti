# LMIS Forecasting Engine — Backend API (Phases 1–7)

FastAPI backend providing data ingestion validation, SQLite persistence, NCO-2015 reference taxonomy management, deterministic title normalization, human review queue, demand–supply gap calculation engine, chronological forecasting with holdout evaluation, early warning alerts, and training-seat scenario planning for the AI-Enabled Labour Market Intelligence & Skill Demand-Supply Forecasting Engine (LMIS).

---

## 1. Prerequisites
- **Python**: 3.11, 3.12, 3.13, or 3.14+ on Windows.
- **PowerShell**: Windows PowerShell 5.1 or PowerShell 7+.

---

## 2. Setup & Virtual Environment (Windows PowerShell)

Open PowerShell in the project root directory:

```powershell
# Navigate to backend directory
cd "c:\Users\Soham Parab\Documents\lmis-forecasting-engine\backend"

# Create virtual environment (quotes handle spaces in path)
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Upgrade pip (optional)
python -m pip install --upgrade pip

# Install backend dependencies
pip install -r requirements.txt
```

> **Note on Windows execution policy**: If PowerShell blocks script execution (`Activate.ps1 cannot be loaded`), run:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
> ```
> Or invoke Python directly using `.\.venv\Scripts\python.exe`.

---

## 3. Running Automated Tests

Run the full pytest suite (58 automated tests covering health checks, CSV schema validation, atomic persistence, duplicate protection, deterministic normalization, token overlap matching, human review queue, gap arithmetic, zero-demand edge cases, evidence compatibility, time-series forecasting, holdout evaluation without leakage, early warning alerts, and training scenario simulation):

```powershell
# From project root:
.\backend\.venv\Scripts\python.exe -m pytest backend/tests -v

# Or from backend/ with active venv:
pytest tests -v
```

All tests execute against an isolated in-memory SQLite database (`sqlite:///:memory:` with `StaticPool`), leaving production and development databases unaffected.

---

## 4. Starting the Development API Server

Start the FastAPI application using Uvicorn on port 8000:

```powershell
# From project root:
.\backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 5. API Documentation & Interactive Exploration

- **Swagger UI (Interactive API Docs)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc (Alternative Documentation)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

## 6. Endpoints Implemented

### System
- `GET /api/health` — System status, database accessibility check, software version, and timestamp.
- `GET /` — API metadata and endpoint links.

### Data Ingestion (Phase 1)
- `POST /api/ingestion/validate` — Validate uploaded CSV against canonical schema 1.0 without persisting. Returns 1-indexed row-level errors and counts.
- `POST /api/ingestion/import` — Validate and atomically persist an entire CSV batch. Rejects duplicate batches via SHA-256 file hashing (`409 Conflict`). Rejects any batch with errors with zero partial writes (`422 Unprocessable Content`).
- `GET /api/ingestion/batches` — Audit ledger of imported batches.

### NCO-2015 Reference Taxonomy (Phase 2)
- `GET /api/occupations/reference` — Query loaded NCO-2015 reference occupations with search (`q`), division filter, and provenance filter.
- `GET /api/occupations/reference/{nco_code}` — Retrieve single NCO occupation hierarchy and registered aliases.
- `POST /api/occupations/reference/seed-baseline` — Idempotently seed verified Maharashtra pilot baseline occupations.
- `POST /api/occupations/reference/import` — Ingest external official DGE NCO-2015 CSV taxonomy file.

### Title Normalization & Review Queue (Phase 2)
- `POST /api/normalization/normalize` — Deterministically clean a raw job title and evaluate exact/candidate matches in-memory.
- `POST /api/normalization/process-batch/{batch_id}` — Process all postings in an imported batch into normalization review proposals.
- `GET /api/normalization/proposals` — List normalization review items filtered by status, batch ID, or search query.
- `GET /api/normalization/proposals/{proposal_id}` — Retrieve single proposal details with match rationale.
- `POST /api/normalization/proposals/{proposal_id}/review` — Submit human decision (`APPROVED`, `REJECTED`, or `OVERRIDDEN`) and learn approved aliases.

### Demand & Supply Gap Calculation Engine (Phase 3)
- `POST /api/analytics/demand` — Ingest an employer demand observation with method and provenance.
- `POST /api/analytics/aggregate-demand` — Aggregate demand from reviewed and approved job postings.
- `POST /api/analytics/supply` — Ingest a qualified supply estimate with method and provenance.
- `POST /api/analytics/training-capacity` — Record training capacity, enrolment, completion, and placement figures.
- `GET /api/analytics/gaps` — Query demand-supply gap indicators with full evidence status and classification.
- `GET /api/analytics/gaps/detail` — Full audit trail detailing posting status, data status, and limitations for an occupation.
- `POST /api/analytics/seed-baseline` — Idempotently seed demonstration baseline records clearly marked as `SYNTHETIC_DEMO`.

### Chronological Forecasting Engine (Phase 4)
- `POST /api/forecasting/generate` — Generate chronological baseline and candidate forecasts with holdout evaluation and uncertainty intervals.
- `GET /api/forecasting/projections` — Query persisted or generated forecast projections for an occupation and district.
- `GET /api/forecasting/evaluations` — List holdout evaluation scorecards with MAE, RMSE, MAPE, and model verdicts.
- `POST /api/forecasting/seed-history` — Seed multi-month historical demonstration observations for pilot occupations.

### Early-Warning Alerts (Phase 5A)
- `GET /api/alerts` — Retrieve rule-based early-warning alerts with severity filtering, triggering evidence, and prototype threshold disclosures.
- `POST /api/alerts/evaluate` — Evaluate rule thresholds across all current gap indicators and active forecasts.

### Training-Seat Scenario Planner (Phase 5B)
- `POST /api/scenarios/calculate` — Simulate training capacity expansion using the exact Master R&D Section 10 formula: `Scenario Entrants = Additional Seats × Enrolment Rate × Completion Rate × Local Entry Rate`.
- `GET /api/scenarios/defaults` — Retrieve prototype default policy rates and assumptions.

---

## 7. Data Provenance & Integrity Rules
- **Synthetic Data**: Any illustrative or demonstration figures (such as demand=680, supply=420) are labeled `SYNTHETIC_DEMO`.
- **Zero Hallucination**: No external portal integrations are claimed unless fully implemented and verified.
- **Chronological Holdout**: Historical forecast evaluation strictly splits training and test periods to guarantee zero future data leakage.
- **Seat vs Worker Separation**: Sanctioned training seats are treated strictly as institutional training capacity, never as immediate qualified labor supply.
