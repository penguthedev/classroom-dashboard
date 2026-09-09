# Project 2 — Classroom Management Dashboard

**Team:** 2 people (1 backend, 1 frontend) · one shared repo
**Target:** 1 week · **Stack:** FastAPI + PostgreSQL (Neon) + React
**Deploy:** Netlify (frontend) · Render (backend)

---

## 1. What you're building

A university classroom management dashboard — think Google Classroom's admin side.

Departments contain subjects. Subjects have classes. Classes have a teacher, a capacity, a banner image and an invite code. Students enroll in classes using that code. Three roles: `student`, `teacher`, `admin`.

You'll follow this course for the **frontend**:

> **Full Stack Engineering Course — Build and Deploy a Full Stack PERN Admin Dashboard in 2026** (JavaScript Mastery, 7h53m)
> https://www.youtube.com/watch?v=ek7hmv5PVV8

**Important:** the video builds the backend in Node/Express. **Ignore all of that.** You are writing the backend in FastAPI, against the API contract in section 5 of this document. The video's frontend is what you're following.

Useful chapters:
- `1:45:40` Project demo — what the finished thing looks like
- `1:55:42`–`2:53:33` Frontend setup, routes, Refine data provider, subjects list
- `4:13:34` Create class form (react-hook-form + Zod)
- `4:35:57` Cloudinary integration
- `6:45:48` Class details page

> ⚠️ The demo at `1:45:40` is the **finished, AI-completed** app running on a deployed URL. The version built by hand in the video is smaller than that. Don't measure yourselves against the intro demo.

---

## 2. Stack

| Layer | Use this | Notes |
|---|---|---|
| Frontend | React + Vite + TypeScript | Same as project 1 |
| Admin framework | **Refine Core** | New. Handles tables, filters, pagination |
| UI | shadcn/ui + Tailwind | New |
| Forms | react-hook-form + Zod | |
| Backend | **FastAPI** | |
| ORM | **SQLAlchemy 2.0** | |
| Migrations | **Alembic** | Required — not `create_all()` |
| Validation | **Pydantic v2** | Every request body gets a model |
| Database | **PostgreSQL on Neon** | New — this is not SQLite |
| Auth | **JWT**, hand-rolled | Video uses Better Auth (TS-only) — ignore it |
| Images | **Cloudinary** | New — see section 8 |

### What's genuinely new for you

Postgres, Alembic, Refine, shadcn, Cloudinary. That's a lot in a week — read section 11 before you start, it lists the things that will waste your time if you don't know them in advance.

---

## 3. Ground rules

These come from reviewing your restaurant projects. Non-negotiable this time.

1. **`.gitignore` first, before the first commit.** `node_modules/`, `.venv/`, `__pycache__/`, `.env`, `*.db`. Both previous repos committed `node_modules` — hundreds of megabytes of noise that makes every diff unreviewable.
2. **No secrets or credentials in source.** No hardcoded database URLs, no default admin passwords in `config.py`. Everything through environment variables via `pydantic-settings`, with a committed `.env.example` listing the keys and no values.
3. **Alembic from day one.** No `SQLModel.metadata.create_all()`. Every schema change is a migration with a message.
4. **Use the backend layout in section 4.** It's the structure from `Noviem52/restaurant_booking_project` — the better of the two — so standardise on it.
5. **Push daily.** Every feature on a branch, opened as a PR, merged after review. Don't commit to `main`.

---

## 4. Repo layout

One repo, two top-level folders.

