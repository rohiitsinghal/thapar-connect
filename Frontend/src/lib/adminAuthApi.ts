const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type AdminLoginResult = {
  token: string;
};

class AdminAuthError extends Error {}

const readErrorDetail = async (response: Response): Promise<string> => {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? response.statusText;
  } catch {
    return response.statusText;
  }
};

export const loginAdmin = async (email: string, password: string): Promise<AdminLoginResult> => {
  const response = await fetch(`${API_BASE_URL}/auth/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    throw new AdminAuthError(await readErrorDetail(response));
  }

  return (await response.json()) as AdminLoginResult;
};
