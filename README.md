🎓 Classroom Dashboard + Luminara AI Assistant

A role-aware university management dashboard with a built-in GenAI assistant that answers questions and makes changes using your live data.

Features · Architecture · Quick start · Configuration · AI assistant · API · Deployment


📖 Overview

Classroom Dashboard is a full-stack web app for running the day-to-day of a university: faculties, departments, programmes, subjects, classes, enrollments, rooms and timetables. Five roles — student, lecturer, tutor, admin and technical services — each get a dashboard scoped to what they are allowed to see and do.

Built into every page is Luminara, a GenAI assistant powered by Google Gemini. It has no institution knowledge baked into its prompt. Instead, it calls typed backend tools that run permission-scoped database queries as the signed-in user, so its answers always reflect the live database and never leak data the user couldn't already see. It can also act: enroll a student, schedule a session or find a free room, always after an explicit confirmation step.

✨ Features

University management

Full CRUD for faculties, departments, programmes, subjects, classes, buildings and rooms
Class enrollments by invite code, with a live seats-left count
Timetable scheduling with conflict detection for room, lecturer, tutor and student cohort clashes, backed by Postgres exclusion constraints
In-app notifications with unread counts
Document and image uploads (profile pictures, class banners, registration documents) sent directly from the browser to Cloudinary

Accounts and security

Multi-step registration wizard per role, with an admin approval queue for new accounts
JWT bearer authentication with bcrypt password hashing
Login lockout after repeated failures (HTTP 429 with Retry-After)
Password reset by email with hashed, single-use, expiring tokens
Role-based access control enforced on every endpoint

GenAI assistant (Luminara)

Natural-language questions over live data ("What's on my timetable Thursday?", "Which rooms are free at 2pm?")
Screen-aware: reads the page you're looking at (route, filters, visible table rows) so "summarise this" just works
Tool calling with 14 read tools and 11 write tools, filtered per role before the model ever sees them
Two-phase confirmation on every write, plus transactional commit or rollback
Open tables refresh automatically after the assistant changes something
Degrades gracefully: without an API key, the dashboard still works and the panel shows a "not configured" notice

Operations

GET /health liveness probe and an admin-only GET /api/system/status that reports database, storage, mail and assistant health
One-click deploys via render.yaml (API) and netlify.toml (SPA)
🛠 Tech stack
Layer	Technology
Frontend	React 19, TypeScript, Vite, Refine, React Router 7, Tailwind CSS 4, react-hook-form + Zod, Axios
Backend	FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, PyJWT, bcrypt, Uvicorn
GenAI	Google Gemini via the google-genai SDK (function calling)
Database	PostgreSQL (Neon serverless, pooled connection), btree_gist exclusion constraints
File storage	Cloudinary (signed direct browser uploads)
Email	Any SMTP server (optional)
Hosting	Netlify (frontend) and Render (backend)
🏗 Architecture
REST + JWT
signed upload
function calling
optional
👤 UserBrowser
React SPANetlify CDN
FastAPIRender
Cloudinary
PostgreSQLNeon
Google Gemini
SMTP

The architecture diagram, API sequence diagrams and CI/CD pipeline are documented in detail in docs/ARCHITECTURE.md.

📁 Project structure
classroom-dashboard/
├── client/                      # React + Vite SPA
│   ├── public/_redirects        # SPA fallback for Netlify
│   └── src/
│       ├── components/assistant # Luminara chat panel + markdown renderer
│       ├── hooks/               # use-assistant, use-departments, ...
│       ├── lib/                 # http client, screen-context capture, uploads
│       ├── pages/               # auth, dashboards, classes, subjects, admin
│       └── providers/           # Refine auth + data providers
├── server/                      # FastAPI backend
│   ├── alembic/versions/        # database migrations
│   ├── app/
│   │   ├── ai/                  # assistant runtime, prompt, tool declarations, tools
│   │   ├── api/                 # one router per resource
│   │   ├── core/                # config, security, storage, mail
│   │   ├── db/                  # engine/session + seed data
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response models
│   │   └── services/            # serializers
│   └── tests/                   # standalone check scripts (in-memory SQLite)
├── docs/ARCHITECTURE.md
├── DEPLOYMENT.md
├── netlify.toml
└── render.yaml
🚀 Quick start
Prerequisites
Python 3.12+
Node.js 18+ (22 is used in production)
A PostgreSQL database (Neon, Supabase or local)
A Gemini API key from Google AI Studio — optional, only needed for the assistant
A Cloudinary account — optional, only needed for uploads
1. Clone
bash
git clone https://github.com/<your-username>/classroom-dashboard.git
cd classroom-dashboard
2. Backend
bash
cd server
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\activate
python -m pip install -r requirements.txt

