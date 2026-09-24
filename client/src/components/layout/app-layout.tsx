import type { PropsWithChildren } from "react";
import { NavLink } from "react-router-dom";
import { useGetIdentity, useLogout } from "@refinedev/core";
import {
  Building2,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  School,
  ShieldPlus,
  UserCheck,
} from "lucide-react";

import { AssistantWidget } from "@/components/assistant";
import { Button } from "@/components/ui/button";
import { usePendingApprovals } from "@/hooks/use-pending-approvals";
import { roleHome } from "@/providers/auth";
import { cn } from "@/lib/utils";
import { ROLE_LABELS, type User } from "@/types";

const BASE_NAV_ITEMS = [
  { to: "/departments", label: "Departments", icon: Building2 },
  { to: "/subjects", label: "Subjects", icon: GraduationCap },
  { to: "/classes", label: "Classes", icon: School },
];

export function AppLayout({ children }: PropsWithChildren) {
  const { data: identity } = useGetIdentity<User>();
  const { mutate: logout } = useLogout();

  const isAdmin = identity?.role === "admin";
  const pendingCount = usePendingApprovals(isAdmin);

  const dashboardTo = identity ? roleHome(identity.role) : "/";
  const navItems: {
    to: string;
    label: string;
    icon: typeof LayoutDashboard;
    badge?: number | null;
  }[] = [
    { to: dashboardTo, label: "Dashboard", icon: LayoutDashboard },
    ...BASE_NAV_ITEMS,
    ...(isAdmin
      ? [
          { to: "/admin/approvals", label: "Approvals", icon: UserCheck, badge: pendingCount },
          { to: "/admin/create-admin", label: "Create admin", icon: ShieldPlus },
        ]
      : []),
  ];

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="hidden w-64 shrink-0 flex-col border-r bg-sidebar text-sidebar-foreground md:flex">
        <div className="flex h-14 items-center gap-2 border-b px-4">
          <School className="size-5" />
          <span className="font-semibold">Classroom Admin</span>
        </div>

        <nav className="flex-1 space-y-1 p-3">
          {navItems.map(({ to, label, icon: Icon, badge }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                  isActive &&
                    "bg-sidebar-accent text-sidebar-accent-foreground",
                )
              }
            >
              <Icon className="size-4" />
              {label}
              {badge ? (
                <span className="ml-auto rounded-full bg-amber-500 px-2 py-0.5 text-xs font-semibold text-white">
                  {badge}
                </span>
              ) : null}
            </NavLink>
          ))}
        </nav>

        <div className="border-t p-3">
          <div className="mb-2 px-1 text-xs text-muted-foreground">
            {identity ? (
              <>
                <div className="truncate font-medium text-sidebar-foreground">
                  {identity.full_name}
                </div>
                <div className="truncate">{ROLE_LABELS[identity.role]}</div>
              </>
            ) : (
              "Loading..."
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2"
            onClick={() => logout()}
          >
            <LogOut className="size-4" />
            Log out
          </Button>
        </div>
      </aside>

      <main className="flex-1 overflow-x-hidden">
        <div className="mx-auto max-w-6xl p-4 md:p-8">{children}</div>
      </main>

      <AssistantWidget />
    </div>
  );
}
