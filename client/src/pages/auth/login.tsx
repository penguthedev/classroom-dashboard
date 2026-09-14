import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useLogin } from "@refinedev/core";
import { Eye, EyeOff, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { type LoginFormValues, loginSchema } from "@/lib/schema";

export function LoginPage() {
  const { mutate: login, isPending } = useLogin<LoginFormValues>();
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [lockedUntilCountdown, setLockedUntilCountdown] = useState<number | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) });

  useEffect(() => {
    if (lockedUntilCountdown === null) return;
    if (lockedUntilCountdown <= 0) {
      setLockedUntilCountdown(null);
      setFormError(null);
      return;
    }
    const timer = setTimeout(() => setLockedUntilCountdown((s) => (s ?? 0) - 1), 1000);
    return () => clearTimeout(timer);
  }, [lockedUntilCountdown]);

  const isLocked = lockedUntilCountdown !== null && lockedUntilCountdown > 0;

  function onSubmit(values: LoginFormValues) {
    setFormError(null);
    login(values, {
      onSuccess: (result: any) => {
        if (result?.success === false) {
          const retryAfterSeconds = result.error?.retryAfterSeconds as number | undefined;
          if (typeof retryAfterSeconds === "number") {
            setLockedUntilCountdown(retryAfterSeconds);
          }
          setFormError(result.error?.message ?? "Invalid email or username, or password.");
        }
      },
    });
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Sign in</CardTitle>
          <CardDescription>
            University Management System — enter your credentials.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
            <div className="space-y-1.5">
              <Label htmlFor="identifier">Email or username</Label>
              <Input
                id="identifier"
                placeholder="you@school.edu or username"
                {...register("identifier")}
              />
              {errors.identifier && (
                <p className="text-xs text-destructive">{errors.identifier.message}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  {...register("password")}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="text-xs text-destructive">{errors.password.message}</p>
              )}
            </div>

            {formError && (
              <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {formError}
                {isLocked && (
                  <span className="mt-1 block font-medium">
                    Try again in {lockedUntilCountdown}s.
                  </span>
                )}
              </div>
            )}

            <Button type="submit" className="w-full" disabled={isPending || isLocked}>
              {isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Signing in...
                </>
              ) : isLocked ? (
                "Try again in " + lockedUntilCountdown + "s"
              ) : (
                "Sign in"
              )}
            </Button>
          </form>

          <p className="mt-4 text-center text-sm text-muted-foreground">
            No account?{" "}
            <Link to="/register" className="font-medium text-primary underline-offset-4 hover:underline">
              Register
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
