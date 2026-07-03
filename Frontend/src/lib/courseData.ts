import * as XLSX from "xlsx";
import { PeopleProfile } from "@/lib/peopleData";

export type CourseCatalogItem = {
  courseCode: string;
  title: string;
  semester: number;
  credits: number;
  facultyName: string;
  facultyCode: string;
  programs: string[];
  categories: string[];
  remarks: string[];
};

type WorkbookRow = Record<string, unknown>;

const courseWorkbookUrl = new URL("../../data/COURSE WISE SHEET.xlsx", import.meta.url).href;

let courseCatalogPromise: Promise<CourseCatalogItem[]> | null = null;

const STOP_WORDS = new Set(["AND", "OF", "THE", "FOR", "IN", "TO", "A", "AN"]);

const toText = (value: unknown): string => {
  if (value === null || value === undefined) {
    return "";
  }

  return String(value).trim();
};

const normalizeLookup = (value: string): string => value.trim().toUpperCase().replace(/\s+/g, " ");

const normalizePhrase = (value: string): string =>
  value
    .replace(/&/g, " ")
    .replace(/[^a-z0-9]+/gi, " ")
    .toUpperCase()
    .split(" ")
    .filter((segment) => segment.length > 1 && !STOP_WORDS.has(segment))
    .join(" ");

const normalizeKey = (value: string): string => value.trim().toLowerCase().replace(/\s+/g, " ");

const parseRomanNumeral = (value: string): number | null => {
  const roman = normalizeLookup(value);
  const map: Record<string, number> = { I: 1, V: 5, X: 10 };
  let total = 0;
  let previous = 0;

  for (let index = roman.length - 1; index >= 0; index -= 1) {
    const current = map[roman[index]];
    if (!current) {
      return null;
    }

    if (current < previous) {
      total -= current;
    } else {
      total += current;
      previous = current;
    }
  }

  return total > 0 ? total : null;
};

const inferSemesterFromSheet = (sheetName: string): number | null => {
  const normalizedName = sheetName.trim();

  if (/foundation/i.test(normalizedName)) {
    return 1;
  }

  const explicitNumberMatch = normalizedName.match(/\b(\d{1,2})\s*(?:ST|ND|RD|TH)?\s*SEM/i);
  if (explicitNumberMatch?.[1]) {
    return Number.parseInt(explicitNumberMatch[1], 10);
  }

  const romanMatch = normalizedName.match(/\b([IVX]{1,4})\b/i);
  if (romanMatch?.[1]) {
    return parseRomanNumeral(romanMatch[1]);
  }

  return null;
};

const buildRowObject = (headers: string[], rowValues: unknown[]): WorkbookRow =>
  headers.reduce<WorkbookRow>((accumulator, header, index) => {
    accumulator[header] = toText(rowValues[index]);
    return accumulator;
  }, {});

const normalizeCourseKey = (courseCode: string, semester: number, title: string): string =>
  `${normalizeLookup(courseCode)}|${semester}|${normalizeLookup(title)}`;

const buildCourseSearchText = (course: CourseCatalogItem): string =>
  normalizePhrase(
    [course.courseCode, course.title, course.facultyName, course.facultyCode, ...course.programs, ...course.categories, ...course.remarks]
      .filter((value) => value.length > 0)
      .join(" ")
  );

const getStudentStudyAreas = (profile: PeopleProfile): string[] => {
  const rawValues = [profile.details["Major"], profile.details["Minor"], profile.details["Degree Name"], profile.details["Program"]]
    .filter((value): value is string => Boolean(value))
    .flatMap((value) => value.split(/[/,&|]+/g));

  return Array.from(new Set(rawValues.map((value) => normalizePhrase(value)).filter((value) => value.length > 0)));
};

