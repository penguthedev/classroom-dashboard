import { useState } from "react";
import { Link } from "react-router-dom";
import { GraduationCap, Shield, UserCog, Users, Wrench } from "lucide-react";

import { ROLE_LABELS, type Role } from "@/types";

import { ROLE_CONFIGS } from "./role-config";
import { RegisterWizard } from "./RegisterWizard";

const ROLE_ICONS: Record<Role, React.ComponentType<{ className?: string }>> = {
  student: GraduationCap,
  lecturer: Users,
  tutor: Users,
  admin: Shield,
  technical_services: Wrench,
};

export function RegisterPage() {
  const [role, setRole] = useState<Role | null>(null);

  if (role) {
    return (
      <div className="min-h-screen bg-muted/30 p-4 py-10">
        <RegisterWizard config={ROLE_CONFIGS[role]} onBack={() => setRole(null)} />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <div className="w-full max-w-2xl">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <UserCog className="h-5 w-5" />
          </div>
          <h1 className="text-2xl font-semibold text-foreground">Create an account</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Select your role to get started with the right registration form.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {(Object.keys(ROLE_CONFIGS) as Role[]).map((r) => {
            const Icon = ROLE_ICONS[r];
            return (
              <button
                key={r}
                type="button"
                onClick={() => setRole(r)}
                className="flex items-start gap-3 rounded-xl border border-border bg-card p-4 text-left shadow-sm transition-colors hover:border-primary hover:bg-accent"
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                  <Icon className="h-4 w-4" />
                </div>
                <div>
                  <p className="font-medium text-foreground">{ROLE_LABELS[r]}</p>
                  <p className="text-xs text-muted-foreground">{ROLE_CONFIGS[r].tagline}</p>
                </div>
              </button>
            );
          })}
        </div>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-primary underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
