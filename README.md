# Classroom Dashboard + AI Assistant

The AI assistant has been merged into this repository. The separate Node/Express service and
its sample fixtures are gone; the assistant now runs inside the FastAPI backend and reads the
live Postgres database seeded from `app/db/seed.py`.

**Stack:** FastAPI + SQLAlchemy + Alembic + Postgres (Neon) on the backend, React + Refine +
Vite on the frontend, Google Gemini for the assistant.

---

## Prerequisites

- Python 3.12+ (3.14 works)
- Node.js 18+
- A Postgres database (Neon, Supabase or local)
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

---

## Backend setup

From the repository root:

```powershell
cd server

# create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\activate          # Windows PowerShell
# source .venv/bin/activate       # macOS / Linux

python -m pip install -r requirements.txt
```

Copy `server/.env.example` to `server/.env` and fill in your own values — see the settings
table below. `.env` is git-ignored; `.env.example` must stay empty.
Then create the schema and load seed data:

```powershell
python -m alembic upgrade head
python -c "from app.db.seed import seed; seed()"
```

Start the API:

```powershell
python -m uvicorn app.main:app --reload
```

It serves on `http://127.0.0.1:8000`. Interactive docs at `http://127.0.0.1:8000/docs`.

> **Use `python -m uvicorn`, not bare `uvicorn`.** Windows virtual environments hard-code an
> absolute path inside `.venv\Scripts\*.exe`. If the project folder is ever renamed or moved,
> every launcher breaks with *"Fatal error in launcher: Unable to create process"*. Going
> through `python -m` sidesteps the launcher entirely. The same applies to `alembic` and `pip`.
> To fix the launchers properly, delete `.venv` and rebuild it from scratch.

---

## Frontend setup

In a second terminal:

```powershell
cd client
npm install
npm run dev
```

Vite serves on `http://localhost:5173`, which must match `FRONTEND_URL` in `server/.env` or
CORS will block every request.

---

## Configuration

All backend settings live in `server/.env`. Never commit this file — keep `.env.example` as a
template with **empty** values.

| Key | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | *required* | Postgres connection string |
| `JWT_SECRET` | *required* | Signing secret for access tokens |
| `JWT_ALGORITHM` | `HS256` | Token algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` | Token lifetime (7 days) |
| `FRONTEND_URL` | `http://localhost:5173` | Allowed CORS origin; comma-separate for several |
| `GEMINI_API_KEY` | empty | Turns the assistant on |
| `GEMINI_MODEL` | `gemini-3.6-flash` | Model used for chat and tool calling |
| `ASSISTANT_NAME` | `Luminara` | Name shown in the panel header |
| `ASSISTANT_INSTITUTION` | `Classroom Dashboard` | Institution name used in the system prompt |
| `ASSISTANT_MAX_TOOL_TURNS` | `3` | Tool-calling rounds before the loop gives up |
| `ASSISTANT_HISTORY_LIMIT` | `12` | Prior messages sent as context |
| `LOGIN_MAX_ATTEMPTS` | `5` | Failed logins before lockout |
| `LOGIN_LOCKOUT_SECONDS` | `50` | Lockout duration |
| `CLOUDINARY_CLOUD_NAME` / `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET` | empty | Cloudinary credentials for banners, profile pictures and documents |
| `CLOUDINARY_FOLDER` | empty | Optional folder prefix for every uploaded asset |

Without `GEMINI_API_KEY` the dashboard works normally and the assistant panel shows a
"not configured" notice instead of failing.

### Choosing a model

Google retires older models for accounts that never used them, so a model name that works on
one key returns `404 NOT_FOUND` on another. List what your key can actually call:

```powershell
python -c "from google import genai; from app.core.config import settings; c=genai.Client(api_key=settings.GEMINI_API_KEY); [print(m.name) for m in c.models.list() if 'generateContent' in (m.supported_actions or [])]"
```

Pick any `flash` model from that output and set it as `GEMINI_MODEL`.

### Rate limits

The Gemini free tier allows roughly **5 requests per minute per model**. One assistant question
can cost several requests, because `run_conversation` calls the API once per tool-calling round
— up to `ASSISTANT_MAX_TOOL_TURNS`. Keep that value at 3 or lower on the free tier, or enable
billing on the Google Cloud project behind the key for much higher limits.

> `.env` is read once at startup and cached by `@lru_cache` on `get_settings()`. Editing it does
> **not** trigger the `--reload` watcher, which only watches `.py` files. Stop and restart
> uvicorn after any `.env` change.

---

## How the assistant gets its data

It has no institution knowledge baked into the prompt. Every fact comes from a tool call that
runs a scoped SQLAlchemy query as the signed-in user:

