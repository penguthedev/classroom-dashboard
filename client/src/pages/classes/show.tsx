import { Link, useParams } from "react-router-dom";
import { useOne } from "@refinedev/core";
import { ArrowLeft, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { RESOURCES } from "@/constants";
import type { Class } from "@/types";

export function ClassShowPage() {
  const { id } = useParams();

  const { result, query } = useOne<Class>({
    resource: RESOURCES.classes,
    id,
  });

  const klass = result;

  if (query.isLoading) {
    return <p className="text-muted-foreground">Loading...</p>;
  }

  if (!klass) {
    return <p className="text-muted-foreground">Class not found.</p>;
  }

  return (
    <div>
      <Link
        to="/classes"
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        Back to classes
      </Link>

      <Card className="overflow-hidden">
        {klass.banner_url ? (
          <img
            src={klass.banner_url}
            alt={klass.name}
            className="h-56 w-full object-cover"
          />
        ) : (
          <div className="flex h-56 w-full items-center justify-center bg-muted text-muted-foreground">
            No banner image
          </div>
        )}

        <CardContent className="p-6">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold">{klass.name}</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                {klass.description}
              </p>
            </div>
            <Badge
              variant={klass.status === "active" ? "default" : "secondary"}
              className="capitalize"
            >
              {klass.status}
            </Badge>
          </div>

          <dl className="grid grid-cols-1 gap-4 border-t pt-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs uppercase text-muted-foreground">
                Department
              </dt>
              <dd className="font-medium">{klass.subject.department.name}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-muted-foreground">
                Subject
              </dt>
              <dd className="font-medium">
                {klass.subject.code} — {klass.subject.name}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-muted-foreground">
                Teacher
              </dt>
              <dd className="font-medium">{klass.lecturer.full_name}</dd>
              <dd className="text-sm text-muted-foreground">
                {klass.lecturer.email}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-muted-foreground">
                Capacity
              </dt>
              <dd className="flex items-center gap-1.5 font-medium">
                <Users className="size-4 text-muted-foreground" />
                {klass.capacity} seats
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-muted-foreground">
                Invite code
              </dt>
              <dd className="font-mono font-medium">{klass.invite_code}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      <Link
        to="/classes"
        className={buttonVariants({ variant: "outline", className: "mt-4" })}
      >
        Back to list
      </Link>
    </div>
  );
}
