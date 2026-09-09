export type Role = "student" | "teacher" | "admin";
export type ClassStatus = "active" | "archived";

export interface Department {
  id: number;
  code: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface Subject {
  id: number;
  code: string;
  name: string;
  description: string | null;
  department_id: number;
  department: Pick<Department, "id" | "code" | "name" | "description">;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  image_url: string | null;
}

export interface Class {
  id: number;
  name: string;
  description: string | null;
  capacity: number;
  status: ClassStatus;
  banner_url: string | null;
  banner_cld_pub_id: string | null;
  invite_code: string;
  subject_id: number;
  teacher_id: number;
  subject: Pick<Subject, "id" | "code" | "name" | "description">;
  teacher: Pick<User, "id" | "name" | "email" | "image_url">;
  department: Pick<Department, "id" | "code" | "name">;
  created_at: string;
  updated_at: string;
}

export interface Enrollment {
  id: number;
  student_id: number;
  class_id: number;
  enrolled_at: string;
  student?: Pick<User, "id" | "name" | "email">;
  class?: Pick<Class, "id" | "name">;
}

/** Envelope every list endpoint returns. */
export interface ListResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

/** Envelope every single-resource endpoint returns. */
export interface SingleResponse<T> {
  data: T;
}

export interface AuthResponsePayload {
  user: User;
  access_token: string;
}