```
classroom-dashboard/
├── client/                     # React + Vite + Refine
│   ├── src/
│   │   ├── components/
│   │   ├── pages/              # dashboard, subjects, departments, classes, auth
│   │   ├── providers/          # data.ts, auth.ts  ← the Refine seam
│   │   ├── lib/                # schema.ts (Zod), cloudinary.ts
│   │   ├── types/
│   │   └── constants/
│   ├── .env.example
│   └── public/_redirects       # Netlify SPA routing — see section 10
│
└── server/                     # FastAPI
    ├── alembic/
    │   └── versions/
    ├── app/
    │   ├── api/                # departments.py, subjects.py, classes.py,
    │   │                       # users.py, enrollments.py, auth.py, deps.py
    │   ├── core/               # config.py, security.py
    │   ├── db/                 # session.py, base.py, seed.py
    │   ├── models/             # SQLAlchemy models
    │   ├── schemas/            # Pydantic models
    │   └── main.py
    ├── alembic.ini
    ├── requirements.txt
    └── .env.example
```

---

## 5. The API contract ⭐

**This is the most important section in this document.**

The frontend uses Refine's REST data provider. It expects an exact response shape. If the backend doesn't match it, every page renders empty with no useful error message — and you'll lose half a day to it.

**Agree this on day one, before either of you writes code.** Once the backend is running, FastAPI's auto-generated docs at `/docs` become the shared source of truth. That's a real advantage over the video, which has to hand-write a Swagger file.

### List

```http
GET /api/{resource}?page=1&limit=10&search=<text>&department=<name>
```
```json
{
  "data": [ { "...": "..." } ],
  "pagination": { "page": 1, "limit": 10, "total": 42, "totalPages": 5 }
}
```

### Single

```http
GET /api/{resource}/{id}
```
```json
{ "data": { "...": "..." } }
```

### Create / Update / Delete

```http
POST   /api/{resource}        → 201  { "data": { ... } }
PATCH  /api/{resource}/{id}   → 200  { "data": { ... } }
DELETE /api/{resource}/{id}   → 204
```

Resources: `departments`, `subjects`, `classes`, `users`, `enrollments`.

### Nested objects matter

Related data must be **embedded as objects**, not flat IDs. The frontend reads `department.name`, not `department`. This is what the SQL joins are for.

**Subject row:**
```json
{
  "id": 1, "code": "CS101", "name": "Intro to Programming",
  "description": "Python basics and computational thinking.",
  "department_id": 1,
  "department": { "id": 1, "code": "CS", "name": "Computer Science", "description": "..." },
  "created_at": "2026-01-13T10:00:00Z", "updated_at": "2026-01-13T10:00:00Z"
}
```

**Class row:**
```json
{
  "id": 1, "name": "Python Foundations - Section A",
  "description": "Intro to programming, focus on Python syntax.",
  "capacity": 30, "status": "active",
  "banner_url": "https://res.cloudinary.com/...",
  "banner_cld_pub_id": "uploads/abc123",
  "invite_code": "a7f3k9",
  "subject_id": 1, "teacher_id": 2,
  "subject":    { "id": 1, "code": "CS101", "name": "Intro to Programming", "description": "..." },
  "teacher":    { "id": 2, "name": "Tom Ellis", "email": "tom@teacher.com", "image_url": null },
  "department": { "id": 1, "code": "CS", "name": "Computer Science" },
  "created_at": "...", "updated_at": "..."
}
```

### Query parameters

- `page` (default 1), `limit` (default 10) → translate to `LIMIT` / `OFFSET`
- `search` → case-insensitive partial match on the resource's `name` **or** `code` (use `ILIKE`)
- `department` → filter by department **name** (used by the subjects page)
- `subject` / `teacher` → filter classes

Validate all of these with Pydantic. Never interpolate them into SQL by hand.

---

## 6. Database schema

Everything gets `id` (PK, auto-increment), `created_at`, `updated_at`.

**`departments`** — `code` varchar(50) unique not null · `name` varchar(255) not null · `description` text nullable

**`subjects`** — `department_id` FK → `departments.id`, not null, `ON DELETE RESTRICT` · `code` varchar(50) unique not null · `name` varchar(255) not null · `description` text

**`users`** — `name` not null · `email` unique not null · `password_hash` not null · `role` enum(`student`,`teacher`,`admin`) default `student` · `image_url` nullable · `image_cld_pub_id` nullable

