# Checks

Two standalone scripts. They build a throwaway SQLite database in memory and
never touch Neon, so they are safe to run at any time.

```bash
cd server
PYTHONPATH=. python tests/check_cohort_conflicts.py
PYTHONPATH=. python tests/check_auth_uploads.py
PYTHONPATH=. python tests/check_password_reset.py
```

Both need the environment loaded from `.env`, or the same variables exported. A
non-empty `DATABASE_URL` is required because `pydantic-settings` validates it at
import time, but the value is never connected to.

`check_cohort_conflicts.py` covers the student cohort overlap query: a clash is
found when two classes share enrolled students, the shared-student count is
correct, a non-overlapping window is clean, and a cancelled session stops
counting as a conflict.

`check_auth_uploads.py` drives the API through `TestClient`: student
registration with and without a supplied student ID, the 409 on a duplicate ID,
the banner upload role gate, the required `kind` field, every branch of
change-password, and the five-attempt lockout returning 429 with `Retry-After`.

`check_password_reset.py` covers the reset flow with the mail transport stubbed:
identical responses for known, unknown and deactivated addresses, the raw token
never being stored, rejection of forged, mismatched, weak and replayed tokens,
the old password ceasing to work, a new request invalidating the previous link,
and `/api/system/status` returning all four components to an admin while
rejecting an unauthenticated caller.

None of them use pytest. If you add it later, the assertions convert directly.
