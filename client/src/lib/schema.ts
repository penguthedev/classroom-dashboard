import { z } from "zod";

export const loginSchema = z.object({
  identifier: z.string().min(1, "Enter your email or username"),
  password: z.string().min(1, "Enter your password"),
});
export type LoginFormValues = z.infer<typeof loginSchema>;

// --- Registration -----------------------------------------------------
// Mirrors server/app/schemas/auth.py: one schema per role, all sharing the
// same "common" personal/account fields from brief sections 2-6.

const passwordField = z
  .string()
  .min(8, "At least 8 characters")
  .refine(
    (v) => /[A-Za-z]/.test(v) && /\d/.test(v),
    "Must contain at least one letter and one number",
  );

const commonRegisterFields = z.object({
  id_code: z.string().min(2, "Required"),
  full_name: z.string().min(2, "Required"),
  username: z.string().min(3, "At least 3 characters"),
  email: z.string().email("Enter a valid email"),
  phone_number: z.string().min(6, "Enter a valid phone number"),
  address: z.string().max(2000).optional().or(z.literal("")),
  emergency_contact_name: z.string().max(255).optional().or(z.literal("")),
  emergency_contact_phone: z.string().max(30).optional().or(z.literal("")),
  password: passwordField,
  confirm_password: z.string().min(8, "At least 8 characters"),
});

function withPasswordMatch<T extends z.ZodRawShape>(schema: z.ZodObject<T>) {
  return schema.refine((data: any) => data.password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });
}

export const studentRegisterSchema = withPasswordMatch(
  commonRegisterFields.omit({ id_code: true }).extend({
    date_of_birth: z.string().min(1, "Required"),
    programme: z.string().min(1, "Required"),
    year_of_study: z.coerce.number().int().min(1, "Required").max(8),
  }),
);
export type StudentRegisterValues = z.infer<typeof studentRegisterSchema>;

export const lecturerRegisterSchema = withPasswordMatch(
  commonRegisterFields.extend({
    date_of_birth: z.string().min(1, "Required"),
    faculty: z.string().min(1, "Required"),
    department_id: z.coerce.number().int().positive("Select a department"),
    academic_position: z.enum([
      "professor",
      "associate_professor",
      "senior_lecturer",
      "lecturer",
      "assistant_lecturer",
    ]),
    specialization: z.string().min(1, "Required"),
    qualification: z.string().min(1, "Required"),
  }),
);
export type LecturerRegisterValues = z.infer<typeof lecturerRegisterSchema>;

export const tutorRegisterSchema = withPasswordMatch(
  commonRegisterFields.extend({
    date_of_birth: z.string().min(1, "Required"),
    faculty: z.string().min(1, "Required"),
    department_id: z.coerce.number().int().positive("Select a department"),
    subject_specialization: z.string().min(1, "Required"),
    qualification: z.string().min(1, "Required"),
  }),
);
export type TutorRegisterValues = z.infer<typeof tutorRegisterSchema>;

export const adminRegisterSchema = withPasswordMatch(
  commonRegisterFields.extend({
    department_id: z.coerce.number().int().positive("Select a department"),
    position: z.string().min(1, "Required"),
  }),
);
export type AdminRegisterValues = z.infer<typeof adminRegisterSchema>;

export const technicalServiceRegisterSchema = withPasswordMatch(
  commonRegisterFields.extend({
    department_id: z.coerce.number().int().positive("Select a department"),
    technical_position: z.string().min(1, "Required"),
    technical_specialization: z.enum([
      "network_administration",
      "system_administration",
      "cybersecurity",
      "hardware_support",
      "software_support",
      "database_administration",
    ]),
    qualification: z.string().min(1, "Required"),
  }),
);
export type TechnicalServiceRegisterValues = z.infer<typeof technicalServiceRegisterSchema>;

export const departmentSchema = z.object({
  code: z.string().min(2).max(50),
  name: z.string().min(2).max(255),
  description: z.string().max(2000).optional().or(z.literal("")),
});
export type DepartmentFormValues = z.infer<typeof departmentSchema>;

export const subjectSchema = z.object({
  code: z.string().min(2).max(50),
  name: z.string().min(2).max(255),
  description: z.string().max(2000).optional().or(z.literal("")),
  department_id: z.coerce.number().int().positive("Select a department"),
});
export type SubjectFormValues = z.infer<typeof subjectSchema>;

export const createClassSchema = z.object({
  name: z.string().min(2, "Class name is required").max(255),
  description: z.string().max(2000).optional().or(z.literal("")),
  subject_id: z.coerce.number().int().positive("Select a subject"),
  lecturer_id: z.coerce.number().int().positive("Select a lecturer"),
  tutor_id: z.coerce.number().int().optional(),
  capacity: z.coerce.number().int().min(1, "Capacity must be at least 1"),
  banner_url: z.string().url().optional().or(z.literal("")),
});
export type CreateClassFormInput = z.input<typeof createClassSchema>;
export type CreateClassFormValues = z.output<typeof createClassSchema>;
