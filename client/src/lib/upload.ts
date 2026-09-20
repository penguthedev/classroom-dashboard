import { http } from "@/lib/http";

export type UploadKind = "image" | "document" | "banner";

export interface PresignedUpload {
  upload_url: string;
  object_key: string;
  file_url: string;
  fields: Record<string, string | number>;
  expires_in: number;
}

export interface UploadedFile {
  file_url: string;
  object_key: string;
}

export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

const IMAGE_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp"];

const DOCUMENT_TYPES = [
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];

const ACCEPTED_TYPES: Record<UploadKind, string[]> = {
  image: IMAGE_TYPES,
  banner: IMAGE_TYPES,
  document: DOCUMENT_TYPES,
};

const TYPE_LABELS: Record<UploadKind, string> = {
  image: "JPG, PNG or WebP",
  banner: "JPG, PNG or WebP",
  document: "PDF, DOC or DOCX",
};

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function validateFile(file: File, kind: UploadKind): string | null {
  if (!ACCEPTED_TYPES[kind].includes(file.type)) {
    return `That file type is not supported. Use ${TYPE_LABELS[kind]}.`;
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return `That file is ${formatBytes(file.size)}. The limit is ${formatBytes(
      MAX_UPLOAD_BYTES,
    )}.`;
  }
  return null;
}

export async function uploadFile(
  file: File,
  kind: UploadKind,
): Promise<UploadedFile> {
  const problem = validateFile(file, kind);
  if (problem) {
    throw new Error(problem);
  }

  const { data } = await http.post<{ data: PresignedUpload }>(
    "/uploads/presign",
    { kind, content_type: file.type, filename: file.name },
  );
  const presigned = data.data;

  const form = new FormData();
  Object.entries(presigned.fields).forEach(([key, value]) => {
    form.append(key, String(value));
  });
  form.append("file", file);

  const response = await fetch(presigned.upload_url, {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    throw new Error("The file could not be uploaded to storage.");
  }

  return { file_url: presigned.file_url, object_key: presigned.object_key };
}

export function uploadBanner(file: File): Promise<UploadedFile> {
  return uploadFile(file, "banner");
}
