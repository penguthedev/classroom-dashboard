# Architecture

This document explains how Classroom Dashboard is put together: the system architecture, how requests flow through the API (including the GenAI assistant), and how code gets from a commit to production.

All diagrams are written in [Mermaid](https://mermaid.js.org/) and render natively on GitHub.

**Contents**

1. [System architecture](#1-system-architecture)
2. [Backend internals](#2-backend-internals)
3. [API sequence diagrams](#3-api-sequence-diagrams)
   - [3.1 Login and authenticated requests](#31-login-and-authenticated-requests)
   - [3.2 AI assistant chat with tool calling](#32-ai-assistant-chat-with-tool-calling)
   - [3.3 Assistant write with two-phase confirmation](#33-assistant-write-with-two-phase-confirmation)
   - [3.4 Direct-to-Cloudinary file upload](#34-direct-to-cloudinary-file-upload)
4. [CI/CD pipeline](#4-cicd-pipeline)
5. [Key design decisions](#5-key-design-decisions)

---

## 1. System architecture

```mermaid
flowchart TB
    subgraph Client["🖥️ Client tier — Netlify CDN"]
        direction TB
        SPA["React 19 SPA<br/>Vite + Refine + Tailwind"]
        Panel["Luminara assistant panel"]
        Ctx["assistant-context.ts<br/>screen snapshot"]
        Panel --> Ctx
    end

    subgraph Server["⚙️ Application tier — Render"]
        direction TB
        CORS["CORS middleware"]
        Routers["FastAPI routers<br/>auth · users · classes · schedules<br/>enrollments · rooms · uploads · ..."]
        Deps["deps.py<br/>JWT decode · role guards"]
        AI["ai/ package<br/>runtime · prompt · declarations · tools"]
        ORM["SQLAlchemy 2 ORM"]
        Storage["core/storage.py"]
        Mail["core/mail.py"]
        CORS --> Routers --> Deps
        Routers --> ORM
        Routers --> AI
        AI --> ORM
        Routers --> Storage
        Routers --> Mail
    end

    subgraph Data["🗄️ Data tier"]
        PG[("PostgreSQL — Neon<br/>pooled connection<br/>Alembic migrations")]
    end

    subgraph External["☁️ External services"]
        Gemini["Google Gemini API<br/>function calling"]
        Cloud[("Cloudinary<br/>images + documents")]
        SMTP["SMTP server<br/>optional"]
    end

    User(["👤 Student · Lecturer · Tutor<br/>Admin · Technical services"]) --> SPA
    SPA -- "HTTPS REST + Bearer JWT" --> CORS
    SPA -- "signed multipart POST" --> Cloud
    ORM --> PG
    AI -- "generate_content + tools" --> Gemini
    Storage -- "sign · upload · delete · ping" --> Cloud
    Mail -. "password reset" .-> SMTP
```

### Explanation

**Client tier.** The frontend is a static single-page app built with Vite and served from Netlify's CDN. [Refine](https://refine.dev) provides the data and auth providers, so pages use hooks like `useTable` and `useOne` that map onto the REST API's `{ data, pagination }` envelope. A shared Axios instance attaches the JWT from `localStorage` to every request. The Luminara panel lives in the app layout, so it's available on every page.

**Application tier.** A single FastAPI service on Render holds all business logic. Each resource has its own router under `app/api/`. Authentication and authorisation are FastAPI dependencies (`CurrentUser`, `AdminUser`, `require_role(...)`), so every route declares who may call it. The GenAI assistant is not a separate service: it's a Python package (`app/ai/`) inside the same process, sharing the same database session, models and permission helpers as the REST routers.

**Data tier.** PostgreSQL on Neon, accessed through the pooled connection string to stay within free-tier connection limits. The schema is versioned with Alembic. Scheduling integrity is enforced at the database level with `btree_gist` exclusion constraints that make overlapping room or lecturer bookings impossible, even if application code has a bug.

**External services.**
- **Gemini** is called only from the backend. The API key never reaches the browser.
- **Cloudinary** stores banners, profile pictures and documents. The backend signs upload requests and the browser sends files straight to Cloudinary, so large files never pass through the API server.
- **SMTP** is optional. Without it, password-reset links are written to the server log.

---

## 2. Backend internals

```mermaid
flowchart LR
    Req["HTTP request"] --> R["Router<br/>app/api/*.py"]
    R --> D{"Dependencies"}
    D --> Auth["get_current_user<br/>decode JWT → load user<br/>check active + approved"]
    D --> Role["require_role / AdminUser"]
    D --> DB["get_db<br/>session per request"]
    R --> S["Pydantic schemas<br/>app/schemas"]
    R --> Ser["serializers<br/>DB names → API names"]
    R --> M["ORM models<br/>app/models"]
    M --> PG[("Postgres")]

    R -- "/api/assistant/chat" --> RT["ai/runtime.py<br/>run_conversation"]
    RT --> P["ai/prompt.py<br/>system instruction"]
    RT --> Dec["ai/declarations.py<br/>tool schemas per role"]
    RT --> T["ai/tools.py<br/>25 tool handlers"]
    T --> M
```

| Module | Responsibility |
| --- | --- |
| `app/main.py` | Creates the FastAPI app, configures CORS, mounts all routers, exposes `/health` |
| `app/api/deps.py` | JWT validation, user loading with eager-loaded profiles, role guards |
| `app/api/*.py` | One router per resource: validation, permission checks, queries, responses |
| `app/schemas/` | Pydantic request and response models; `serialization_alias` maps DB field names (`name`, `phone`, `technical`) to client names (`full_name`, `phone_number`, `technical_services`) |
| `app/models/` | SQLAlchemy models: users and profiles, faculties, departments, programmes, subjects, classes, enrollments, buildings, rooms, schedules, notifications, documents, password-reset tokens |
| `app/core/` | Settings (`pydantic-settings`), password hashing and JWT, Cloudinary client, SMTP mailer |
| `app/ai/runtime.py` | The tool-calling loop, transaction handling and response shaping |
| `app/ai/prompt.py` | Builds the system instruction from the user's role, profile and current screen |
| `app/ai/declarations.py` | Gemini function schemas and the per-role write-tool allow-list |
| `app/ai/tools.py` | Tool implementations: scoped SQLAlchemy queries that respect the same visibility rules as the REST API |

### Assistant write permissions by role

| Role | Write tools offered to the model |
| --- | --- |
| Student | `join_class_by_invite_code`, `remove_enrollment`, `mark_notifications_read`, `update_my_profile` |
| Tutor | Student set (minus join) + `enroll_student`, `update_class`, `create_schedule`, `update_schedule`, `cancel_schedule` |
| Lecturer | Tutor set + `create_class` |
| Admin / Technical services | All 11 write tools |

All roles get all 14 read tools, but each read tool filters its results by the caller's visibility (for example, students only ever see teaching staff in `search_people`).

---

## 3. API sequence diagrams

### 3.1 Login and authenticated requests

Shows credential checking, brute-force lockout, the approval gate for new accounts, and how the JWT is used on later calls.

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant FE as React SPA
    participant API as FastAPI /api/auth
    participant DB as Postgres

    U->>FE: Enter email or username + password
    FE->>API: POST /api/auth/login
    API->>DB: SELECT user by email or username
    DB-->>API: user row

    alt Account currently locked
        API-->>FE: 429 Too Many Requests + Retry-After
        FE-->>U: Show lockout countdown
    else Wrong password
        API->>DB: failed_login_attempts += 1
        alt Attempts reached LOGIN_MAX_ATTEMPTS
            API->>DB: set locked_until = now + LOGIN_LOCKOUT_SECONDS
            API-->>FE: 429 Too Many Requests
        else Below limit
            API-->>FE: 401 Invalid credentials
        end
    else Deactivated or not yet approved
        API-->>FE: 403 Forbidden
        FE-->>U: "Awaiting admin approval"
    else Valid
        API->>DB: reset failed attempts
        API->>API: create JWT with sub=user_id, role, exp
        API-->>FE: 200 with user + access_token
        FE->>FE: Store token in localStorage
    end

    Note over FE,API: Every later request goes through the shared Axios instance
    FE->>API: GET /api/classes with Authorization Bearer token
    API->>API: get_current_user decodes JWT, checks active + approved
    API->>DB: Role-scoped query
    DB-->>API: rows
    API-->>FE: 200 with data + pagination
```

### 3.2 AI assistant chat with tool calling

The core GenAI flow. The model never sees the database directly; it can only call declared tools, and the backend executes them as the signed-in user.

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant FE as Assistant panel
    participant API as POST /api/assistant/chat
    participant RT as ai/runtime.py
    participant G as Google Gemini
    participant T as ai/tools.py
    participant DB as Postgres

    U->>FE: "Which rooms are free Thursday at 2pm?"
    FE->>FE: captureScreenContext() — route, filters, visible rows
    FE->>API: message + last 12 messages + context, Bearer JWT
    API->>API: Authenticate user, check GEMINI_API_KEY is set
    API->>RT: run_conversation(db, user, message, history, context)
    RT->>RT: Build system prompt (role brief, profile, screen)
    RT->>RT: Declare read tools + role-permitted write tools

    loop Up to ASSISTANT_MAX_TOOL_TURNS rounds
        RT->>G: generate_content(contents, tools, temperature 0.2)
        alt Model requests tool calls
            G-->>RT: function_call find_free_rooms(starts_at, ends_at)
            RT->>RT: Re-check write permission for this role
            RT->>T: run_tool(name, args, ctx)
            T->>DB: Scoped SQLAlchemy query as the signed-in user
            DB-->>T: rows
            T-->>RT: JSON result or error
            RT->>RT: Append function_response to contents
        else Model calls final_answer
            G-->>RT: final_answer(reply, sources, follow_ups)
            RT->>DB: COMMIT if mutations happened, else ROLLBACK
        end
    end

    RT-->>API: reply, sources, follow-ups, tool calls, mutations
    API-->>FE: 200 ChatResponse
    FE->>FE: Render markdown reply
    FE->>FE: useInvalidate() for each mutated resource
    FE-->>U: Answer + sources + suggested follow-ups

    Note over API,G: Gemini 429 → HTTP 429, 404 → 503 "model unavailable",<br/>401/403 → 503 "could not authenticate", other → 502. DB is rolled back on every error.
```

If the loop runs out of rounds without a `final_answer`, the runtime rolls back and returns a polite "try narrowing the question" reply rather than an error.

### 3.3 Assistant write with two-phase confirmation

Every write tool has a `confirmed` flag. The first call never changes data; it returns a summary that the model must relay to the user.

```mermaid
sequenceDiagram
    autonumber
    actor L as Lecturer
    participant FE as Assistant panel
    participant RT as Assistant runtime
    participant G as Gemini
    participant T as create_schedule tool
    participant DB as Postgres

    L->>FE: "Book CS201 in LT3 next Monday 10–12"
    FE->>RT: POST /api/assistant/chat
    RT->>G: prompt + tools
    G-->>RT: create_schedule(args, confirmed=false)
    RT->>T: run_tool
    T->>DB: Overlap check: room, lecturer, tutor, student cohort
    T-->>RT: status = confirmation_required + summary
    RT->>G: function_response
    G-->>RT: final_answer "This will book LT3 ... Confirm?"
    RT->>DB: ROLLBACK (nothing written)
    RT-->>FE: reply, awaitingConfirmation = true
    FE-->>L: Shows the proposed change

    L->>FE: "Yes"
    FE->>RT: POST /api/assistant/chat with history
    RT->>G: prompt + history + tools
    G-->>RT: create_schedule(args, confirmed=true)
    RT->>T: run_tool
    T->>DB: INSERT schedule
    Note right of DB: Exclusion constraints are the final guard<br/>against overlapping room or lecturer bookings
    T-->>RT: success, mutation recorded
    RT->>G: function_response
    G-->>RT: final_answer "Booked."
    RT->>DB: COMMIT
    RT-->>FE: reply + mutations = schedules
    FE->>FE: Invalidate schedules so open tables refresh
```

### 3.4 Direct-to-Cloudinary file upload

Files go straight from the browser to Cloudinary. The API only signs the request, so the Cloudinary secret stays on the server and large files never pass through Render.

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant FE as React SPA
    participant API as POST /api/uploads/presign
    participant C as Cloudinary

    U->>FE: Choose file (banner, image or document)
    FE->>FE: validateFile — type and 10 MB limit
    FE->>API: kind, content_type, filename + Bearer JWT
    API->>API: Check role (banners: teaching staff + admins only)
    API->>API: Check storage is configured
    API->>API: Build public_id and sign params with API secret
    API-->>FE: upload_url, fields (api_key, timestamp, signature...), file_url
    FE->>C: multipart POST with signed fields + file
    C-->>FE: 200 OK
    FE->>FE: Save file_url on the class, profile or document record
    Note over FE,C: Signatures expire after 1 hour. Images are served with f_auto,q_auto.
```

---

## 4. CI/CD pipeline

The project uses **Git-driven continuous deployment**: pushing to `main` triggers independent builds on Render (API) and Netlify (SPA). Database migrations are run manually from a developer machine before deploying a change that needs them.

The dashed nodes show a **recommended CI stage** using GitHub Actions. It isn't in the repository yet, but adding it would stop broken code from reaching production, since both platforms currently deploy whatever lands on `main`.

```mermaid
flowchart LR
    Dev["👩‍💻 Developer"] -->|"git push / open PR"| GH["GitHub<br/>repository"]

    subgraph CI["Recommended: GitHub Actions on pull requests"]
        direction TB
        FE_CI["Client job<br/>npm ci · npm run lint<br/>npm run build (tsc + vite)"]
        BE_CI["Server job<br/>pip install<br/>python tests/check_*.py"]
        MIG_CI["Migration job<br/>alembic upgrade head<br/>on a Postgres service container"]
    end

    GH -.->|"pull_request"| CI
    CI -.->|"all checks green"| Merge{"Merge to main"}
    GH -->|"merge / push"| Merge

    Dev -->|"manual, before deploy"| MIG["alembic upgrade head<br/>against Neon"]
    MIG --> Neon[("Neon Postgres")]

    subgraph Render["Render — backend CD (render.yaml)"]
        direction TB
        RB["Build<br/>pip install -r requirements.txt"]
        RS["Start<br/>uvicorn app.main:app"]
        RH{"Health check<br/>GET /health"}
        RLive["✅ API live"]
        RB --> RS --> RH
        RH -->|"200 ok"| RLive
        RH -->|"fails"| RKeep["Previous version<br/>keeps serving"]
    end

    subgraph Netlify["Netlify — frontend CD (netlify.toml)"]
        direction TB
        NB["Build in client/<br/>npm ci && npm run build<br/>Node 22"]
        NP["Publish dist/<br/>+ _redirects SPA fallback"]
        NLive["✅ SPA live on CDN"]
        NB --> NP --> NLive
    end

    Merge -->|"autoDeploy webhook"| RB
    Merge -->|"build hook"| NB
    RLive --> Neon
    NLive -->|"VITE_BACKEND_BASE_URL"| RLive

    classDef proposed stroke-dasharray: 5 5
    class FE_CI,BE_CI,MIG_CI proposed
```

### Pipeline stages

| Stage | Where | What happens | Failure behaviour |
| --- | --- | --- | --- |
| **Source** | GitHub | Push or merge to `main` fires webhooks to Render and Netlify | — |
| **CI** *(recommended)* | GitHub Actions | Lint, type-check and build the client; run backend check scripts against in-memory SQLite; apply migrations to a throwaway Postgres | PR blocked from merging |
| **Migrate** | Developer machine | `alembic upgrade head` against Neon's pooled URL, deliberately not run inside the app process | Deploy should wait |
| **Backend build** | Render | `pip install -r requirements.txt` from `server/` | Deploy aborted, previous version keeps running |
| **Backend release** | Render | `uvicorn` starts; Render polls `/health` before switching traffic | Unhealthy release never receives traffic |
| **Frontend build** | Netlify | `npm ci && npm run build` from `client/` on Node 22; `VITE_BACKEND_BASE_URL` injected at build time | Deploy aborted, previous version keeps serving |
| **Frontend release** | Netlify | `dist/` published atomically to the CDN; hashed `/assets/*` cached for 1 year | Instant rollback available in the Netlify UI |
| **Verify** | Manual | `/health`, admin `/api/system/status`, `/docs`, and a hard refresh on a nested route | — |

### Secrets and configuration

| Secret | Lives in | Never in |
| --- | --- | --- |
| `DATABASE_URL`, `GEMINI_API_KEY`, `CLOUDINARY_*`, `SMTP_*` | Render environment (`sync: false`, entered on first deploy) | Git, Netlify, browser |
| `JWT_SECRET` | Generated by Render (`generateValue: true`) | Anywhere else |
| `VITE_BACKEND_BASE_URL` | Netlify environment (public, compiled into the bundle) | — |

`FRONTEND_URL` on Render and `VITE_BACKEND_BASE_URL` on Netlify point at each other, so the first deployment is done in order: Render with a placeholder `FRONTEND_URL`, then Netlify, then update `FRONTEND_URL` and redeploy Render. See [DEPLOYMENT.md](../DEPLOYMENT.md) for the full walkthrough.

---

## 5. Key design decisions

**Assistant inside the API, not a separate service.** An earlier version ran the assistant as a Node/Express service with fixture data. Merging it into FastAPI lets tools reuse the exact models, permission helpers and overlap queries the REST API uses, so the assistant can't drift from the API's rules, and there's one fewer service to deploy.

**Tools instead of retrieval or prompt-stuffed data.** The prompt contains no institution data. Every fact comes from a tool call, which keeps answers current, keeps the prompt small, and means data access is governed by code rather than by instructions to the model.

**Defence in depth for writes.** Writes pass four independent gates: the role allow-list decides which tools are declared; the runtime re-checks permission on every call; each tool requires `confirmed=true`; and database constraints reject anything that still conflicts. The request's transaction commits only if a mutation succeeded.

**Own tool loop instead of automatic function calling.** The runtime disables the SDK's automatic function calling and runs its own loop. That gives explicit control over the round limit (important on the Gemini free tier), permission checks, error mapping and transaction boundaries.

**Signed direct uploads.** Sending files from the browser to Cloudinary keeps large payloads off the free-tier API server and keeps the storage secret out of the frontend.

**Integrity in the database.** Postgres exclusion constraints on `schedules` guarantee no double-booked rooms or lecturers, even under concurrent requests that would race past an application-level check.

**Stateless JWT auth.** Tokens carry the user id and role, which fits a single stateless API instance that may sleep and wake on the free tier. The trade-off is that tokens can't be revoked early; the `is_active` and `is_approved` checks on every request limit the impact.
