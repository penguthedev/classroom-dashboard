import { Cloudinary } from "@cloudinary/url-gen";
import { autoGravity } from "@cloudinary/url-gen/qualifiers/gravity";
import { fill } from "@cloudinary/url-gen/actions/resize";

import { CLOUDINARY_CLOUD_NAME, CLOUDINARY_UPLOAD_PRESET } from "@/constants";

const cld = new Cloudinary({
  cloud: { cloudName: CLOUDINARY_CLOUD_NAME },
});

/** Returns a transformed, auto-optimized banner image for a given Cloudinary public_id. */
export function getBannerImage(publicId: string, width = 800, height = 400) {
  return cld
    .image(publicId)
    .resize(fill().width(width).height(height).gravity(autoGravity()))
    .format("auto")
    .quality("auto");
}

interface CloudinaryUploadResult {
  secure_url: string;
  public_id: string;
}

/**
 * Uploads a file directly from the browser to Cloudinary using an UNSIGNED
 * upload preset. The backend never sees the file — only the resulting
 * secure_url / public_id, which get POSTed along with the rest of the form.
 */
export async function uploadToCloudinary(
  file: File,
): Promise<CloudinaryUploadResult> {
  if (!CLOUDINARY_CLOUD_NAME || !CLOUDINARY_UPLOAD_PRESET) {
    throw new Error(
      "Cloudinary is not configured. Set VITE_CLOUDINARY_CLOUD_NAME and VITE_CLOUDINARY_UPLOAD_PRESET.",
    );
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("upload_preset", CLOUDINARY_UPLOAD_PRESET);

  const response = await fetch(
    `https://api.cloudinary.com/v1_1/${CLOUDINARY_CLOUD_NAME}/image/upload`,
    { method: "POST", body: formData },
  );

  if (!response.ok) {
    throw new Error("Cloudinary upload failed. Check the preset is unsigned.");
  }

  const json = (await response.json()) as CloudinaryUploadResult;
  return { secure_url: json.secure_url, public_id: json.public_id };
}
