import { useMemo, useState } from "react";
import { useForm, type FieldValues, type Path } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRegister } from "@refinedev/core";
import { Eye, EyeOff, FileText, Loader2, Upload, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useDepartments } from "@/hooks/use-departments";
import {
  adminRegisterSchema,
  lecturerRegisterSchema,
  studentRegisterSchema,
  technicalServiceRegisterSchema,
  tutorRegisterSchema,
} from "@/lib/schema";
import { ROLE_LABELS } from "@/types";

import type { FieldConfig, RoleConfig } from "./role-config";

const SCHEMAS_BY_ROLE = {
  student: studentRegisterSchema,
  lecturer: lecturerRegisterSchema,
  tutor: tutorRegisterSchema,
  admin: adminRegisterSchema,
  technical_services: technicalServiceRegisterSchema,
} as const;

const STEP_LABELS = ["Personal", "Academic", "Documents", "Account", "Review"] as const;

const PERSONAL_FIELDS = [
  "full_name",
  "id_code",
  "email",
  "phone_number",
  "address",
  "emergency_contact_name",
  "emergency_contact_phone",
] as const;

const ACCOUNT_FIELDS = ["username", "password", "confirm_password"] as const;

interface RegisterWizardProps {
  config: RoleConfig;
  onBack: () => void;
}