**`classes`** — `name` not null · `description` text · `subject_id` FK → `subjects.id` not null · `teacher_id` FK → `users.id` not null · `capacity` int not null · `status` enum(`active`,`archived`) default `active` · `banner_url` · `banner_cld_pub_id` · `invite_code` varchar unique not null

**`enrollments`** — `student_id` FK → `users.id` · `class_id` FK → `classes.id` · `enrolled_at` · **`UNIQUE(student_id, class_id)`**

### Two modelling points to understand, not just copy

**Departments are entities, not strings.** Don't store `department = "Computer Science"` on every subject row. If the name changes you'd have to update every row, and you can't attach anything else to a department. Give it its own table and reference it.

**Enrollments need their own table.** Don't put a `student_ids` array on `classes`. One student takes many classes and one class has many students — that's many-to-many, and it needs a join table. The `UNIQUE(student_id, class_id)` constraint is what stops a student enrolling twice; enforce it in the database, not in Python.

Seed at least 4 departments, 10 subjects, 4 teachers and 6 students so pagination and filtering are actually testable. Put it in `app/db/seed.py`.

---

## 7. Authentication (JWT)

Hand-rolled. Do not use Better Auth — it's TypeScript-only, which is why the video's approach doesn't transfer.

### Endpoints

```http
POST /api/auth/register   { name, email, password, role }  → 201 { data: { user, access_token } }
POST /api/auth/login      { email, password }              → 200 { data: { user, access_token } }
GET  /api/auth/me                                          → 200 { data: user }
```

### Backend

- Hash with **bcrypt** (`passlib[bcrypt]`). Never store or log a plaintext password.
- Sign with **HS256**, secret from `JWT_SECRET` env var. Expiry 7 days. Access token only — no refresh tokens, keep it simple.
- Payload: `sub` (user id), `role`, `exp`.
- Use `OAuth2PasswordBearer` + a `get_current_user` dependency in `app/api/deps.py`.
- Add a `require_role("teacher", "admin")` dependency for protected writes.

### Permissions

| Action | Who |
|---|---|
| Read anything | any authenticated user |
| Create/edit departments, subjects | teacher, admin |
| Create/edit classes | teacher, admin |
| Enroll in a class | student |
| Manage users | admin |

### Frontend

The video has **no hand-built auth pages** — Better Auth is configured on the backend and tested with an HTTP client, and the login screens only appear in the AI-generated section at the end. So you're building this yourself:

1. Sign-in and sign-up pages (sign-up includes a role selector)
2. A Refine **`authProvider`** in `src/providers/auth.ts` implementing `login`, `logout`, `check`, `getIdentity`, `getPermissions`, `onError`
3. Store the token in `localStorage`; attach `Authorization: Bearer <token>` to every request in the data provider
4. Protected routes — unauthenticated users get bounced to `/login`

---

## 8. Image uploads (Cloudinary)

### Why this changed from project 1

Both restaurant projects saved uploads to the server's local disk (`server/uploads/`) and served them with `StaticFiles`. **That is broken on Render.** The filesystem is ephemeral — every deploy, restart or idle spin-down wipes it. If those apps are still live, the uploaded images are already gone.

Cloudinary fixes it: the file never touches your server.

### How it works

1. Create a Cloudinary account and an **unsigned** upload preset.
2. The browser uploads **directly to Cloudinary** using their upload widget (video at `4:35:57`). Your backend never receives the file.
3. Cloudinary returns a `secure_url` and a `public_id`.
4. Those two strings are what you POST to your API and store in `classes.banner_url` / `classes.banner_cld_pub_id`.
5. Render the banner with `@cloudinary/react`'s `AdvancedImage` plus `@cloudinary/url-gen` transformations — resize, `format: auto`, `quality: auto`, and a text overlay of the class name.

