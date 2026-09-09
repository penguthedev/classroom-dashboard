import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});
export type LoginFormValues = z.infer<typeof loginSchema>;

export const registerSchema = z.object({
  name: z.string().min(2, "Name is required"),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  role: z.enum(["student", "teacher", "admin"]),
});
export type RegisterFormValues = z.infer<typeof registerSchema>;

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
  teacher_id: z.coerce.number().int().positive("Select a teacher"),
  capacity: z.coerce.number().int().min(1, "Capacity must be at least 1"),
  banner_url: z.string().url().optional().or(z.literal("")),
  banner_cld_pub_id: z.string().optional().or(z.literal("")),
});
/** Raw form values as typed by the user (numeric fields are strings until coerced). */
export type CreateClassFormInput = z.input<typeof createClassSchema>;
/** Parsed values after Zod coercion — what actually gets submitted. */
export type CreateClassFormValues = z.output<typeof createClassSchema>;
