import * as XLSX from "xlsx";

export type PeopleRole = "student" | "faculty";

export type PeopleProfile = {
  role: PeopleRole;
  primaryId: string;
  displayName: string;
  email: string;
  sourceSheet: string;
  loginAliases: string[];
  details: Record<string, string>;
};

export type PeopleData = {
  students: PeopleProfile[];
  faculty: PeopleProfile[];
};

type WorkbookRow = Record<string, unknown>;

const studentWorkbookUrl = new URL("../../data/Students List  (4).xlsx", import.meta.url).href;
const facultyWorkbookUrl = new URL("../../data/FACULTY DETAILS - TSLAS.xlsx", import.meta.url).href;

let peopleDataPromise: Promise<PeopleData> | null = null;
let peopleDataCache: PeopleData | null = null;

const normalizeLookup = (value: string): string => value.trim().toUpperCase().replace(/\s+/g, " ");

const toText = (value: unknown): string => {
  if (value === null || value === undefined) {
    return "";
  }

  return String(value).trim();
};

const normalizeKey = (value: string): string => value.trim().toLowerCase().replace(/\s+/g, " ");

const collectDetails = (row: WorkbookRow): Record<string, string> =>
  Object.entries(row).reduce<Record<string, string>>((accumulator, [key, value]) => {
    const text = toText(value);
    if (text) {
      accumulator[key.trim()] = text;
    }

    return accumulator;
  }, {});

const getValue = (details: Record<string, string>, candidates: string[]): string => {
  const normalizedCandidates = candidates.map(normalizeKey);

  for (const [key, value] of Object.entries(details)) {
    if (normalizedCandidates.includes(normalizeKey(key))) {
      return value;
    }
  }

  return "";
};

const createAliases = (...values: Array<string | null | undefined>): string[] => {
  const aliases = values
    .map((value) => toText(value))
    .filter((value) => value.length > 0)
    .map((value) => normalizeLookup(value));

  return Array.from(new Set(aliases));
};

const createStudentProfile = (sheetName: string, row: WorkbookRow): PeopleProfile | null => {
  const details = collectDetails(row);
  const rollNo = getValue(details, ["Roll No", "Roll No.", "Enrollment Number", "Enrollment No", "Enrollment No."]);
  const name = getValue(details, ["Name", "Student Name"]);
  const email = getValue(details, ["Email Address", "Email", "Email ID", "Email Id"]);

  if (!rollNo || !name) {
    return null;
  }

  return {
    role: "student",
    primaryId: rollNo,
    displayName: name,
    email,
    sourceSheet: sheetName,
    loginAliases: createAliases(rollNo, email),
    details,
  };
};

const createFacultyProfile = (sheetName: string, row: WorkbookRow): PeopleProfile | null => {
  const details = collectDetails(row);
  const employeeCode = getValue(details, ["Empolyee Code", "Employee Code", "Emp Code", "Employee No"]);
  const teacherCode = getValue(details, ["Teacher Code"]);
  const name = getValue(details, ["Name of Faculty Name", "Name of Faculty", "Faculty Name", "Name"]);
  const email = getValue(details, ["Email", "Email Address"]);

  const primaryId = employeeCode || email || teacherCode;

  if (!primaryId || !name) {
    return null;
  }

  return {
    role: "faculty",
    primaryId,
    displayName: name,
    email,
    sourceSheet: sheetName,
    loginAliases: createAliases(primaryId, employeeCode, teacherCode, email),
    details,
  };
};

const parseWorkbook = async (url: string, role: PeopleRole): Promise<PeopleProfile[]> => {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Unable to load workbook from ${url}`);
  }

  const buffer = await response.arrayBuffer();
  const workbook = XLSX.read(buffer, { type: "array" });

  return workbook.SheetNames.flatMap((sheetName) => {
    const sheet = workbook.Sheets[sheetName];
    if (!sheet) {
      return [];
    }

    const rows = XLSX.utils.sheet_to_json<WorkbookRow>(sheet, { defval: "" });
    return rows
      .map((row) => (role === "student" ? createStudentProfile(sheetName, row) : createFacultyProfile(sheetName, row)))
      .filter((profile): profile is PeopleProfile => Boolean(profile));
  });
};

export const getPeopleData = (): Promise<PeopleData> => {
  if (!peopleDataPromise) {
    peopleDataPromise = Promise.all([
      parseWorkbook(studentWorkbookUrl, "student"),
      parseWorkbook(facultyWorkbookUrl, "faculty"),
    ])
      .then(([students, faculty]) => {
        const resolvedData = { students, faculty };
        peopleDataCache = resolvedData;
        return resolvedData;
      })
      .catch((error) => {
        peopleDataPromise = null;
        throw error;
      });
  }

  return peopleDataPromise;
};

export const getCachedPeopleData = (): PeopleData | null => peopleDataCache;

const findProfileByIdentifier = (profiles: PeopleProfile[], identifier: string): PeopleProfile | null => {
  const normalizedIdentifier = normalizeLookup(identifier);
  return profiles.find((profile) => profile.loginAliases.some((alias) => alias === normalizedIdentifier)) ?? null;
};

export const findStudentProfile = (data: PeopleData, identifier: string): PeopleProfile | null =>
  findProfileByIdentifier(data.students, identifier);

export const findFacultyProfile = (data: PeopleData, identifier: string): PeopleProfile | null =>
  findProfileByIdentifier(data.faculty, identifier);

export const findPersonProfile = (data: PeopleData, identifier: string): PeopleProfile | null =>
  findStudentProfile(data, identifier) ?? findFacultyProfile(data, identifier);