cp .env.example .env               # then fill in the values
python -m alembic upgrade head     # create the schema
python -m app.db.seed              # load demo data
python -m uvicorn app.main:app --reload

The API runs at http://127.0.0.1:8000, with interactive docs at http://127.0.0.1:8000/docs.

💡 Use python -m uvicorn / python -m alembic rather than the bare commands. On Windows, virtual-environment launchers hard-code an absolute path and break if the folder is ever moved or renamed.

3. Frontend

In a second terminal:

bash
cd client
npm install
cp .env.example .env               # VITE_BACKEND_BASE_URL=http://localhost:8000
npm run dev

Open http://localhost:5173. This origin must match FRONTEND_URL in server/.env, or CORS will block every request.

⚙ Configuration

All backend settings live in server/.env (git-ignored). Keep server/.env.example as a template with empty secrets.

Key	Example	Purpose
DATABASE_URL	required	Postgres connection string (use Neon's pooled URL in production)
JWT_SECRET	required	Signing secret for access tokens
JWT_ALGORITHM	HS256	Token algorithm
ACCESS_TOKEN_EXPIRE_MINUTES	10080	Token lifetime (7 days)
FRONTEND_URL	http://localhost:5173	Allowed CORS origin(s), comma-separated
LOGIN_MAX_ATTEMPTS / LOGIN_LOCKOUT_SECONDS	5 / 50	Brute-force lockout policy
CLOUDINARY_CLOUD_NAME / _API_KEY / _API_SECRET	empty	Enables uploads
CLOUDINARY_FOLDER	empty	Optional folder prefix for assets
UPLOAD_MAX_BYTES	10485760	Max upload size (10 MB)
SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD / SMTP_FROM / SMTP_USE_SSL	empty	Password-reset email; if unset, the reset link is written to the server log
PASSWORD_RESET_EXPIRE_MINUTES	30	Reset-link lifetime
GEMINI_API_KEY	empty	Turns the assistant on
GEMINI_MODEL	gemini-3.6-flash	Model used for chat and tool calling
ASSISTANT_NAME	Luminara	Name shown in the chat panel
ASSISTANT_INSTITUTION	Classroom Dashboard	Institution name used in the system prompt
ASSISTANT_MAX_TOOL_TURNS	3	Max tool-calling rounds per question
ASSISTANT_HISTORY_LIMIT	12	Prior messages sent as context

Frontend (client/.env):

Key	Purpose
VITE_BACKEND_BASE_URL	Base URL of the FastAPI server, without /api

⚠️ Settings are cached at startup. --reload only watches .py files, so restart uvicorn after editing .env.

🤖 How the AI assistant works
User question ──► POST /api/assistant/chat
                  │  message + last 12 messages + snapshot of the current screen
                  ▼
        System prompt (role brief + user profile + screen context)
                  ▼
        Gemini ◄──► tool loop (max ASSISTANT_MAX_TOOL_TURNS rounds)
                  │   each tool = scoped SQLAlchemy query run as the signed-in user
                  ▼
        final_answer ──► reply, sources, follow-ups, mutations
                  ▼
        Client refreshes any affected Refine resources

Grounded, not memorised. Every fact comes from a tool call such as list_my_schedule, find_free_rooms or search_people, and each tool applies the same visibility rules as the REST API. A student can't see other students' records through the assistant, because the tool never returns them.

Role-filtered tools. Write tools are filtered by role before they're declared to the model. A student is only offered the handful they can actually use, and the runtime re-checks permission on every call.

Human-in-the-loop writes. Every write tool returns confirmation_required on its first call. The model must describe the change, get a "yes", then call again with confirmed=true. The database transaction commits only when a mutation actually succeeds; everything else rolls back.

Same rules as the API. find_free_rooms, create_schedule and update_schedule share the overlap query used by POST /api/schedules, and the Postgres exclusion constraints remain the final guard.

Screen awareness. client/src/lib/assistant-context.ts snapshots the route, page heading, active filters, pagination, up to 25 visible table rows and detail-view fields on every message, so "explain this one" resolves against what's actually on screen.

<details> <summary><b>Available tools</b></summary>

Read: get_my_profile, get_dashboard_overview, list_my_classes, list_my_schedule, get_class, list_class_roster, search_classes, search_subjects, list_departments, list_programmes, search_people, list_rooms, find_free_rooms, list_my_notifications

Write: join_class_by_invite_code, enroll_student, remove_enrollment, create_class, update_class, create_schedule, update_schedule, cancel_schedule, mark_notifications_read, create_subject, update_my_profile

</details> <details> <summary><b>Choosing a Gemini model</b></summary>

Google retires older models for accounts that never used them, so a model name that works on one key can return 404 on another. List the models your key can call:

bash
python -c "from google import genai; from app.core.config import settings; c=genai.Client(api_key=settings.GEMINI_API_KEY); [print(m.name) for m in c.models.list() if 'generateContent' in (m.supported_actions or [])]"

The free tier allows roughly 5 requests per minute per model, and one question can use one request per tool round. Keep ASSISTANT_MAX_TOOL_TURNS at 3 or lower on the free tier.

</details>
🔌 API overview

All endpoints are under /api and, apart from registration, login and password reset, require Authorization: Bearer <token>. List endpoints return { data, pagination }; single-item endpoints return { data }.

Area	Endpoints
Auth	POST /auth/register/{student|lecturer|tutor|admin|technical-services}, POST /auth/login, GET /auth/me, POST /auth/forgot-password, POST /auth/reset-password, POST /auth/change-password
Users	GET /users, GET|PATCH /users/me, GET|PATCH|DELETE /users/{id}, GET /users/pending-count, POST /users/{id}/approve, POST /users/{id}/reject
Academic structure	GET|POST and GET|PATCH|DELETE /{id} on /faculties, /departments, /programmes, /subjects
Classes	GET|POST /classes, GET|PATCH|DELETE /classes/{id}
Enrollments	GET|POST /enrollments, POST /enrollments/join, DELETE /enrollments/{id}
Facilities	GET|POST and GET|PATCH|DELETE /{id} on /buildings, /rooms
Schedules	GET|POST /schedules, GET|PATCH|DELETE /schedules/{id}
Notifications	GET|POST /notifications, GET /notifications/unread-count, POST /notifications/read-all, PATCH|DELETE /notifications/{id}
Files	GET|POST /documents, POST /uploads, POST /uploads/presign
Dashboard	GET /stats/overview, GET /meta/registration-options
System	GET /system/status (admin), GET /health (no prefix)
Assistant	GET /assistant/status, POST /assistant/chat

Full request and response schemas are available in Swagger UI at /docs.

🧪 Testing

The backend ships with standalone check scripts that run against a throwaway in-memory SQLite database, so they never touch your real data:

bash
cd server
PYTHONPATH=. python tests/check_auth_uploads.py
PYTHONPATH=. python tests/check_password_reset.py
PYTHONPATH=. python tests/check_cohort_conflicts.py
PYTHONPATH=. python tests/check_admin_approvals.py

A non-empty DATABASE_URL must be set because settings are validated at import time, but it is never connected to.

Frontend checks:

bash
cd client
npm run lint
npm run build   # runs tsc type-checking, then the Vite build
☁ Deployment
Component	Platform	Config
API	Render (Python web service)	render.yaml
SPA	Netlify	netlify.toml
Database	Neon Postgres	pooled connection string
Files	Cloudinary	API credentials on Render only

Both platforms auto-deploy on push to main. Migrations are run manually before a deploy. See DEPLOYMENT.md for the step-by-step guide and docs/ARCHITECTURE.md for the pipeline diagram.

On the free tiers, Render sleeps after ~15 minutes idle and Neon scales to zero, so the first request after a pause can take 50 seconds or more.

🩺 Troubleshooting
Symptom	Cause and fix
"The configured assistant model is unavailable."	Gemini returned 404. Your GEMINI_MODEL isn't available to this key; list models and pick another.
"The assistant is handling too many requests right now."	Gemini rate limit (429). Wait, lower ASSISTANT_MAX_TOOL_TURNS, or enable billing.
"The assistant could not authenticate."	Check GEMINI_API_KEY.
"The assistant could not complete that request."	See the uvicorn log for Assistant conversation failed.
CORS errors in the browser	FRONTEND_URL doesn't exactly match the frontend origin (no trailing slash).
ModuleNotFoundError: No module named 'app'	Run backend commands from server/, not from inside app/.
404 on refresh of a nested route in production	client/public/_redirects is missing from the build.
🔒 Security
Never commit server/.env. It holds the database password, JWT secret and API keys. If any have been exposed, rotate them.
Cloudinary's API secret stays on the server. The browser only ever receives a short-lived signature.
Password-reset tokens are stored hashed, expire, and are invalidated after use.
The assistant cannot bypass role checks: tools run as the signed-in user and every write requires explicit confirmation.
🤝 Contributing
Fork the repo and create a branch: git checkout -b feature/my-change
Add an Alembic migration for any model change: python -m alembic revision --autogenerate -m "describe change"
Run the backend check scripts plus npm run lint and npm run build
Open a pull request against main describing what changed and why
📄 License

No license has been chosen yet. Add a LICENSE file (MIT is a common choice) before accepting outside contributions.
