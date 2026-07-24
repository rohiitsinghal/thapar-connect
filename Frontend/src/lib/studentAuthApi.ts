const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type StudentLoginResult = {
  token: string;
  roll_no: string;
  name: string;
  email: string;
  major: string;
  minor: string;
  must_change_password: boolean;
};  

class StudentAuthError extends Error {}

const readErrorDetail = async (response: Response): Promise<string> => {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? response.statusText;
  } catch {
    return response.statusText;
  }
};

export const loginStudent = async (rollNo: string, password: string): Promise<StudentLoginResult> => {
  const response = await fetch(`${API_BASE_URL}/auth/student/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ roll_no: rollNo, password }),
  });

  if (!response.ok) {
    throw new StudentAuthError(await readErrorDetail(response));
  }

  return (await response.json()) as StudentLoginResult;
};

export const changeStudentPassword = async (
  token: string,
  currentPassword: string,
  newPassword: string,
): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/auth/student/change-password`, {
    method: "POST", 
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });

  if (!response.ok) {
    throw new StudentAuthError(await readErrorDetail(response));
  }
};
