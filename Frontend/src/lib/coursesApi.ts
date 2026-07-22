const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type CourseRecord = {
  course_code: string;
  semester: string;
  title: string;
  credits: number;
  facultyName: string;
  facultyCode: string;
  programs: string[];
  categories: string[];
};

export type RosterStudent = {
  roll_no: string;
  name: string;
  email: string;
  major: string;
  minor: string;
};

class CoursesError extends Error {}

const readErrorDetail = async (response: Response): Promise<string> => {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? response.statusText;
  } catch {
    return response.statusText;
  }
};

export const fetchCourseCatalog = async (): Promise<CourseRecord[]> => {
  const response = await fetch(`${API_BASE_URL}/courses`);

  if (!response.ok) {
    throw new CoursesError(await readErrorDetail(response));
  }

  const body = (await response.json()) as { courses: CourseRecord[] };
  return body.courses;
};

export const fetchCourseRoster = async (courseCode: string, token: string): Promise<RosterStudent[]> => {
  const response = await fetch(`${API_BASE_URL}/courses/${encodeURIComponent(courseCode)}/roster`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    throw new CoursesError(await readErrorDetail(response));
  }

  const body = (await response.json()) as { students: RosterStudent[] };
  return body.students;
};
