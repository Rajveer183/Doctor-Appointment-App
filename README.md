# CarePoint — Doctor Appointment Booking System

FastAPI + React appointment booking system with symptom-based doctor matching
(rapidfuzz + NVIDIA embeddings/ChromaDB) and an NVIDIA tool-calling chatbot.

## Backend

```bash
cd backend
python -m venv venv
venv/Scripts/activate        # Windows; use `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt

cp .env.example .env         # fill in NVIDIA_API_KEY
python -m app.seed           # populate SQLite with demo doctors/patients/slots
python -m app.embed_taxonomy # embed the symptom taxonomy into ChromaDB (needs NVIDIA_API_KEY)

python -m uvicorn app.main:app --reload --port 8000
```

Run tests: `python -m pytest tests/ -v`

Without `NVIDIA_API_KEY` set, the app still runs — the emergency and fuzzy-match
symptom layers work with no external dependency, the embedding fallback layer and
chatbot just report they're unavailable instead of crashing.

## Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173, proxies /api to http://127.0.0.1:8000
```

There's no auth: use the patient/doctor dropdown in the top nav to switch who
you're acting as (persisted per-browser via localStorage).

## Re-seeding

`python -m app.seed` wipes and regenerates the whole database (6 doctors across 5
specialties, ~3 weeks of slots, 7 patients, some pre-existing bookings) — safe to
re-run any time you want a clean demo state.
