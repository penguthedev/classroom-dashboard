# Classroom Dashboard — Client

React + Vite + TypeScript frontend for the Classroom Management Dashboard,
built with [Refine](https://refine.dev) (data/auth providers), shadcn-style
UI on Tailwind v4, react-hook-form + Zod, and direct-to-Cloudinary image
uploads.

## Stack

- **React 19 + Vite + TypeScript**
- **Refine Core** — `dataProvider` / `authProvider` seam, `useTable`/`useList`/`useOne`/`useCreate`
- **Tailwind v4** + hand-rolled shadcn-style primitives (`src/components/ui`)
- **react-hook-form + Zod** for all forms
- **Cloudinary** — unsigned browser upload + `@cloudinary/react` `AdvancedImage` for banners
- **react-router-dom v7** for routing

## Getting started

```bash
cd client
npm install
cp .env.example .env   # fill in the values below
npm run dev
```

The app runs at `http://localhost:5173` by default.

### Environment variables

| Variable | Description |
|---|---|
| `VITE_BACKEND_BASE_URL` | Base URL of the FastAPI backend, e.g. `http://localhost:8000` (no trailing slash). `/api` is appended automatically. |
| `VITE_CLOUDINARY_CLOUD_NAME` | Your Cloudinary cloud name. |
| `VITE_CLOUDINARY_UPLOAD_PRESET` | An **unsigned** upload preset — signed presets will fail silently from the browser. |

Without a running backend, the app will boot and show the login screen, but
every list/table request will fail until `server/` is up and matches the API
contract.

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Start the Vite dev server |
| `npm run build` | Typecheck (`tsc -b`) then produce a production build in `dist/` |
| `npm run preview` | Preview the production build locally |
| `npm run lint` | Run ESLint |

## Project layout

```
src/
├── components/
│   ├── ui/            # Button, Input, Card, Table, Badge, Select, Textarea...
│   └── layout/         # AppLayout (sidebar nav + identity + logout)
├── pages/
│   ├── auth/            # login.tsx, register.tsx
│   ├── dashboard/        # dashboard.tsx (resource counts)
│   ├── departments/      # list.tsx
│   ├── subjects/         # list.tsx (with department filter)
│   └── classes/          # list.tsx, show.tsx, create.tsx
├── providers/
│   ├── data.ts          # Refine DataProvider — matches the API contract exactly
│   └── auth.ts          # Refine AuthProvider — hand-rolled JWT flow
├── lib/
│   ├── http.ts          # Axios instance, attaches Bearer token
│   ├── schema.ts        # Zod schemas for every form
│   ├── cloudinary.ts    # unsigned upload + banner transform helper
│   └── utils.ts          # cn() class merger
├── types/                # Shared TS types matching the API contract
└── constants/            # Env-driven config, resource name constants
```

## How the data provider maps to the backend contract

`src/providers/data.ts` implements Refine's `DataProvider` against the exact
shapes in section 5 of the spec:

- `getList` → `GET /api/{resource}?page=&limit=&search=&department=...` and
  reads `{ data, pagination: { total } }`
- `getOne` → `GET /api/{resource}/{id}` → `{ data }`
- `create` → `POST /api/{resource}` → `{ data }`
- `update` → `PATCH /api/{resource}/{id}` → `{ data }`
- `deleteOne` → `DELETE /api/{resource}/{id}`

Refine filters are passed straight through as extra query params (`search`,
`department`, `subject`, `teacher`), which is what the FastAPI backend
actually expects — not Refine's generic filter DSL.

## Auth flow

`src/providers/auth.ts` implements `login`, `register`, `logout`, `check`,
`onError`, `getIdentity`, and `getPermissions` against `/api/auth/*`. The JWT
is stored in `localStorage` (`TOKEN_KEY` in `constants/index.ts`) and
attached to every request by `lib/http.ts`. A 401 anywhere logs the user out
and redirects to `/login`.

## Image uploads

Banners never touch the backend. `lib/cloudinary.ts` posts the file directly
to `https://api.cloudinary.com/v1_1/{cloud_name}/image/upload` with an
**unsigned** preset, and the resulting `secure_url` / `public_id` are sent to
the API as plain strings (`banner_url`, `banner_cld_pub_id`) as part of the
create-class payload.

## Deploying to Netlify

- Build command: `npm run build` · Publish directory: `dist`
- `public/_redirects` is already in place for SPA routing (fixes 404s on
  refresh for routes like `/classes`)
- Set the three env vars above in Netlify's site settings
- Remember the CORS ordering trap: deploy the backend first, set
  `VITE_BACKEND_BASE_URL` and redeploy the frontend, then set `FRONTEND_URL`
  on the backend and redeploy that too
