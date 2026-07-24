const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type CourseMaterialItem = {
  material_id: string;
  title: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
  uploaded_by_name: string;
  uploaded_at: string; 
};

class CourseMaterialError extends Error {}

const readErrorDetail = async (response: Response): Promise<string> => {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? response.statusText;
  } catch {
    return response.statusText;
  }
};

export const listCourseMaterial = async (courseCode: string, token: string): Promise<CourseMaterialItem[]> => {
  const response = await fetch(`${API_BASE_URL}/course-material/${encodeURIComponent(courseCode)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    throw new CourseMaterialError(await readErrorDetail(response));
  }

  const body = (await response.json()) as { materials: CourseMaterialItem[] };
  return body.materials;
};

export const uploadCourseMaterial = async (
  courseCode: string,
  title: string,
  file: File,
  token: string,
): Promise<CourseMaterialItem> => {
  const formData = new FormData();
  formData.append("title", title);
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/course-material/${encodeURIComponent(courseCode)}/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });

  if (!response.ok) {
    throw new CourseMaterialError(await readErrorDetail(response));
  }

  return (await response.json()) as CourseMaterialItem;
};

export const downloadCourseMaterial = async (
  courseCode: string,
  materialId: string,
  fileName: string,
  token: string,
): Promise<void> => {
  const response = await fetch(
    `${API_BASE_URL}/course-material/${encodeURIComponent(courseCode)}/${encodeURIComponent(materialId)}/download`,
    { headers: { Authorization: `Bearer ${token}` } },
  );

  if (!response.ok) {
    throw new CourseMaterialError(await readErrorDetail(response));
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
};

export const deleteCourseMaterial = async (courseCode: string, materialId: string, token: string): Promise<void> => {
  const response = await fetch(
    `${API_BASE_URL}/course-material/${encodeURIComponent(courseCode)}/${encodeURIComponent(materialId)}`,
    {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    },
  );

  if (!response.ok) {
    throw new CourseMaterialError(await readErrorDetail(response));
  }
};