- **Reads** — `get_my_profile`, `get_dashboard_overview`, `list_my_classes`, `list_my_schedule`,
  `get_class`, `list_class_roster`, `search_classes`, `search_subjects`, `list_departments`,
  `list_programmes`, `search_people`, `list_rooms`, `find_free_rooms`, `list_my_notifications`
- **Writes** — `join_class_by_invite_code`, `enroll_student`, `remove_enrollment`, `create_class`,
  `update_class`, `create_schedule`, `update_schedule`, `cancel_schedule`,
  `mark_notifications_read`, `create_subject`, `update_my_profile`

Write tools are filtered per role before they are ever shown to the model, so a student is only
offered the four they can actually use. Each one returns `confirmation_required` on its first
call: the model has to relay the change, get a yes, then call again with `confirmed=true`.
Nothing commits unless a mutation actually succeeded.

`find_free_rooms`, `create_schedule` and `update_schedule` share the overlap query used by
`POST /api/schedules`, so the assistant reports the same clashes the REST API would reject, and
the Postgres exclusion constraints from migration `c3f6e4d9a0b5` remain the final guard.

## Reading the screen

`client/src/lib/assistant-context.ts` snapshots the rendered page on each message: route, page
heading, resource, active Refine filters, pagination, up to 25 table rows with their headers,
and any detail-view `dl` pairs. That goes to the backend as `context` and is rendered into the
system prompt, so "summarise what I'm looking at" or "explain this one" resolves against the
actual screen. No page component was modified to make this work.

When a write succeeds, the response lists the touched resources and the client calls Refine's
`useInvalidate`, so open tables refresh on their own.

---

## Troubleshooting

`app/api/assistant.py` maps upstream failures to distinct messages, so the panel usually tells
you which one you hit.

**"The configured assistant model is unavailable."**
Upstream `404`. Google retired your `GEMINI_MODEL` for this account. Run the model-listing
command above and pick another.

**"The assistant is handling too many requests right now."**
Upstream `429`. Free-tier rate limit. Wait a few seconds, lower `ASSISTANT_MAX_TOOL_TURNS`, or
enable billing on the project.

**"The assistant could not authenticate."**
Upstream `401`/`403`. Check `GEMINI_API_KEY`. Google now issues keys with an `AQ.` prefix rather
than the older `AIza`; both work against the native endpoint used here, but some accounts are
restricted. Confirm with a cheap `client.models.list()` call before blaming anything else.

**"The assistant could not complete that request."**
Anything else. The full traceback is printed to the uvicorn terminal by `logger.exception` —
look for `Assistant conversation failed`.

**`ModuleNotFoundError: No module named 'app'`**
You are running from the wrong directory. All backend commands run from `server/`, the folder
that contains `app/`, not from inside `app/`.

**"Fatal error in launcher: Unable to create process"**
The `.venv` was built under a different folder path. Use `python -m <tool>` or rebuild the venv.

**Department dropdown crashes on registration**
See the known client mismatches below.

---

## API surface

```
POST   /api/auth/register/{student|lecturer|tutor|admin|technical-services}
POST   /api/auth/login
GET    /api/auth/me
GET    /api/users, GET|PATCH|DELETE /api/users/{id}
GET|POST /api/faculties, /api/departments, /api/programmes, /api/subjects
GET|PATCH|DELETE the same by id
GET|POST /api/classes, GET|PATCH|DELETE /api/classes/{id}
GET|POST /api/enrollments, POST /api/enrollments/join, DELETE /api/enrollments/{id}
GET|POST /api/buildings, /api/rooms
GET|POST /api/schedules, GET|PATCH|DELETE /api/schedules/{id}
GET|POST /api/notifications, GET /api/notifications/unread-count, POST /api/notifications/read-all
GET|POST /api/documents, POST /api/uploads, POST /api/uploads/presign
GET    /api/stats/overview
GET    /api/assistant/status
POST   /api/assistant/chat
```

---

## Client / server contract

Two mismatches that used to exist have been corrected in this tree:

1. `src/hooks/use-departments.ts` now unwraps `{ data, pagination }` from
   `GET /api/departments` instead of assigning the envelope straight to state.
2. `src/providers/auth.ts` now checks for HTTP **429** on login lockout, which is what the
   backend actually returns, so the countdown renders.

## Note on field names

`src/types/index.ts` and the page components expect `full_name`, `id_code`, `phone_number`,
`profile_picture_url` and the role `technical_services`. The server models store `name`, `phone`,
`image_url` and the role `technical`. The API translates at the schema boundary using
`serialization_alias` and a role map, so responses match the client exactly with no migration and
no client edits.

---

## Security note

`.env` holds a live database password, a JWT signing secret and an API key. Keep it out of
version control, and make sure `.env.example` contains only empty placeholders. If any of these
have been committed or shared, rotate them.