Frontend env vars: `VITE_CLOUDINARY_CLOUD_NAME`, `VITE_CLOUDINARY_UPLOAD_PRESET`.

> Note: the video initially sets the preset to **signed** and the upload silently fails. It has to be **unsigned** for browser-side uploads. He hits this at ~`4:58:00`.

---

## 9. Milestones

Target is one week. Realistically the **must-have** tier is the week; the rest is what you keep going on. Get to a deployed, working app early — don't leave deployment to the last day.

### Day 0 — Setup *(both, together)*
- Repo created, `.gitignore` correct, both folders scaffolded
- **Agree the API contract in section 5 out loud.** Write down the exact JSON shapes
- Neon project created, connection string in `server/.env`
- Frontend scaffolded via Refine CLI (video `1:55:42`) — choose Vite, REST API, shadcn/ui

### M1 — Schema + read endpoints — **must-have**
- Backend: all 5 tables as SQLAlchemy models, first Alembic migration applied to Neon, seed script run
- Backend: `GET /api/departments`, `GET /api/subjects` with pagination, `search`, `department` filter, and the nested `department` object
- Frontend: Refine app running, sidebar + routes, subjects list page rendering from the real API

✅ **Done when:** the subjects table on the frontend shows seeded data from Neon with working search, department filter and pagination.

### M2 — Classes + joins — **must-have**
- Backend: `GET /api/classes` joining subjects → departments → users, with `search`, `subject`, `teacher` filters
- Backend: `GET /api/classes/{id}` returning the full nested class detail
- Frontend: classes list page, class details page (video `6:45:48`)

✅ **Done when:** you can click a class from the list and see its teacher, subject and department on a details page.

### M3 — Auth — **must-have**
- Backend: register / login / me, bcrypt hashing, JWT, `get_current_user`, `require_role`
- Frontend: sign-in + sign-up pages, `authProvider`, protected routes, token attached to requests

✅ **Done when:** you can register as a teacher, log in, and an unauthenticated visitor is redirected to `/login`.

### M4 — Writes + Cloudinary — **must-have**
- Backend: `POST /api/classes` — **validated with a Pydantic model**, teacher/admin only. Verify `subject_id` and `teacher_id` actually exist before inserting. Generate the `invite_code`
- Backend: `POST /api/departments`, `POST /api/subjects`
- Frontend: create-class form with react-hook-form + Zod, Cloudinary upload widget wired in

✅ **Done when:** you can create a class with a banner image through the UI and see the row in Neon with a Cloudinary URL.

### M5 — Deploy — **must-have**
- Backend to Render, frontend to Netlify, both talking to each other in production
- See section 10 — do this before M6, not after

✅ **Done when:** a public Netlify URL loads real data from your Render backend, and page refresh doesn't 404.

### M6 — Enrollments + invite codes — *nice-to-have*
- `POST /api/enrollments` with the unique constraint enforced and a clean 409 on duplicates
- Join-by-code flow on the class details page
- Enrollments list page

