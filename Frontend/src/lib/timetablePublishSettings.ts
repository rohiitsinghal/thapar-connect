export const TIMETABLE_PUBLISH_SETTINGS_KEY = "thapartime_timetable_publish_settings";

export type TimetablePublishSettings = {
  semesterWeeks: number;
  semesterStartDate: string;
  semesterEndDate: string;
  publishedAt: string;
};

const DEFAULT_SEMESTER_WEEKS = 16;
const MIN_SEMESTER_WEEKS = 1;
const MAX_SEMESTER_WEEKS = 52;
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const toDateInput = (value: Date): string => {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const getDefaultStartDate = (): string => {
  const today = new Date();
  const date = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const daysUntilMonday = (8 - date.getDay()) % 7;
  date.setDate(date.getDate() + daysUntilMonday);
  return toDateInput(date);
};

const addDays = (dateValue: string, days: number): string => {
  const [year, month, day] = dateValue.split("-").map(Number);
  if (!year || !month || !day) {
    return dateValue;
  }
  const date = new Date(year, month - 1, day);
  date.setDate(date.getDate() + days);
  return toDateInput(date);
};

const DEFAULT_START_DATE = getDefaultStartDate();
const DEFAULT_END_DATE = addDays(DEFAULT_START_DATE, (DEFAULT_SEMESTER_WEEKS * 7) - 1);

const parseDateInput = (value: string): Date | null => {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) {
    return null;
  }
  const parsed = new Date(year, month - 1, day);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed;
};

const normalizeDateInput = (value: string, fallback: string): string => {
  const parsed = parseDateInput(value);
  return parsed ? toDateInput(parsed) : fallback;
};

export const deriveSemesterWeeksFromDateRange = (startDate: string, endDate: string): number => {
  const start = parseDateInput(startDate);
  const end = parseDateInput(endDate);

  if (!start || !end) {
    return DEFAULT_SEMESTER_WEEKS;
  }

  if (end < start) {
    return DEFAULT_SEMESTER_WEEKS;
  }

  const diffInMs = end.getTime() - start.getTime();
  const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24)) + 1;
  return clampSemesterWeeks(Math.ceil(diffInDays / 7));
};

const clampSemesterWeeks = (value: number): number => {
  if (!Number.isFinite(value)) {
    return DEFAULT_SEMESTER_WEEKS;
  }

  return Math.min(MAX_SEMESTER_WEEKS, Math.max(MIN_SEMESTER_WEEKS, Math.round(value)));
};

export const getTimetablePublishSettings = (): TimetablePublishSettings => {
  if (typeof window === "undefined") {
    return {
      semesterWeeks: DEFAULT_SEMESTER_WEEKS,
      semesterStartDate: DEFAULT_START_DATE,
      semesterEndDate: DEFAULT_END_DATE,
      publishedAt: "",
    };
  }

  const raw = window.localStorage.getItem(TIMETABLE_PUBLISH_SETTINGS_KEY);
  if (!raw) {
    return {
      semesterWeeks: DEFAULT_SEMESTER_WEEKS,
      semesterStartDate: DEFAULT_START_DATE,
      semesterEndDate: DEFAULT_END_DATE,
      publishedAt: "",
    };
  }

  try {
    const parsed = JSON.parse(raw) as Partial<TimetablePublishSettings>;
    const semesterStartDate = normalizeDateInput(
      typeof parsed.semesterStartDate === "string" ? parsed.semesterStartDate : "",
      DEFAULT_START_DATE,
    );
    const semesterEndDate = normalizeDateInput(
      typeof parsed.semesterEndDate === "string" ? parsed.semesterEndDate : "",
      DEFAULT_END_DATE,
    );

    return {
      semesterWeeks: deriveSemesterWeeksFromDateRange(semesterStartDate, semesterEndDate),
      semesterStartDate,
      semesterEndDate,
      publishedAt: typeof parsed.publishedAt === "string" ? parsed.publishedAt : "",
    };
  } catch {
    window.localStorage.removeItem(TIMETABLE_PUBLISH_SETTINGS_KEY);
    return {
      semesterWeeks: DEFAULT_SEMESTER_WEEKS,
      semesterStartDate: DEFAULT_START_DATE,
      semesterEndDate: DEFAULT_END_DATE,
      publishedAt: "",
    };
  }
};

const saveLocalTimetablePublishSettings = (settings: TimetablePublishSettings): void => {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(TIMETABLE_PUBLISH_SETTINGS_KEY, JSON.stringify(settings));
};

const readRemoteSettingsPayload = (payload: unknown): TimetablePublishSettings | null => {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const record = payload as Record<string, unknown>;
  const semesterStartDate = normalizeDateInput(
    typeof record.semester_start_date === "string" ? record.semester_start_date : "",
    DEFAULT_START_DATE,
  );
  const semesterEndDate = normalizeDateInput(
    typeof record.semester_end_date === "string" ? record.semester_end_date : "",
    DEFAULT_END_DATE,
  );
  const semesterWeeks = deriveSemesterWeeksFromDateRange(semesterStartDate, semesterEndDate);
  const publishedAt = typeof record.published_at === "string" ? record.published_at : "";
  return { semesterWeeks, semesterStartDate, semesterEndDate, publishedAt };
};

export const fetchTimetablePublishSettings = async (): Promise<TimetablePublishSettings> => {
  try {
    const response = await fetch(`${API_BASE_URL}/timetable-settings/publish`);
    if (!response.ok) {
      throw new Error(`Failed to fetch publish settings: ${response.status}`);
    }

    const payload = readRemoteSettingsPayload(await response.json());
    if (!payload) {
      throw new Error("Invalid publish settings payload");
    }

    saveLocalTimetablePublishSettings(payload);
    return payload;
  } catch {
    return getTimetablePublishSettings();
  }
};

export const publishTimetableSettings = async (
  semesterWeeks: number,
  semesterStartDate: string,
  semesterEndDate: string,
): Promise<TimetablePublishSettings> => {
  const normalizedStartDate = normalizeDateInput(semesterStartDate, DEFAULT_START_DATE);
  const normalizedEndDate = normalizeDateInput(semesterEndDate, DEFAULT_END_DATE);

  const nextSettings: TimetablePublishSettings = {
    semesterWeeks: deriveSemesterWeeksFromDateRange(normalizedStartDate, normalizedEndDate),
    semesterStartDate: normalizedStartDate,
    semesterEndDate: normalizedEndDate,
    publishedAt: new Date().toISOString(),
  };

  try {
    const response = await fetch(`${API_BASE_URL}/timetable-settings/publish`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        semester_weeks: nextSettings.semesterWeeks,
        semester_start_date: nextSettings.semesterStartDate,
        semester_end_date: nextSettings.semesterEndDate,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to publish settings: ${response.status}`);
    }

    const payload = readRemoteSettingsPayload(await response.json());
    if (!payload) {
      throw new Error("Invalid publish settings response");
    }

    saveLocalTimetablePublishSettings(payload);
    return payload;
  } catch {
    saveLocalTimetablePublishSettings(nextSettings);
    return nextSettings;
  }
};
