# commands.md — Deploying the Doctor Appointment Booking app to GCP

Copy-pasteable commands to take this repository from a local checkout to a running
deployment on Cloud Run (backend + frontend), backed by Cloud SQL for PostgreSQL, with
images in Artifact Registry and secrets in Secret Manager.

Repository structure this guide reflects:

```
backend/
  Dockerfile            Cloud Run image, build context = ./backend
  .dockerignore         note: does NOT exclude chroma_data/ — see step 2
  requirements.txt
  app/{main,config,database,models,schemas,errors,utils,seed,taxonomy}.py
  app/chroma_client.py        PersistentClient over chroma_persist_dir
  app/embed_taxonomy.py       offline: embeds taxonomy into Chroma (needs NVIDIA_API_KEY)
  app/routers/{doctors,patients,appointments,dashboard,symptom_search,chat}.py
  app/services/{doctors,patients,appointments,slots}.py
  app/services/{nvidia_client,symptom_match,chat,chat_tools}.py
  scripts/create_tables.py    non-destructive schema creation (app/seed.py drops first)
  tests/{conftest.py,test_booking_race.py}
  chroma_data/                gitignored; must be built locally before the image build
frontend/
  Dockerfile            Cloud Run image, build context = ./frontend
  nginx.conf            static only, no proxy_pass (see the comment in the file)
  .dockerignore
  vite.config.js        dev-only /api proxy to 127.0.0.1:8000
  src/App.jsx           ⚠ still the stock Vite starter page
.gcloudignore
```

## Read this before you start

Five things about this repo determine everything below.

**1. SQLite cannot come with you.** `app/config.py` defaults to
`sqlite+aiosqlite:///./appointments.db`. On Cloud Run the container filesystem is an
in-memory tmpfs: wiped on every restart, not shared between instances. Two instances
would hold two different sets of bookings and both would vanish on redeploy. Mounting
the file from Cloud Storage does not rescue this — gcsfuse provides no POSIX byte-range
locking, which is the exact mechanism `BEGIN IMMEDIATE` in `app/database.py` depends on.
This guide provisions Cloud SQL for PostgreSQL. SQLite stays the local-dev default.

**2. The app runs on naive local time, so the container's timezone is load-bearing.**
`app/utils.py::local_now()` returns `datetime.now()` with no timezone, matching the naive
clinic-local slot timestamps that `seed.py` writes — a deliberate single-clinic decision,
documented in the docstring. Containers run in UTC by default. Deploy without pinning the
timezone and every "is this slot in the past" check, every next-available-slot lookup and
the whole cancellation window shift by 5h30m in IST — silently, with no error. `TZ` is set
in `backend/Dockerfile` and again on the service in step 8. Change the clinic's timezone in
both places, or not at all.

**3. The Chroma taxonomy index has to be baked into the image.** `app/chroma_client.py`
opens a `PersistentClient` on `chroma_persist_dir` (`./chroma_data`), and
`app/embed_taxonomy.py` populates it from an NVIDIA embeddings call. Nothing populates it
at startup. If the directory ships empty, `symptom_match._embedding_match` hits
`collection.count() == 0`, returns `None`, and the embedding layer silently degrades to
fuzzy-only — no exception, no log line, just worse matching. Step 2 builds it; the
Dockerfile copies it in.

**4. Nothing in the repo creates the SQL schema.** `app/main.py` never calls `create_all`,
and the only place that does is `app/seed.py`, which runs `drop_all()` first.
`backend/scripts/create_tables.py` is a non-destructive `create_all` that runs as a Cloud
Run Job in step 7. That is not migrations — see "Next steps".

**5. The frontend is the untouched Vite scaffold.** `src/App.jsx` is still the counter and
the Vite/React logo links. Steps 9–10 build and deploy it correctly, and what they put on
the internet is the starter page. Skip them until there's a real UI if you prefer —
steps 1–8 stand alone and give you a working API.

---

## 0. Prerequisites