### M7 — Polish — *nice-to-have*
- Dashboard with real counts (users, teachers, subjects, departments, classes) and a role breakdown chart
- Faculty directory page with search and pagination
- Theme switching via [tweakcn](https://tweakcn.com) (video `2:00:28`)

### M8 — Production hardening — *stretch, only if everything above is done*
- **Arcjet** rate limiting and bot detection (Python SDK, FastAPI support — it's in beta)
- **Site24x7** APM (`pip install apminsight`, launch via `apminsight-run`) — works on Render because it's a long-running process

---

## 10. Deployment

### Backend → Render
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Env vars: `DATABASE_URL`, `JWT_SECRET`, `FRONTEND_URL`
- Use Neon's **pooled** connection string (the host contains `-pooler`). The direct one will exhaust connections.
- Run Alembic migrations from your machine or as a build step — **never from inside the app**.

### Frontend → Netlify
- Build: `npm run build` · Publish directory: `dist`
- Env vars: `VITE_BACKEND_BASE_URL`, `VITE_CLOUDINARY_CLOUD_NAME`, `VITE_CLOUDINARY_UPLOAD_PRESET`
- **Create `client/public/_redirects`** containing exactly:
  ```
  /*    /index.html   200
  ```
  Without this, refreshing on `/classes` gives a 404. It's the Netlify equivalent of the `vercel.json` rewrite at video `6:29:27`.

### The ordering trap
CORS is circular: the backend needs the frontend's URL and vice versa. Sequence:
1. Deploy backend → get the Render URL
2. Set `VITE_BACKEND_BASE_URL` on Netlify → deploy frontend → get the Netlify URL
3. Set `FRONTEND_URL` on Render → **redeploy the backend**

Use the main Netlify domain, not a deploy-preview URL, and no trailing slash.

---

## 11. Things that will waste your time — read before you start

Ordered by how likely they are to bite.

1. **`connect_args={"check_same_thread": False}` is SQLite-only.** Both your previous projects have it. It will throw on Postgres. Delete it.
2. **You need a Postgres driver.** Neither previous `requirements.txt` had one. Add `psycopg[binary]`.
3. **The response envelope must match section 5 exactly.** Wrong shape = empty tables, no error. Check `/docs` against the contract before blaming the frontend.
4. **Refine reads nested keys.** The subjects table column is `department.name`, not `department`. If you return a flat string, the cell is blank.
5. **Render free tier spins down after ~15 min idle.** The first request then takes 50+ seconds. This is not a bug — don't debug it.
6. **Neon free tier also scales to zero.** Same symptom, same non-bug.
7. **Cloudinary preset must be `unsigned`** for browser uploads, or they fail silently.
8. **Never `**request.body` straight into an insert.** The video does exactly this for `POST /classes` and says out loud that it's exploitable. Use a Pydantic model and verify foreign keys exist.
9. **Don't commit `.env` or `node_modules`.** Check `git status` before your first push.
10. **Alembic autogenerate misses things** — enum changes and constraints especially. Read every generated migration before applying it.

---

## 12. Definition of done

- [ ] Public Netlify URL loads and works end to end
- [ ] Register, log in, log out all work; protected routes redirect
- [ ] Departments, subjects and classes lists all paginate, search and filter **server-side**
- [ ] A class can be created with a Cloudinary banner, and it persists across a backend redeploy
- [ ] Class details page shows teacher, subject and department
- [ ] `/docs` matches the contract in section 5
- [ ] All schema changes are Alembic migrations
- [ ] No secrets, no `node_modules`, no `.db` files in the repo
- [ ] `README.md` explains how to run both halves locally
- [ ] Every feature went through a PR

---

## 13. Working agreement

You're splitting backend and frontend, but the API contract is shared. Rules:

- **Neither of you changes the contract alone.** If it needs to change, agree it and update this document.
- The backend person should get `/docs` live on day 1 so the frontend has something to read.
- Frontend: don't wait for real endpoints. Build against Refine's mock data provider (video `2:39:32`) and swap in the REST provider when M1 lands.
- Daily push, even if incomplete. `wip:` prefix is fine.
- Branch names: `feat/subjects-list`, `fix/cors-origin`.
- If you're stuck more than 2 hours, ask. Don't burn an evening on a CORS error.

---

## 14. Links

- Course — https://www.youtube.com/watch?v=ek7hmv5PVV8
- Refine docs — https://refine.dev/docs/
- FastAPI security tutorial — https://fastapi.tiangolo.com/tutorial/security/
- SQLAlchemy 2.0 ORM — https://docs.sqlalchemy.org/en/20/orm/
- Alembic — https://alembic.sqlalchemy.org/
- Neon — https://neon.tech
- Cloudinary upload widget — https://cloudinary.com/documentation/upload_widget
- shadcn/ui — https://ui.shadcn.com
- tweakcn themes — https://tweakcn.com
