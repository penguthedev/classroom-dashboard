import { Link } from "react-router-dom";
import { Clock3, LogIn } from "lucide-react";

export function RegistrationPendingPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <div className="w-full max-w-md rounded-xl border border-border bg-card p-8 text-center shadow-sm">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-accent text-accent-foreground">
          <Clock3 className="h-6 w-6" />
        </div>
        <h1 className="text-xl font-semibold text-foreground">Account created</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Your account is waiting for an administrator to review and approve it. You'll be
          able to sign in as soon as that happens — this usually doesn't take long.
        </p>
        <Link
          to="/login"
          className="mt-6 inline-flex items-center justify-center gap-2 rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
        >
          <LogIn className="h-4 w-4" />
          Back to sign in
        </Link>
      </div>
    </div>
  );
}