export function RegisterWizard({ config, onBack }: RegisterWizardProps) {
  const [step, setStep] = useState(0);
  const [showPassword, setShowPassword] = useState(false);
  const [files, setFiles] = useState<Record<string, File | null>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const { departments, isLoading: departmentsLoading } = useDepartments();
  const { mutate: registerUser, isPending } = useRegister();

  const schema = SCHEMAS_BY_ROLE[config.role];
  const academicFieldNames = useMemo(
    () => config.academicFields.map((f) => f.name),
    [config.academicFields],
  );

  const {
    register,
    handleSubmit,
    trigger,
    getValues,
    formState: { errors },
  } = useForm<FieldValues>({
    resolver: zodResolver(schema as any),
    mode: "onBlur",
  });

  const stepFieldNames: string[][] = [
    config.role === "student" ? PERSONAL_FIELDS.filter((f) => f !== "id_code") : [...PERSONAL_FIELDS],
    academicFieldNames,
    [], // documents step has no RHF-validated fields (handled separately)
    [...ACCOUNT_FIELDS],
    [],
  ];

  const isLastStep = step === STEP_LABELS.length - 1;

  async function goNext() {
    const fieldsToValidate = stepFieldNames[step];
    if (fieldsToValidate.length > 0) {
      const valid = await trigger(fieldsToValidate as Path<FieldValues>[]);
      if (!valid) return;
    }
    if (step === 2) {
      const missingRequired = config.documents.find((d) => d.required && !files[d.name]);
      if (missingRequired) {
        setSubmitError(`${missingRequired.label} is required.`);
        return;
      }
    }
    setSubmitError(null);
    setStep((s) => Math.min(s + 1, STEP_LABELS.length - 1));
  }

  function goBack() {
    setSubmitError(null);
    setStep((s) => Math.max(s - 1, 0));
  }

  function handleFileChange(name: string, kind: "image" | "document") {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0] ?? null;
      if (file) {
        const allowed =
          kind === "image"
            ? ["image/jpeg", "image/jpg", "image/png"]
            : [
                "application/pdf",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
              ];
        if (!allowed.includes(file.type)) {
          setSubmitError(
            kind === "image"
              ? "Profile picture must be a JPG, JPEG, or PNG file."
              : "Documents must be a PDF, DOC, or DOCX file.",
          );
          return;
        }
        setSubmitError(null);
      }
      setFiles((prev) => ({ ...prev, [name]: file }));
    };
  }

  const onSubmit = handleSubmit((values) => {
    const formData = new FormData();
    Object.entries(values).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") return;
      formData.append(key, String(value));
    });
    Object.entries(files).forEach(([key, file]) => {
      if (file) formData.append(key, file);
    });

    setSubmitError(null);
    registerUser(
      { role: config.role, formData } as any,
      {
        onSuccess: (result: any) => {
          if (result?.success === false) {
            setSubmitError(result.error?.message ?? "Could not create your account.");
          }
        },
      },
    );
  });

  return (
    <div className="mx-auto w-full max-w-2xl">
      <button
        type="button"
        onClick={onBack}
        className="mb-4 text-sm text-muted-foreground hover:text-foreground"
      >
        &larr; Choose a different role
      </button>

      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-foreground">
          Register as {ROLE_LABELS[config.role]}
        </h1>
        <p className="text-sm text-muted-foreground">{config.tagline}</p>
      </div>

      <Stepper step={step} />

      <form onSubmit={onSubmit} className="mt-6 space-y-6 rounded-xl border border-border bg-card p-6 shadow-sm">
        {step === 0 && (
          <div className="space-y-4">
            {renderField(
              { name: "full_name", label: "Full name", type: "text" },
              register,
              errors,
            )}
            {config.role === "student" ? (
              <p className="rounded-md border border-dashed border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                Your {config.idLabel} will be generated automatically from your name after you submit
                (e.g. "Bhone Myint Maw" &rarr; "BMM00001").
              </p>
            ) : (
              renderField({ name: "id_code", label: config.idLabel, type: "text" }, register, errors)
            )}
            {renderField({ name: "email", label: "Email", type: "email" }, register, errors)}
            {renderField({ name: "phone_number", label: "Phone number", type: "tel" }, register, errors)}
            {renderField({ name: "address", label: "Address", type: "textarea" }, register, errors)}
            <div className="grid gap-4 sm:grid-cols-2">
              {renderField(
                { name: "emergency_contact_name", label: "Emergency contact name", type: "text" },
                register,
                errors,
              )}
              {renderField(
                { name: "emergency_contact_phone", label: "Emergency contact phone", type: "tel" },
                register,
                errors,
              )}
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4">
            {config.academicFields.map((field) =>
              renderField(field, register, errors, departments, departmentsLoading),
            )}
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <FileField
              name="profile_picture"
              label="Profile picture"
              hint="JPG, JPEG, or PNG"
              file={files.profile_picture ?? null}
              onChange={handleFileChange("profile_picture", "image")}
              onRemove={() => setFiles((p) => ({ ...p, profile_picture: null }))}
              accept="image/jpeg,image/jpg,image/png"
              preview
            />
            {config.documents.map((doc) => (
              <FileField
                key={doc.name}
                name={doc.name}
                label={doc.label}
                hint={doc.hint}
                required={doc.required}
                file={files[doc.name] ?? null}
                onChange={handleFileChange(doc.name, doc.kind)}
                onRemove={() => setFiles((p) => ({ ...p, [doc.name]: null }))}
                accept=".pdf,.doc,.docx"
              />
            ))}
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            {renderField({ name: "username", label: "Username", type: "text" }, register, errors)}
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
                <p className="text-xs text-destructive">{String(errors.password.message)}</p>
              )}
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
        )}

        {step === 4 && (
          <ReviewStep config={config} values={getValues()} files={files} />
        )}

        {submitError && (
          <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {submitError}
          </div>
        )}

        <div className="flex items-center justify-between pt-2">
          <Button type="button" variant="outline" onClick={goBack} disabled={step === 0}>
            Back
          </Button>
          {isLastStep ? (
            <Button type="submit" disabled={isPending}>
              {isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Creating account...
                </>
              ) : (
                "Create account"
              )}
            </Button>
          ) : (
            <Button type="button" onClick={goNext}>
              Next
            </Button>
          )}
        </div>
      </form>
    </div>
  );
}

function Stepper({ step }: { step: number }) {
  return (
    <ol className="flex items-center gap-2">
      {STEP_LABELS.map((label, i) => (
        <li key={label} className="flex flex-1 items-center gap-2">
          <div
            className={
              "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-medium " +
              (i < step
                ? "bg-primary text-primary-foreground"
                : i === step
                  ? "border-2 border-primary text-primary"
                  : "border border-border text-muted-foreground")
            }
          >
            {i + 1}
          </div>
          <span
            className={
              "hidden text-xs sm:block " +
              (i === step ? "font-medium text-foreground" : "text-muted-foreground")
            }
          >
            {label}
          </span>
          {i < STEP_LABELS.length - 1 && (
            <div className={"h-px flex-1 " + (i < step ? "bg-primary" : "bg-border")} />
          )}
        </li>
      ))}
    </ol>
  );
}

