import type { Role } from "@/types";

export type FieldConfig =
  | { name: string; label: string; type: "text" | "email" | "tel" | "date" | "number" | "textarea"; placeholder?: string }
  | { name: string; label: string; type: "select"; options: { value: string; label: string }[] }
  | { name: "department_id"; label: string; type: "department-select" };

export interface DocumentFieldConfig {
  name: string;
  label: string;
  kind: "image" | "document";
  required?: boolean;
  hint: string;
}

export interface RoleConfig {
  role: Role;
  title: string;
  tagline: string;
  idLabel: string;
  academicFields: FieldConfig[];
  documents: DocumentFieldConfig[];
}

const ACADEMIC_POSITION_OPTIONS = [
  { value: "professor", label: "Professor" },
  { value: "associate_professor", label: "Associate Professor" },
  { value: "senior_lecturer", label: "Senior Lecturer" },
  { value: "lecturer", label: "Lecturer" },
  { value: "assistant_lecturer", label: "Assistant Lecturer" },
];

const TECHNICAL_SPECIALIZATION_OPTIONS = [
  { value: "network_administration", label: "Network Administration" },
  { value: "system_administration", label: "System Administration" },
  { value: "cybersecurity", label: "Cybersecurity" },
  { value: "hardware_support", label: "Hardware Support" },
  { value: "software_support", label: "Software Support" },
  { value: "database_administration", label: "Database Administration" },
];

export const ROLE_CONFIGS: Record<Role, RoleConfig> = {
  student: {
    role: "student",
    title: "Student",
    tagline: "Enroll in classes and track your schedule",
    idLabel: "Student ID",
    academicFields: [
      { name: "date_of_birth", label: "Date of birth", type: "date" },
      { name: "programme", label: "Programme", type: "text", placeholder: "e.g. BSc Computer Science" },
      { name: "year_of_study", label: "Year of study", type: "number" },
    ],
    documents: [
      { name: "proof_of_enrollment", label: "Proof of enrollment", kind: "document", hint: "PDF, DOC, or DOCX" },
      { name: "transcript", label: "Academic transcript", kind: "document", hint: "PDF, DOC, or DOCX" },
    ],
  },
  lecturer: {
    role: "lecturer",
    title: "Lecturer",
    tagline: "Manage your classes and teaching schedule",
    idLabel: "Staff ID",
    academicFields: [
      { name: "date_of_birth", label: "Date of birth", type: "date" },
      { name: "faculty", label: "Faculty / School", type: "text", placeholder: "e.g. Faculty of Computing" },
      { name: "department_id", label: "Department", type: "department-select" },
      { name: "academic_position", label: "Academic position", type: "select", options: ACADEMIC_POSITION_OPTIONS },
      { name: "specialization", label: "Specialization", type: "text" },
      { name: "qualification", label: "Qualification", type: "text", placeholder: "e.g. PhD in Computer Science" },
    ],
    documents: [
      {
        name: "qualification_document",
        label: "Academic qualification document",
        kind: "document",
        hint: "PDF, DOC, or DOCX",
      },
    ],
  },
  tutor: {
    role: "tutor",
    title: "Tutor",
    tagline: "Support teaching and track your assigned students",
    idLabel: "Tutor ID",
    academicFields: [
      { name: "date_of_birth", label: "Date of birth", type: "date" },
      { name: "faculty", label: "Faculty / School", type: "text", placeholder: "e.g. Faculty of Computing" },
      { name: "department_id", label: "Department", type: "department-select" },
      { name: "subject_specialization", label: "Subject / specialization", type: "text" },
      { name: "qualification", label: "Qualification", type: "text", placeholder: "e.g. MSc Computer Science" },
    ],
    documents: [
      { name: "qualification_document", label: "Qualification document", kind: "document", hint: "PDF, DOC, or DOCX" },
    ],
  },
  admin: {
    role: "admin",
    title: "Admin",
    tagline: "Manage users, schedules, and system-wide settings",
    idLabel: "Admin ID",
    academicFields: [
      { name: "department_id", label: "Department", type: "department-select" },
      { name: "position", label: "Position", type: "text", placeholder: "e.g. Registrar" },
    ],
    documents: [
      {
        name: "staff_verification_document",
        label: "Staff verification document",
        kind: "document",
        required: true,
        hint: "Required — admin accounts have full system access",
      },
    ],
  },
  technical_services: {
    role: "technical_services",
    title: "Technical Services",
    tagline: "Support the platform's systems and infrastructure",
    idLabel: "Technical Staff ID",
    academicFields: [
      { name: "department_id", label: "Department", type: "department-select" },
      { name: "technical_position", label: "Technical position", type: "text", placeholder: "e.g. Systems Engineer" },
      {
        name: "technical_specialization",
        label: "Technical specialization",
        type: "select",
        options: TECHNICAL_SPECIALIZATION_OPTIONS,
      },
      { name: "qualification", label: "Qualification", type: "text" },
    ],
    documents: [
      {
        name: "certification_document",
        label: "Qualification / certification document",
        kind: "document",
        hint: "PDF, DOC, or DOCX",
      },
    ],
  },
};
