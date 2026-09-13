import { Link } from "react-router-dom";
import { GraduationCap, LogIn, UserPlus } from "lucide-react";

export function WelcomePage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <div className="w-full max-w-2xl">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <GraduationCap className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-semibold text-foreground">
            University Management System
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Are you a new or a returning student?
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Link
            to="/register"
            className="group flex flex-col items-start gap-3 rounded-xl border border-border bg-card p-6 text-left shadow-sm transition-colors hover:border-primary hover:bg-accent"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-accent-foreground group-hover:bg-primary group-hover:text-primary-foreground">
              <UserPlus className="h-5 w-5" />
            </div>
            <div>
              <p className="font-medium text-foreground">New student? Register</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Create an account to enroll and get started.
              </p>
            </div>
          </Link>

          <Link
            to="/login"
            className="group flex flex-col items-start gap-3 rounded-xl border border-border bg-card p-6 text-left shadow-sm transition-colors hover:border-primary hover:bg-accent"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-accent-foreground group-hover:bg-primary group-hover:text-primary-foreground">
              <LogIn className="h-5 w-5" />
            </div>
            <div>
              <p className="font-medium text-foreground">Already a student? Login</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Sign in to access your existing account.
              </p>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}