function renderField(
  field: FieldConfig,
  register: ReturnType<typeof useForm<FieldValues>>["register"],
  errors: ReturnType<typeof useForm<FieldValues>>["formState"]["errors"],
  departments: { id: number; name: string }[] = [],
  departmentsLoading = false,
) {
  const error = errors[field.name]?.message as string | undefined;

  if (field.type === "textarea") {
    return (
      <div key={field.name} className="space-y-1.5">
        <Label htmlFor={field.name}>{field.label}</Label>
        <Textarea id={field.name} rows={3} {...register(field.name)} />
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
    );
  }

  if (field.type === "select") {
    return (
      <div key={field.name} className="space-y-1.5">
        <Label htmlFor={field.name}>{field.label}</Label>
        <Select id={field.name} defaultValue="" {...register(field.name)}>
          <option value="" disabled>
            Select {field.label.toLowerCase()}
          </option>
          {field.options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
    );
  }

  if (field.type === "department-select") {
    return (
      <div key={field.name} className="space-y-1.5">
        <Label htmlFor={field.name}>{field.label}</Label>
        <Select id={field.name} defaultValue="" {...register(field.name)} disabled={departmentsLoading}>
          <option value="" disabled>
            {departmentsLoading ? "Loading departments..." : "Select a department"}
          </option>
          {departments.map((dept) => (
            <option key={dept.id} value={dept.id}>
              {dept.name}
            </option>
          ))}
        </Select>
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
    );
  }

  return (
    <div key={field.name} className="space-y-1.5">
      <Label htmlFor={field.name}>{field.label}</Label>
      <Input
        id={field.name}
        type={field.type}
        placeholder={"placeholder" in field ? field.placeholder : undefined}
        {...register(field.name)}
      />
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

interface FileFieldProps {
  name: string;
  label: string;
  hint: string;
  file: File | null;
  accept: string;
  required?: boolean;
  preview?: boolean;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onRemove: () => void;
}

function FileField({ name, label, hint, file, accept, required, preview, onChange, onRemove }: FileFieldProps) {
  const previewUrl = preview && file ? URL.createObjectURL(file) : null;

  return (
    <div className="space-y-1.5">
      <Label htmlFor={name}>
        {label}
        {required && <span className="text-destructive"> *</span>}
      </Label>
      {file ? (
        <div className="flex items-center justify-between rounded-md border border-border bg-muted/40 px-3 py-2">
          <div className="flex items-center gap-2 overflow-hidden">
            {previewUrl ? (
              <img src={previewUrl} alt="" className="h-8 w-8 rounded object-cover" />
            ) : (
              <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
            )}
            <div className="overflow-hidden">
              <p className="truncate text-sm text-foreground">{file.name}</p>
              <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(0)} KB</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onRemove}
            className="text-muted-foreground hover:text-destructive"
            aria-label={`Remove ${label}`}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ) : (
        <label
          htmlFor={name}
          className="flex cursor-pointer items-center justify-center gap-2 rounded-md border border-dashed border-border px-3 py-4 text-sm text-muted-foreground hover:border-primary hover:text-primary"
        >
          <Upload className="h-4 w-4" />
          Choose file
          <input id={name} type="file" accept={accept} onChange={onChange} className="hidden" />
        </label>
      )}
      <p className="text-xs text-muted-foreground">{hint}</p>
    </div>
  );
}

function ReviewStep({
  config,
  values,
  files,
}: {
  config: RoleConfig;
  values: FieldValues;
  files: Record<string, File | null>;
}) {
  const rows: [string, string][] = [
    ["Full name", values.full_name ?? "—"],
    [
      config.idLabel,
      config.role === "student" ? "Generated automatically after submission" : (values.id_code ?? "—"),
    ],
    ["Email", values.email ?? "—"],
    ["Phone number", values.phone_number ?? "—"],
    ["Username", values.username ?? "—"],
    ...config.academicFields.map(
      (f) => [f.label, String(values[f.name] ?? "—")] as [string, string],
    ),
    ["Profile picture", files.profile_picture?.name ?? "Not provided"],
    ...config.documents.map(
      (d) => [d.label, files[d.name]?.name ?? "Not provided"] as [string, string],
    ),
  ];

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Review your details before creating your account.
      </p>
      <dl className="divide-y divide-border rounded-md border border-border">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-4 px-3 py-2 text-sm">
            <dt className="text-muted-foreground">{label}</dt>
            <dd className="text-right text-foreground">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
