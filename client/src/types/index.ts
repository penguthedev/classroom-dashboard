export type Role = "student" | "lecturer" | "tutor" | "admin" | "technical_services";
export type ClassStatus = "active" | "archived";

export const ROLE_LABELS: Record<Role, string> = {
  student: "Student",
  lecturer: "Lecturer",
  tutor: "Tutor",
  admin: "Admin",
  technical_services: "Technical Services",
};

export interface Department {
  id: number;
  code: string;
  name: string;
  description: string | null;
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

export interface StudentProfile {
  date_of_birth: string;
  programme: string;
  year_of_study: number;
  proof_of_enrollment_url: string | null;
  transcript_url: string | null;
}

export interface LecturerProfile {
  date_of_birth: string;
  faculty: string;
  department_id: number;
  academic_position: string;
  specialization: string;
  qualification: string;
  qualification_document_url: string | null;
}

export interface TutorProfile {
  date_of_birth: string;
  faculty: string;
  department_id: number;
  subject_specialization: string;
  qualification: string;
  qualification_document_url: string | null;
}

export interface AdminProfile {
  department_id: number;
  position: string;
  verification_document_url: string | null;
}

export interface TechnicalServiceProfile {
  department_id: number;
  technical_position: string;
  technical_specialization: string;
  qualification: string;
  certification_document_url: string | null;
}

export type AnyProfile =
  | StudentProfile
  | LecturerProfile
  | TutorProfile
  | AdminProfile
  | TechnicalServiceProfile;

/** Matches the backend's UserOut schema (see server/app/schemas/user.py). */
export interface User {
  id: number;
  id_code: string;
  role: Role;
  full_name: string;
  username: string;
  email: string;
  phone_number: string;
  profile_picture_url: string | null;
  address: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  is_active: boolean;
  created_at: string;
  profile: AnyProfile | null;
}

export interface Class {
  id: number;
  name: string;
  description: string | null;
  capacity: number;
  status: ClassStatus;
  banner_url: string | null;
  invite_code: string;
  subject_id: number;
  lecturer_id: number;
  tutor_id: number | null;
  subject: Pick<Subject, "id" | "code" | "name" | "description" | "department">;
  lecturer: Pick<User, "id" | "full_name" | "email" | "profile_picture_url">;
  tutor: Pick<User, "id" | "full_name" | "email" | "profile_picture_url"> | null;
  created_at: string;
  updated_at: string;
}

export interface Schedule {
  id: number;
  class_id: number;
  session_date: string;
  start_time: string;
  end_time: string;
  classroom: string;
  building: string;
  status: "scheduled" | "cancelled" | "completed";
  class_?: Pick<Class, "id" | "name" | "subject" | "lecturer" | "tutor">;
}

export interface Enrollment {
  id: number;
  student_id: number;
  class_id: number;
  enrolled_at: string;
  student?: Pick<User, "id" | "full_name" | "email">;
  class_?: Pick<Class, "id" | "name">;
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

export interface TokenResponsePayload {
  access_token: string;
  token_type: string;
  user: User;
}

/** Shape of the 423 lockout body returned by POST /api/auth/login. */
export interface LockoutDetail {
  message: string;
  retry_after_seconds: number;
}
