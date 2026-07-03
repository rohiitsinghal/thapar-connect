const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type TimetableSlot = {
  slot_index: number;
  day: string;
  start: string;
  end: string;
  is_lunch: boolean;
};

export type TimetableClassEntry = {
  unit_id: string;
  course_code: string;
  title: string;
  credits: number;
  type: "lecture" | "tutorial" | "practical" | string;
  slots: number;
  day: string;
  start: string;
  end: string;
  slot_index: number;
  room_id: string;
  room_type: string;
  capacity: number;
  teacher: string;
};

export type StudentTimetable = {
  enrollment_no: string;
  name: string;
  email: string;
  major: string;
  minor: string;
  semester: number;
  classes: TimetableClassEntry[];
};

export type TimetablePayload = {
  meta: {
    total_classes: number;
    total_students: number;
    days: string[];
    slots_per_day: number;
    slot_duration_minutes: number;
    timeslots: TimetableSlot[];
  };
  timetable: TimetableClassEntry[];
  by_day: Record<string, TimetableClassEntry[]>;
  by_student: Record<string, StudentTimetable>;
};

export type GenerateTimetableRequest = {
  active_parity?: "even" | "odd";
};

export const fetchLatestTimetable = async (): Promise<TimetablePayload> => {
  const response = await fetch(`${API_BASE_URL}/timetable/latest`);
  if (!response.ok) {
    throw new Error(`Failed to fetch timetable: ${response.status}`);
  }

  return response.json() as Promise<TimetablePayload>;
};

export const generateTimetable = async (payload: GenerateTimetableRequest = {}): Promise<TimetablePayload> => {
  const response = await fetch(`${API_BASE_URL}/timetable/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Failed to generate timetable: ${response.status}`);
  }

  const data = await response.json() as { timetable?: TimetablePayload };
  if (!data.timetable) {
    throw new Error("Invalid timetable generation response");
  }

  return data.timetable;
};
