export const BACKEND_BASE_URL: string =
  import.meta.env.VITE_BACKEND_BASE_URL ?? "http://localhost:8000";

export const API_BASE_URL = `${BACKEND_BASE_URL}/api`;

export const CLOUDINARY_CLOUD_NAME: string =
  import.meta.env.VITE_CLOUDINARY_CLOUD_NAME ?? "";

export const CLOUDINARY_UPLOAD_PRESET: string =
  import.meta.env.VITE_CLOUDINARY_UPLOAD_PRESET ?? "";

export const TOKEN_KEY = "classroom_dashboard_token";

export const ROLES = ["student", "teacher", "admin"] as const;

export const RESOURCES = {
  departments: "departments",
  subjects: "subjects",
  classes: "classes",
  users: "users",
  enrollments: "enrollments",
} as const;
