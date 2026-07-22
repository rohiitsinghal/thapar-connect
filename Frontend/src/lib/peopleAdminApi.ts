const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type PeopleAdminRole = "students" | "faculty";

export type StudentRecord = {
  roll_no: string;
  name: string;
  email: string;
  major: string;
  minor: string;
  [key: string]: unknown;
};

export type FacultyRecord = {
  employee_code: string;
  name: string;
  teacher_code: string;
  designation: string;
  email: string;
  [key: string]: unknown;
};

export type PersonRecord = StudentRecord | FacultyRecord;

class PeopleAdminError extends Error {}

const readErrorDetail = async (response: Response): Promise<string> => {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? response.statusText;
  } catch {
    return response.statusText;
  }
};

const authHeaders = (token: string): Record<string, string> => ({ Authorization: `Bearer ${token}` });

export const fetchStudents = async (token: string): Promise<StudentRecord[]> => {
  const response = await fetch(`${API_BASE_URL}/admin/people/students`, { headers: authHeaders(token) });
  if (!response.ok) {
    throw new PeopleAdminError(await readErrorDetail(response));
  }
  const body = (await response.json()) as { students: StudentRecord[] };
  return body.students;
};

export const fetchFaculty = async (token: string): Promise<FacultyRecord[]> => {
  const response = await fetch(`${API_BASE_URL}/admin/people/faculty`, { headers: authHeaders(token) });
  if (!response.ok) {
    throw new PeopleAdminError(await readErrorDetail(response));
  }
  const body = (await response.json()) as { faculty: FacultyRecord[] };
  return body.faculty;
};

export const uploadStudentsFile = async (file: File, token: string): Promise<{ written: number; count: number }> => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/admin/people/students/upload`, {
    method: "POST",
    headers: authHeaders(token),
    body: formData,
  });

  if (!response.ok) {
    throw new PeopleAdminError(await readErrorDetail(response));
  }

  return (await response.json()) as { written: number; count: number };
};

export const uploadFacultyFile = async (file: File, token: string): Promise<{ written: number; count: number }> => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/admin/people/faculty/upload`, {
    method: "POST",
    headers: authHeaders(token),
    body: formData,
  });

  if (!response.ok) {
    throw new PeopleAdminError(await readErrorDetail(response));
  }

  return (await response.json()) as { written: number; count: number };
};

export const updateStudent = async (
  rollNo: string,
  fields: Record<string, string>,
  token: string,
): Promise<StudentRecord> => {
  const response = await fetch(`${API_BASE_URL}/admin/people/students/${encodeURIComponent(rollNo)}`, {
    method: "PUT",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ fields }),
  });

  if (!response.ok) {
    throw new PeopleAdminError(await readErrorDetail(response));
  }

  const body = (await response.json()) as { student: StudentRecord };
  return body.student;
};

export const updateFaculty = async (
  employeeCode: string,
  fields: Record<string, string>,
  token: string,
): Promise<FacultyRecord> => {
  const response = await fetch(`${API_BASE_URL}/admin/people/faculty/${encodeURIComponent(employeeCode)}`, {
    method: "PUT",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ fields }),
  });

  if (!response.ok) {
    throw new PeopleAdminError(await readErrorDetail(response));
  }

  const body = (await response.json()) as { faculty: FacultyRecord };
  return body.faculty;
};

export const deleteStudent = async (rollNo: string, token: string): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/admin/people/students/${encodeURIComponent(rollNo)}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });

  if (!response.ok) {
    throw new PeopleAdminError(await readErrorDetail(response));
  }
};

export const deleteFaculty = async (employeeCode: string, token: string): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/admin/people/faculty/${encodeURIComponent(employeeCode)}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });

  if (!response.ok) {
    throw new PeopleAdminError(await readErrorDetail(response));
  }
};
