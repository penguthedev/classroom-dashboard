import { useList } from "@refinedev/core";
import { Building2, GraduationCap, School, Users } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RESOURCES } from "@/constants";

const STAT_CARDS = [
  { resource: RESOURCES.departments, label: "Departments", icon: Building2 },
  { resource: RESOURCES.subjects, label: "Subjects", icon: GraduationCap },
  { resource: RESOURCES.classes, label: "Classes", icon: School },
  { resource: RESOURCES.users, label: "Users", icon: Users },
] as const;

function StatCard({
  resource,
  label,
  icon: Icon,
}: (typeof STAT_CARDS)[number]) {
  const { result, query } = useList({
    resource,
    pagination: { pageSize: 1 },
  });

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {label}
        </CardTitle>
        <Icon className="size-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">
          {query.isLoading ? "—" : (result.total ?? 0)}
        </div>
      </CardContent>
    </Card>
  );
}

export function DashboardPage() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          An overview of the classroom management system.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STAT_CARDS.map((card) => (
          <StatCard key={card.resource} {...card} />
        ))}
      </div>
    </div>
  );
}
