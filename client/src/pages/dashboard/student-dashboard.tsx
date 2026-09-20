import { Link } from "react-router-dom";
import { useGetIdentity, useList } from "@refinedev/core";
import { CalendarClock, GraduationCap, MapPin, School } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RESOURCES } from "@/constants";
import type { Class, Schedule, User } from "@/types";

function formatWhen(startsAt: string, endsAt: string): string {
  const start = new Date(startsAt);
  const end = new Date(endsAt);
  const day = start.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  const startTime = start.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  const endTime = end.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  return `${day}, ${startTime} – ${endTime}`;
}

export function StudentDashboard() {
  const { data: identity } = useGetIdentity<User>();

  const { result: classesResult, query: classesQuery } = useList<Class>({
    resource: RESOURCES.classes,
    filters: [{ field: "mine", operator: "eq", value: true }],
    pagination: { pageSize: 6 },
  });

  const { result: scheduleResult, query: scheduleQuery } = useList<Schedule>({
    resource: "schedules",
    filters: [{ field: "from", operator: "eq", value: new Date().toISOString() }],
    sorters: [{ field: "starts_at", order: "asc" }],
    pagination: { pageSize: 5 },
  });

  const classes = classesResult?.data ?? [];
  const schedule = scheduleResult?.data ?? [];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">
          Welcome{identity ? `, ${identity.full_name.split(" ")[0]}` : ""}
        </h1>
        <p className="text-sm text-muted-foreground">
          Your enrolled classes and what's coming up next.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Enrolled classes
            </CardTitle>
            <School className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {classesQuery.isLoading ? "—" : (classesResult?.total ?? 0)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Upcoming sessions
            </CardTitle>
            <CalendarClock className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {scheduleQuery.isLoading ? "—" : (scheduleResult?.total ?? 0)}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <section>
          <h2 className="mb-3 text-lg font-medium">My classes</h2>
          {classesQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : classes.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              You're not enrolled in any classes yet.
            </p>
          ) : (
            <div className="space-y-3">
              {classes.map((cls) => (
                <Link
                  key={cls.id}
                  to={`/classes/${cls.id}`}
                  className="flex items-center justify-between rounded-lg border border-border bg-card p-4 shadow-sm transition-colors hover:border-primary hover:bg-accent"
                >
                  <div>
                    <p className="font-medium text-foreground">{cls.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {cls.subject.name} · {cls.lecturer.full_name}
                    </p>
                  </div>
                  <GraduationCap className="size-4 shrink-0 text-muted-foreground" />
                </Link>
              ))}
            </div>
          )}
        </section>

        <section>
          <h2 className="mb-3 text-lg font-medium">Upcoming schedule</h2>
          {scheduleQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : schedule.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nothing scheduled yet.</p>
          ) : (
            <div className="space-y-3">
              {schedule.map((session) => (
                <div
                  key={session.id}
                  className="rounded-lg border border-border bg-card p-4 shadow-sm"
                >
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-foreground">{session.class.name}</p>
                    {session.status !== "scheduled" && (
                      <Badge variant="secondary">{session.status}</Badge>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatWhen(session.starts_at, session.ends_at)}
                  </p>
                  <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                    <MapPin className="size-3" />
                    {session.room.building.name} · {session.room.name ?? session.room.code}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
