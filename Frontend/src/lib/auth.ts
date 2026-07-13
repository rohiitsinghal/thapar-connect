export const AUTH_SESSION_KEY = "thapartime_user_session";
const AUTH_PASSWORDS_KEY = "thapartime_password_overrides";

export type UserRole = "admin" | "instructor" | "student";
export type AuthRole = Exclude<UserRole, "admin">;

export type UserSession = {
  role: UserRole;
  displayName: string;
  identifier: string;
  /** JWT issued by the backend. Only set for roles authenticated against DynamoDB (currently: student). */
  token?: string;
};

const DEFAULT_PASSWORDS: Record<AuthRole, string> = {
  student: "12345",
  instructor: "tiet12345",
};

type PasswordOverrides = Partial<Record<string, string>>;

const normalizeIdentifier = (identifier: string): string => identifier.trim().toUpperCase();

const buildPasswordKey = (role: AuthRole, identifier: string): string =>
  `${role}:${normalizeIdentifier(identifier)}`;

const readPasswordOverrides = (): PasswordOverrides => {
  if (typeof window === "undefined") {
    return {};
  }

  const rawValue = window.localStorage.getItem(AUTH_PASSWORDS_KEY);
  if (!rawValue) {
    return {};
  }

  try {
    return JSON.parse(rawValue) as PasswordOverrides;
  } catch {
    window.localStorage.removeItem(AUTH_PASSWORDS_KEY);
    return {};
  }
};

const writePasswordOverrides = (overrides: PasswordOverrides): void => {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(AUTH_PASSWORDS_KEY, JSON.stringify(overrides));
};

export const getDefaultPassword = (role: AuthRole): string => DEFAULT_PASSWORDS[role];

export const getEffectivePassword = (role: AuthRole, identifier: string): string => {
  const overrides = readPasswordOverrides();
  return overrides[buildPasswordKey(role, identifier)] ?? getDefaultPassword(role);
};

export const verifyPassword = (role: AuthRole, identifier: string, password: string): boolean =>
  getEffectivePassword(role, identifier) === password;

export const setPasswordForUser = (role: AuthRole, identifier: string, password: string): void => {
  if (typeof window === "undefined") {
    return;
  }

  const overrides = readPasswordOverrides();
  overrides[buildPasswordKey(role, identifier)] = password;
  writePasswordOverrides(overrides);
};

export const getUserSession = (): UserSession | null => {
  if (typeof window === "undefined") {
    return null;
  }

  const rawSession = window.localStorage.getItem(AUTH_SESSION_KEY);
  if (!rawSession) {
    return null;
  }

  try {
    return JSON.parse(rawSession) as UserSession;
  } catch {
    window.localStorage.removeItem(AUTH_SESSION_KEY);
    return null;
  }
};

export const setUserSession = (session: UserSession): void => {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(session));
};

export const clearUserSession = (): void => {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(AUTH_SESSION_KEY);
};