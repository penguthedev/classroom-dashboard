import { useState } from "react";
import { useForm, type FieldValues, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { AxiosError } from "axios";
import { CheckCircle2, Eye, EyeOff, Loader2, ShieldPlus } from "lucide-react";

import { AdminOnly } from "@/components/admin-only";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { useDepartments } from "@/hooks/use-departments";
import { http } from "@/lib/http";
import { adminRegisterSchema } from "@/lib/schema";
import type { TokenResponsePayload, User } from "@/types";

function errorMessage(error: unknown): string {
  const detail = (error as AxiosError<{ detail?: unknown }>).response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && typeof detail[0]?.msg === "string") return detail[0].msg;
  return "Could not create the admin account. Please try again.";
}

export function CreateAdminPage() {
  return (
    <AdminOnly>
      <CreateAdminForm />
    </AdminOnly>
  );
}

function CreateAdminForm() {
  const { departments, isLoading: departmentsLoading } = useDepartments();
  const [showPassword, setShowPassword] = useState(false);
  const [document, setDocument] = useState<File | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [created, setCreated] = useState<User | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FieldValues>({
    resolver: zodResolver(adminRegisterSchema) as unknown as Resolver<FieldValues>,
    mode: "onBlur",
  });

  const onSubmit = handleSubmit(async (values) => {
    const formData = new FormData();
    Object.entries(values).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") return;
      formData.append(key, String(value));
    });
    if (document) formData.append("staff_verification_document", document);

    setSubmitError(null);
    try {
      // Goes through the shared axios instance, so the signed-in admin's token
      // is attached. The API does not return a token for the new account, so
      // you stay signed in as yourself.
      const { data } = await http.post<TokenResponsePayload>("/auth/register/admin", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setCreated(data.user);
      setDocument(null);
      reset();
    } catch (error) {
      setSubmitError(errorMessage(error));
    }
  });

  const field = (name: string, label: string, type = "text", placeholder?: string) => (
    <div className="space-y-1.5">
      <Label htmlFor={name}>{label}</Label>
      <Input id={name} type={type} placeholder={placeholder} {...register(name)} />
      {errors[name] && <p className="text-xs text-destructive">{String(errors[name]?.message)}</p>}
    </div>
  );

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Create admin account</h1>
        <p className="text-sm text-muted-foreground">
          Admin accounts can only be created here, by an existing admin. They're approved straight
          away — share the username and password with the new admin so they can sign in.
        </p>
      </div>

      {created && (
        <div className="mb-4 flex items-start gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-400">
          <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
          <span>
            Admin account for <strong>{created.full_name}</strong> created (username{" "}
            <strong>{created.username}</strong>
            {created.id_code ? <>, ID <strong>{created.id_code}</strong></> : null}). They can sign in now.
          </span>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldPlus className="size-4" /> New admin details
          </CardTitle>
          <CardDescription>Fields match the admin registration form.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            {field("full_name", "Full name")}
            <div className="grid gap-4 sm:grid-cols-2">
              {field("email", "Email", "email")}
              {field("phone_number", "Phone number", "tel")}
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="department_id">Department</Label>
                <Select id="department_id" defaultValue="" disabled={departmentsLoading} {...register("department_id")}>
                  <option value="" disabled>
                    {departmentsLoading ? "Loading departments..." : "Select a department"}
                  </option>
                  {departments.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </Select>
                {errors.department_id && (
                  <p className="text-xs text-destructive">{String(errors.department_id.message)}</p>
                )}
              </div>
              {field("position", "Position", "text", "e.g. Registrar")}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="staff_verification_document">Staff verification document (optional)</Label>
              <Input
                id="staff_verification_document"
                type="file"
                accept=".pdf,.doc,.docx"
                onChange={(e) => setDocument(e.target.files?.[0] ?? null)}
              />
            </div>

            <div className="border-t pt-4" />
            {field("username", "Username")}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="password">Temporary password</Label>
                <div className="relative">
                  <Input id="password" type={showPassword ? "text" : "password"} {...register("password")} />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                  </button>
                </div>
                {errors.password && <p className="text-xs text-destructive">{String(errors.password.message)}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="confirm_password">Confirm password</Label>
                <Input
                  id="confirm_password"
                  type={showPassword ? "text" : "password"}
                  {...register("confirm_password")}
                />
                {errors.confirm_password && (
                  <p className="text-xs text-destructive">{String(errors.confirm_password.message)}</p>
                )}
              </div>
            </div>

            {submitError && (
              <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {submitError}
              </div>
            )}

            <div className="flex justify-end">
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="animate-spin" /> Creating...
                  </>
                ) : (
                  "Create admin"
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