- [`gcloud` CLI](https://cloud.google.com/sdk/docs/install), authenticated: `gcloud auth login`
- Docker Desktop — for the local validation pass in step 3, and required for the frontend
  image build in step 9 (which needs `--build-arg`)
- Python 3.12+ and Node.js 20+
- An NVIDIA NIM API key: https://build.nvidia.com/
- The Cloud SQL Auth Proxy, if you want to reach the production DB from your machine

```bash
export PROJECT_ID=your-gcp-project-id
export REGION=asia-south1          # Mumbai; matches an IST clinic and keeps DB latency low
export AR_REPO=appointments
export BACKEND_SVC=appointments-backend
export FRONTEND_SVC=appointments-frontend
export SQL_INSTANCE=appointments-db
export DB_NAME=appointments
export DB_USER=appuser
export CLINIC_TZ=Asia/Kolkata

gcloud config set project $PROJECT_ID
```

Windows note: these are bash exports — use Git Bash or WSL, or translate to
`$env:PROJECT_ID="..."` in PowerShell.

---

## 1. Run it locally first

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set NVIDIA_API_KEY — /api/chat and the embedding layer need it

python -m app.seed                # ⚠ drops and recreates every table
uvicorn app.main:app --reload --port 8000
```

Verify:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/specialties
curl "http://localhost:8000/api/doctors/1/slots"

curl -X POST http://localhost:8000/api/symptom-search \
  -H "Content-Type: application/json" -d '{"text": "my knee has been hurting"}'
```

Tests: `cd backend && python -m pytest -q`

Frontend, second terminal: `cd frontend && npm install && npm run dev`

---

## 2. Build the Chroma taxonomy index (once, locally)

Skip only if `backend/chroma_data/` already exists and is populated.

```bash
cd backend
source venv/bin/activate
python -m app.embed_taxonomy      # needs NVIDIA_API_KEY in .env
ls chroma_data                    # must show Chroma's sqlite3 file + segment dirs, not be empty
```

Re-run this whenever `app/taxonomy.py` changes, then rebuild and redeploy the image —
the index is baked in, not mounted.

Sanity-check that the embedding layer, not just fuzzy matching, is actually firing. A
deliberate paraphrase that shares no words with any taxonomy phrase should come back with
`"source": "embedding"`:

```bash
curl -X POST http://localhost:8000/api/symptom-search \
  -H "Content-Type: application/json" \
  -d '{"text": "my little one has been running a temperature since last night"}'
```

If that returns `"source": "none"`, the index is empty or the threshold needs
recalibrating — fix it here, because in production the same condition is silent.

---

## 3. Local Docker validation (do this before touching GCP)

### Backend

```bash
docker build -t appt-backend:local ./backend

docker run --rm -p 8080:8080 --name appt-backend-test \
  -e DATABASE_URL="sqlite+aiosqlite:////tmp/appointments.db" \
  -e FRONTEND_ORIGIN="http://localhost:8081" \
  -e NVIDIA_API_KEY="$NVIDIA_API_KEY" \
  appt-backend:local
```

In another terminal — the container starts with an empty database, so create the schema
inside it first:

```bash
docker exec appt-backend-test python -m scripts.create_tables
curl http://localhost:8080/api/health
curl http://localhost:8080/api/specialties     # [] until seeded, but must return 200

# confirm TZ and the baked index both survived the build
docker exec appt-backend-test date
docker exec appt-backend-test python -c \
  "from app.chroma_client import get_taxonomy_collection as c; print('taxonomy phrases:', c().count())"

docker stop appt-backend-test
```

`date` must print IST, and the phrase count must be non-zero. A zero count here means
`chroma_data/` didn't make it into the image — check that `backend/.dockerignore` still
doesn't list it.

### Frontend

```bash
docker build --build-arg VITE_API_URL=http://localhost:8080 \
  -t appt-frontend:local ./frontend

docker run --rm -p 8081:8080 --name appt-frontend-test appt-frontend:local
curl http://localhost:8081/healthz
docker stop appt-frontend-test
```

---

## 4. One-time GCP project setup

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  sqladmin.googleapis.com

gcloud artifacts repositories create $AR_REPO \
  --repository-format=docker \
  --location=$REGION \
  --description="Appointment booking images"

gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

---

## 5. Cloud SQL and secrets

```bash
gcloud sql instances create $SQL_INSTANCE \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=$REGION \
  --storage-size=10GB \
  --storage-auto-increase \
  --backup-start-time=20:00

gcloud sql databases create $DB_NAME --instance=$SQL_INSTANCE

export DB_PASSWORD=$(openssl rand -base64 24)
gcloud sql users create $DB_USER --instance=$SQL_INSTANCE --password="$DB_PASSWORD"

export SQL_CONN_NAME=$(gcloud sql instances describe $SQL_INSTANCE \
  --format='value(connectionName)')
echo $SQL_CONN_NAME    # your-project:asia-south1:appointments-db
```

`db-f1-micro` is the cheapest shared-core tier — fine for a demo, no SLA. Move to
`db-g1-small` or a dedicated-core tier before real traffic.

Cloud Run reaches Cloud SQL over a Unix socket at `/cloudsql/<connection-name>`; asyncpg
takes that as the `host` query parameter:

```bash
export DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${SQL_CONN_NAME}"

printf "%s" "$DATABASE_URL"        | gcloud secrets create DATABASE_URL --data-file=-
printf "%s" "your_nvidia_api_key"  | gcloud secrets create NVIDIA_API_KEY --data-file=-
```

The whole URL goes in the secret rather than just the password, because passwords can
contain characters that need URL-escaping and assembling the string at runtime is where
that breaks quietly.

```bash
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
export RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for SECRET in DATABASE_URL NVIDIA_API_KEY; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:${RUNTIME_SA}" --role="roles/secretmanager.secretAccessor"
done

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${RUNTIME_SA}" --role="roles/cloudsql.client"
```

`RUNTIME_SA` is the default Compute Engine service account Cloud Run uses unless you pass
`--service-account`. If your org disallows it, create a dedicated one and pass it to every
`gcloud run deploy` below.

---

## 6. Build and push the backend image

```bash
gcloud builds submit \
  --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/backend:v1 \
  --timeout=20m \
  ./backend
```

Build context is `./backend`. `backend/chroma_data/` must exist locally at this point
(step 2) — it's gitignored, so a fresh clone won't have it.

---

## 7. Create the schema (Cloud Run Job)

Run this **before** the service, so the first request doesn't hit missing tables.

```bash
gcloud run jobs create appointments-migrate \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/backend:v1 \
  --region $REGION \
  --set-secrets="DATABASE_URL=DATABASE_URL:latest" \
  --set-cloudsql-instances=$SQL_CONN_NAME \
  --set-env-vars="TZ=${CLINIC_TZ}" \
  --command python \
  --args "-m,scripts.create_tables" \
  --max-retries 1 --task-timeout 5m

gcloud run jobs execute appointments-migrate --region $REGION --wait
```

Re-run that `execute` after any schema change, pointing the job at the new tag first:

```bash
gcloud run jobs update appointments-migrate --region $REGION \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/backend:v2
```

### Optional: demo data

`app/seed.py` calls `drop_all()` before inserting. Only run it against a database you are
willing to lose entirely.

```bash
gcloud run jobs create appointments-seed \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/backend:v1 \
  --region $REGION \
  --set-secrets="DATABASE_URL=DATABASE_URL:latest" \
  --set-cloudsql-instances=$SQL_CONN_NAME \
  --set-env-vars="TZ=${CLINIC_TZ}" \
  --command python --args "-m,app.seed" \
  --max-retries 0 --task-timeout 5m

gcloud run jobs execute appointments-seed --region $REGION --wait
```

`TZ` matters here too: the seed writes clinic-local wall-clock slot times, so a job
running in UTC would lay down a schedule shifted by the offset.

The seed only creates slots for a `-7 .. +14` day window around the day it runs, and
nothing regenerates them. Roughly two weeks later the booking API goes empty — see
"Next steps".

---

## 8. Deploy the backend to Cloud Run

```bash
gcloud run deploy $BACKEND_SVC \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/backend:v1 \
  --region $REGION \
  --platform managed \
  --port 8080 \
  --memory 2Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 4 \
  --concurrency 20 \
  --timeout 300 \
  --execution-environment gen2 \
  --allow-unauthenticated \
  --set-secrets="DATABASE_URL=DATABASE_URL:latest,NVIDIA_API_KEY=NVIDIA_API_KEY:latest" \
  --set-cloudsql-instances=$SQL_CONN_NAME \
  --set-env-vars="TZ=${CLINIC_TZ},CANCELLATION_WINDOW_MINUTES=60,FRONTEND_ORIGIN=http://localhost:5173"
```

Why these flags, tied to the actual code:

- `TZ=${CLINIC_TZ}` — the whole naive-local-time design in `app/utils.py` rests on this.
  It's also baked into the Dockerfile; setting it here means you can see it in
  `gcloud run services describe` instead of having to read the image.
- `--memory 2Gi` — `chromadb` loads onnxruntime and the HNSW index into RAM. 512Mi is
  enough for FastAPI alone but not with Chroma resident; a too-small limit shows up as the
  container being killed mid-request, not as a clean error.
- `--timeout 300` — `/api/chat` runs a tool-calling loop against NIM, and
  `nvidia_client._client()` allows 30s per HTTP call, so several sequential round trips
  can exceed Cloud Run's 5-minute default. Everything else is a short DB round trip.
- `--concurrency 20` with `--max-instances 4` — 80 in-flight requests against a pool of
  `5 × 4 = 20` Postgres connections (`pool_size=5` in `app/database.py`). Deliberate:
  requests queue on the pool rather than exhausting Cloud SQL's ~25-connection limit on
  `db-f1-micro`. Raise `--max-instances` and you must raise the tier or lower `pool_size`.
- `--min-instances 0` — cold start is the Python process plus the Chroma index load.
  Set to `1` if first-request latency on `/api/symptom-search` bothers you.
- `--port 8080` matches `PORT` in the Dockerfile.
- `FRONTEND_ORIGIN` is a placeholder until step 9.

```bash
export BACKEND_URL=$(gcloud run services describe $BACKEND_SVC --region $REGION \
  --format='value(status.url)')

curl $BACKEND_URL/api/health
curl $BACKEND_URL/api/specialties
```

`/api/health` returns `{"status":"ok"}` without touching the database, so a healthy
`/api/health` alongside a failing `/api/specialties` isolates the problem to the DB
connection rather than the container.

---

## 9. Build and deploy the frontend

`gcloud builds submit --tag` doesn't accept `--build-arg`, and this build needs
`VITE_API_URL`:

```bash
docker build -f frontend/Dockerfile \
  --build-arg VITE_API_URL=$BACKEND_URL \
  -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/frontend:v1 \
  ./frontend

docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/frontend:v1

gcloud run deploy $FRONTEND_SVC \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/frontend:v1 \
  --region $REGION --platform managed --port 8080 \
  --memory 256Mi --cpu 1 --min-instances 0 --max-instances 4 \
  --allow-unauthenticated

export FRONTEND_URL=$(gcloud run services describe $FRONTEND_SVC --region $REGION \
  --format='value(status.url)')
```

`VITE_API_URL` is inlined into the JS bundle at build time — changing the backend URL
means rebuilding and repushing this image. Setting an env var on the running container
does nothing.

No local Docker? Add a `frontend/cloudbuild.yaml` passing the build arg through a
substitution, then `gcloud builds submit --config=cloudbuild.yaml
--substitutions=_VITE_API_URL=$BACKEND_URL ./frontend`.

### Close the CORS loop

`app/main.py` reads its allow-list from `settings.cors_origins`, no wildcard:

```bash
gcloud run services update $BACKEND_SVC \
  --region $REGION \
  --update-env-vars="FRONTEND_ORIGIN=${FRONTEND_URL}"
```

---

## 10. Verify end to end

```bash
curl $BACKEND_URL/api/health
curl $BACKEND_URL/api/specialties
curl $FRONTEND_URL/healthz

# timezone: must be clinic-local, and slot times must look like clinic hours
curl "$BACKEND_URL/api/doctors/1/slots" | head -c 400

# embedding layer survived the build — expect "source":"embedding", not "none"
curl -X POST $BACKEND_URL/api/symptom-search -H "Content-Type: application/json" \
  -d '{"text": "my little one has been running a temperature since last night"}'

# emergency short-circuit — must come back emergency:true with no specialty
curl -X POST $BACKEND_URL/api/symptom-search -H "Content-Type: application/json" \
  -d '{"text": "crushing chest pain and I cant breathe"}'

# NIM reachable from Cloud Run
curl -X POST $BACKEND_URL/api/chat -H "Content-Type: application/json" \
  -d '{"patient_id": 1, "message": "I need to see someone about my knee", "conversation_history": []}'

# CORS preflight — 200 with access-control-allow-origin set
curl -i -X OPTIONS "$BACKEND_URL/api/doctors" \
  -H "Origin: $FRONTEND_URL" -H "Access-Control-Request-Method: GET"
```

---

## Required before real traffic

These are correctness issues, not deployment config. The deploy works without them; the
application is not safe to accept bookings until they're done.

**No authentication anywhere.** `patient_id` arrives in the request body, so any caller
can book as anyone. `PATCH /api/appointments/{id}/cancel` has no ownership check.
`GET /api/patients` returns every patient's name, email and phone. `POST /api/chat` takes
a `patient_id` from the body and acts on that patient's appointments through
`chat_tools`. And `PATCH /api/appointments/{id}/status` — the doctor/admin path that
bypasses the cancellation window — is reachable by anyone. The `--allow-unauthenticated`
flags above put all of that on a public URL. Add auth before deploying publicly, or drop
`--allow-unauthenticated` and front the services with IAP while you build it.

**Postgres loses the double-booking guard.** `book_appointment` relies on SQLite's
`BEGIN IMMEDIATE`, which `app/database.py` correctly skips on Postgres. Under Postgres's
default READ COMMITTED, two concurrent requests can both read the slot as `open`. The
per-slot race is fixed with a row lock:

```python
# app/services/appointments.py — replace `slot = await db.get(Slot, slot_id)`
slot = (
    await db.execute(select(Slot).where(Slot.id == slot_id).with_for_update())
).scalar_one_or_none()
```

The patient-overlap check a few lines below is harder: its own comment says it "relies
entirely on the BEGIN IMMEDIATE transaction lock above for race-safety", and a lock on
*this* slot's row doesn't serialize two requests booking two *different* slots for the
same patient. Either lock the patient row in the same transaction
(`select(Patient).where(Patient.id == patient_id).with_for_update()` — cheap, and the
patient is already fetched), or run booking transactions at
`SERIALIZABLE` isolation and retry on `40001`. `tests/test_booking_race.py` covers the
slot case but only against SQLite — point it at a Postgres test database before trusting
either path in production.

**A cancelled slot can never be rebooked.** `UniqueConstraint("slot_id")` on
`appointments` counts cancelled rows, so cancelling permanently destroys a slot: it
reappears as `open` in the slots list, then 409s on booking with "was just booked by
someone else". Make the constraint partial:

```python
# app/models.py — in Appointment, replace __table_args__
from sqlalchemy import Index, text

__table_args__ = (
    Index("uq_appointments_active_slot", "slot_id", unique=True,
          postgresql_where=text("status != 'cancelled'"),
          sqlite_where=text("status != 'cancelled'")),
)
```

Changing this once tables exist needs a real migration — `create_tables.py` only creates
missing tables, it won't alter an existing one.

**The emergency path has no test.** `symptom_match._check_emergency` is the one branch
where a miss has real-world consequences, and it's pure in-process logic over
`EMERGENCY_RULES` with no network dependency — cheap to test exhaustively. Worth doing
before this is in front of patients.

---

## Updating and rolling back

```bash
# re-embed only if app/taxonomy.py changed
cd backend && python -m app.embed_taxonomy && cd ..

gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/backend:v2 \
  --timeout=20m ./backend

# schema first, if it changed
gcloud run jobs update appointments-migrate --region $REGION \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/backend:v2
gcloud run jobs execute appointments-migrate --region $REGION --wait

gcloud run deploy $BACKEND_SVC \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/backend:v2 --region $REGION
```

Rollback:

```bash
gcloud run revisions list --service $BACKEND_SVC --region $REGION

gcloud run services update-traffic $BACKEND_SVC --region $REGION \
  --to-revisions=APPOINTMENTS-BACKEND-00001-abc=100
```

Rollback reverts the image only. It does not undo a schema change, so a migration that
drops or renames a column breaks the older revision you roll back to. Keep schema changes
additive.

---

## Connecting to the production database

```bash
cloud-sql-proxy $SQL_CONN_NAME &
psql "host=127.0.0.1 port=5432 dbname=$DB_NAME user=$DB_USER"
gcloud secrets versions access latest --secret=DATABASE_URL    # if you lost the password
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Every endpoint 500s, `/api/health` is fine | tables never created | run the step-7 job; `/api/health` doesn't touch the DB |
| `relation "doctors" does not exist` | same as above | same as above |
| Slot times are off by exactly 5h30m | `TZ` not set on the service or job | `--set-env-vars="TZ=Asia/Kolkata"`; `app/utils.py` uses naive local time by design |
| "No slots available" for a day that should have them | same timezone drift, seen through the past-slot filter | as above |
| `/api/symptom-search` always returns `"source":"none"` or `"exact"`, never `"embedding"` | `chroma_data/` empty in the image | run `python -m app.embed_taxonomy`, rebuild; verify with the `count()` check in step 3 |
| `docker build` fails on `COPY chroma_data` | directory doesn't exist locally | it's gitignored — build it in step 2 |
| `/api/chat` 502s | `NVIDIA_API_KEY` secret missing or NIM rate-limiting | check `--set-secrets`; `nvidia_client` raises `NvidiaAPIError`, now mapped to 502 with a log line |
| `/api/chat` times out | tool-calling loop exceeding the service timeout | `--timeout 300`; also check the 30s per-call timeout in `nvidia_client._client()` |
| Container killed mid-request, no error | memory limit too low for Chroma | `--memory 2Gi` |
| `InvalidPasswordError` / auth failed | `DATABASE_URL` secret with an unescaped password | recreate from step 5 verbatim; don't rebuild the URL by hand |
| `connection refused` on `/cloudsql/...` | `--set-cloudsql-instances` missing or SA lacks `roles/cloudsql.client` | re-run both from step 5, redeploy |
| `sorry, too many clients already` | instances × `pool_size` over the tier's limit | lower `--max-instances` or `pool_size`, or raise the tier |
| CORS error in the browser console | `FRONTEND_ORIGIN` still the placeholder | re-run the update at the end of step 9 |
| Frontend calls `localhost:8000` in production | image built without `--build-arg VITE_API_URL` | rebuild and repush; the value is inlined at build time |
| nginx exits immediately | a `proxy_pass` to a `backend` hostname | Cloud Run services don't share a network namespace; `frontend/nginx.conf` is static-only for this reason |
| Cancel then rebook returns 409 | `UniqueConstraint("slot_id")` counts cancelled rows | see "Required before real traffic" |
| Bookings list empty ~2 weeks after seeding | seed only creates slots for `-7..+14` days | needs a slot-generation job; see "Next steps" |

---

## Cost notes

At `--min-instances 0` on both services, Cloud Run is close to free at low traffic — you
pay per request-second. The recurring cost is Cloud SQL: `db-f1-micro` with 10GB runs
roughly $9–12/month in `asia-south1` and cannot scale to zero. NIM usage is billed
separately by NVIDIA and is driven by `/api/chat`, not by `/api/symptom-search` — the
fuzzy layer answers most symptom queries with no API call at all, which is the point of
the layered design in `symptom_match.py`.

`--min-instances 1` on a 2Gi/1vCPU backend adds roughly $25–30/month.

Artifact Registry storage is cents per month, but the backend image is large (chromadb
pulls onnxruntime). Prune old tags with `gcloud artifacts docker images delete` if it
grows.

---

## Next steps

- **Migrations.** `scripts/create_tables.py` is `create_all`: it adds missing tables and
  ignores existing ones, and will not alter a column you change. Add Alembic before the
  schema changes under real data, and swap the step-7 job's args to
  `alembic,upgrade,head`.
- **Slot generation.** `DoctorAvailability` is seeded and never read by anything. Slots
  exist only in the window `app/seed.py` hardcodes. A Cloud Scheduler → Cloud Run Job that
  materializes slots from availability on a rolling 30-day horizon would replace the
  seed's production role.
- **Chroma as a service.** `PersistentClient` baked into the image is right at this size —
  76 phrases, read-only, changes only when `taxonomy.py` does. If the taxonomy grows or
  needs updating without a redeploy, move to `chromadb.HttpClient` against a Chroma server
  on a small Compute Engine VM, or drop Chroma entirely: at this scale the embeddings fit
  in memory and a numpy dot product replaces the whole dependency, which would also take
  the image from ~1.5GB to ~200MB.
- **Observability.** Cloud Run ships stdout to Cloud Logging automatically, and
  `app/main.py` now logs DB and NIM failures. Beyond that there's no request logging and
  no structured fields — `google-cloud-logging`'s structured handler plus a request-ID
  middleware is the usual next step. Worth logging `symptom_match` outcomes by `source`
  too, so a silently-degrading embedding layer shows up as a metric.
- **Secrets rotation.** `gcloud sql users set-password`, then add a new `DATABASE_URL`
  secret version and redeploy — `:latest` is resolved per revision, not on the running one.