const parseCatalog = async (): Promise<CourseCatalogItem[]> => {
  const response = await fetch(courseWorkbookUrl);
  if (!response.ok) {
    throw new Error(`Unable to load workbook from ${courseWorkbookUrl}`);
  }

  const buffer = await response.arrayBuffer();
  const workbook = XLSX.read(buffer, { type: "array" });
  const courseMap = new Map<string, CourseCatalogItem>();

  workbook.SheetNames.forEach((sheetName) => {
    const sheet = workbook.Sheets[sheetName];
    if (!sheet) {
      return;
    }

    const rows = XLSX.utils.sheet_to_json<unknown[]>(sheet, { header: 1, defval: "" }) as unknown[][];
    const headerRowIndex = rows.findIndex((row) =>
      row.some((cell) => normalizeKey(toText(cell)) === "course code")
    );

    if (headerRowIndex === -1) {
      return;
    }

    const headers = rows[headerRowIndex].map((cell) => toText(cell));
    let currentProgram = "";

    for (const rowValues of rows.slice(headerRowIndex + 1)) {
      if (!rowValues.some((cell) => toText(cell).length > 0)) {
        continue;
      }

      const row = buildRowObject(headers, rowValues);
      const courseCode = toText(row["Course Code"]);
      const title = toText(row["TITLE"] || row["Title"]);
      const semester = Number.parseInt(toText(row["Sem"]), 10);

      if (!courseCode || !title || Number.isNaN(semester)) {
        continue;
      }

      const program = toText(row["Program"]) || currentProgram;
      if (program) {
        currentProgram = program;
      }

      const key = normalizeCourseKey(courseCode, semester, title);
      const existing = courseMap.get(key);
      const credits = Number.parseInt(toText(row["Cr"]), 10) || 0;
      const facultyName = toText(row["Faculty Names"]);
      const facultyCode = toText(row["Faculty Codes"]);
      const category = toText(row["Major /Minor"]);
      const remarks = toText(row["Remarks"]);

      if (existing) {
        existing.programs = Array.from(new Set([...existing.programs, ...(program ? [program] : [])]));
        existing.categories = Array.from(new Set([...existing.categories, ...(category ? [category] : [])]));
        existing.remarks = Array.from(new Set([...existing.remarks, ...(remarks ? [remarks] : [])]));
        if (!existing.facultyName && facultyName) {
          existing.facultyName = facultyName;
        }
        if (!existing.facultyCode && facultyCode) {
          existing.facultyCode = facultyCode;
        }
        if (!existing.credits && credits) {
          existing.credits = credits;
        }
        continue;
      }

      courseMap.set(key, {
        courseCode,
        title,
        semester,
        credits,
        facultyName,
        facultyCode,
        programs: program ? [program] : [],
        categories: category ? [category] : [],
        remarks: remarks ? [remarks] : [],
      });
    }
  });

  return Array.from(courseMap.values()).sort((left, right) => {
    if (left.semester !== right.semester) {
      return left.semester - right.semester;
    }

    return left.courseCode.localeCompare(right.courseCode);
  });
};

export const getCourseCatalog = (): Promise<CourseCatalogItem[]> => {
  if (!courseCatalogPromise) {
    courseCatalogPromise = parseCatalog();
  }

  return courseCatalogPromise;
};

export const inferStudentSemester = (profile: PeopleProfile): number | null => inferSemesterFromSheet(profile.sourceSheet);

const normalizePersonName = (value: string): string => normalizeLookup(value);

const courseMatchesStudyAreas = (course: CourseCatalogItem, studyAreas: string[]): boolean => {
  if (studyAreas.length === 0) {
    return false;
  }

  const courseSearchText = buildCourseSearchText(course);
  return studyAreas.some((studyArea) => courseSearchText.includes(studyArea));
};

const getFacultySearchTerms = (profile: PeopleProfile): string[] => {
  const details = profile.details;
  const terms = [
    profile.displayName,
    profile.primaryId,
    profile.email,
    profile.loginAliases.join(" "),
    details["Teacher Code"],
    details["Teacher code"],
    details["Teacher CODE"],
    details["Teacher Code "],
    details["Teacher Code"],
    details["Name of Faculty Name"],
    details["Name of Faculty Name "],
    details["Name of Faculty"],
    details["Faculty Name"],
    details["Name"],
  ]
    .filter((value): value is string => Boolean(value))
    .map((value) => normalizePhrase(value))
    .filter((value) => value.length > 0);

  return Array.from(new Set(terms));
};

const courseMatchesFaculty = (course: CourseCatalogItem, profile: PeopleProfile): boolean => {
  const courseSearchText = buildCourseSearchText(course);
  const facultyTerms = getFacultySearchTerms(profile);

  return facultyTerms.some((term) => courseSearchText.includes(term));
};

export const getCoursesForStudent = (catalog: CourseCatalogItem[], profile: PeopleProfile | null): CourseCatalogItem[] => {
  if (!profile) {
    return catalog;
  }

  const semester = inferStudentSemester(profile);
  if (!semester) {
    return catalog;
  }

  const studyAreas = getStudentStudyAreas(profile);
  const semesterMatches = catalog.filter((course) => course.semester === semester);
  const mappedCourses = semesterMatches.filter((course) => courseMatchesStudyAreas(course, studyAreas));

  return mappedCourses.length > 0 ? mappedCourses : semesterMatches;
};

export const getCoursesForFaculty = (catalog: CourseCatalogItem[], profile: PeopleProfile | null): CourseCatalogItem[] => {
  if (!profile) {
    return [];
  }

  const matches = catalog.filter((course) => courseMatchesFaculty(course, profile));
  return matches;
};

export const getCoursesForAdmin = (catalog: CourseCatalogItem[]): CourseCatalogItem[] => catalog;