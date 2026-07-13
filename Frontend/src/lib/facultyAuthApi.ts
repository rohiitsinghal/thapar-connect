const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type FacultyLoginResult = {
  token: string;
  employee_code: string;
  teacher_code: string;
  name: string;
  designation: string;
  email: string;
  must_change_password: boolean;
};

class FacultyAuthError extends Error {}

const readErrorDetail = async (response: Response): Promise<string> => {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? response.statusText;
  } catch {
    return response.statusText;
  }
};

export const loginFaculty = async (employeeCode: string, password: string): Promise<FacultyLoginResult> => {
  const response = await fetch(`${API_BASE_URL}/auth/faculty/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ employee_code: employeeCode, password }),
  });

  if (!response.ok) {
    throw new FacultyAuthError(await readErrorDetail(response));
  }

  return (await response.json()) as FacultyLoginResult;
};

export const changeFacultyPassword = async (
  token: string,
  currentPassword: string,
  newPassword: string,
): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/auth/faculty/change-password`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });

  if (!response.ok) {
    throw new FacultyAuthError(await readErrorDetail(response));
  }
};
