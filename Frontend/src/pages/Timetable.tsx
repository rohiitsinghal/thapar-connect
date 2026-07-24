import { useEffect, useMemo, useRef, useState } from "react";
import html2canvas from "html2canvas";
import {
  CheckCircle2,
  Download,
  FileSpreadsheet,
  FileUp,
  ImageDown,
  Pencil,
  RefreshCw,
  Sparkles,
  Undo2,
  Upload,
  XCircle,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import Footer from "@/components/Footer";
import { getUserSession } from "@/lib/auth";
import { findFacultyProfile, getPeopleData } from "@/lib/peopleData";
import { getCourseCatalog, getCoursesForFaculty } from "@/lib/courseData";
import {
  deriveSemesterWeeksFromDateRange,
  fetchTimetablePublishSettings,
  getTimetablePublishSettings,
  publishTimetableSettings,
} from "@/lib/timetablePublishSettings";
import {
  fetchLatestTimetable,
  fetchMasterTimetableXlsx,
  generateTimetable,
  type TimetableClassEntry,
  type TimetablePayload,
} from "@/lib/timetableApi";

// NOTE: this should match whatever base URL `src/lib/timetableApi.ts` uses
// to talk to api_server.py. If that file exports a constant (e.g. API_BASE
// or API_BASE_URL), import and reuse it instead of this local copy so the
// two never drift apart.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type StudentCellOverride = {
  customText: string;
  hideOriginal: boolean;
};

// Field name is what the backend matches on (api_server.py's
// /timetable-data/upload endpoint) — the admin's original filename doesn't
// matter at all, so labels/hints below are just for the admin's benefit.
//
// NOTE: "teacher_name" and "teachers" used to be two separate uploads.
// They were near-duplicate data, so they've been merged into a single
// "teachers" file (the old fallback-sheet behavior has been removed —
// teachers with no code are now tagged with a placeholder code on the
// backend instead of being pulled from a second file).
type DataFileKey = "students" | "curriculum" | "teachers" | "rooms";

type DataFileStatus = Record<DataFileKey, boolean> & { all_present: boolean };

const DATA_FILE_FIELDS: { key: DataFileKey; label: string; hint: string }[] = [
  { key: "students", label: "Students", hint: "enrollment_no, name, email, major, minor, semester" },
  { key: "curriculum", label: "Curriculum", hint: "program, semester, course_code, title, L, T, P, credits, offered_as, teacher, teacher_code" },
  { key: "teachers", label: "Teachers", hint: "teacher_code, teacher_name (teacher_code is optional)" },
  { key: "rooms", label: "Rooms", hint: "room_id, ..., capacity" },
];

const ICS_TIMEZONE = "Asia/Kolkata";
const DAY_INDEX: Record<string, number> = {
  Monday: 1,
  Tuesday: 2,
  Wednesday: 3,
  Thursday: 4,
  Friday: 5,
};

const pad = (value: number): string => String(value).padStart(2, "0");

const parseDateInput = (value: string): Date | null => {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) {
    return null;
  }

  const parsed = new Date(year, month - 1, day);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const parseTime = (value: string): { hour: number; minute: number } => {
  const [hourText, minuteText] = value.split(":");
  return {
    hour: Number(hourText),
    minute: Number(minuteText),
  };
};

const toIcsDateTimeLocal = (date: Date): string => {
  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hour = pad(date.getHours());
  const minute = pad(date.getMinutes());
  const second = pad(date.getSeconds());
  return `${year}${month}${day}T${hour}${minute}${second}`;
};

const toIcsDateTimeUtc = (date: Date): string => {
  const year = date.getUTCFullYear();
  const month = pad(date.getUTCMonth() + 1);
  const day = pad(date.getUTCDate());
  const hour = pad(date.getUTCHours());
  const minute = pad(date.getUTCMinutes());
  const second = pad(date.getUTCSeconds());
  return `${year}${month}${day}T${hour}${minute}${second}Z`;
};

const escapeIcsText = (value: string): string =>
  value
    .replace(/\\/g, "\\\\")
    .replace(/;/g, "\\;")
    .replace(/,/g, "\\,")
    .replace(/\n/g, "\\n");

const getFirstWeekdayOnOrAfter = (startDate: Date, weekday: number): Date => {
  const candidate = new Date(startDate);
  const daysUntilTarget = (weekday - candidate.getDay() + 7) % 7;
  candidate.setDate(candidate.getDate() + daysUntilTarget);
  return candidate;
};

const getClassStyle = (type: string): string => {
  if (type === "practical") {
    return "bg-crimson-light/10 text-crimson-light border-crimson-light/30";
  }

  if (type === "tutorial") {
    return "bg-accent/10 text-accent border-accent/30";
  }

  return "bg-primary/10 text-primary border-primary/30";
};

const sortClasses = (classes: TimetableClassEntry[]): TimetableClassEntry[] =>
  [...classes].sort((left, right) => {
    if (left.day !== right.day) {
      return (DAY_INDEX[left.day] ?? 99) - (DAY_INDEX[right.day] ?? 99);
    }

    if (left.slot_index !== right.slot_index) {
      return left.slot_index - right.slot_index;
    }

    return left.course_code.localeCompare(right.course_code);
  });

// ── Data-file upload helpers ────────────────────────────────────────────
// These talk directly to api_server.py's /timetable-data/* endpoints.

const fetchDataFileStatus = async (): Promise<DataFileStatus> => {
  const response = await fetch(`${API_BASE}/timetable-data/status`);
  if (!response.ok) {
    throw new Error("Failed to check uploaded data files");
  }
  return (await response.json()) as DataFileStatus;
};

const uploadDataFiles = async (files: Partial<Record<DataFileKey, File>>): Promise<DataFileStatus> => {
  const formData = new FormData();
  Object.entries(files).forEach(([key, file]) => {
    if (file) {
      formData.append(key, file);
    }
  });

  const response = await fetch(`${API_BASE}/timetable-data/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "Failed to upload data files");
  }

  const result = (await response.json()) as { status: DataFileStatus };
  return result.status;
};

// ── Master timetable upload ─────────────────────────────────────────────
// POST /timetable/master accepts a hand-edited copy of the same
// master_timetable.xlsx downloaded via "Download XLSX" (merged-cell grid,
// produced by genMaster.py) and rebuilds the published timetable from it
// directly — no separate editable file format, no scheduler re-run.

const uploadEditedMasterTimetable = async (
  file: File
): Promise<{ timetable: TimetablePayload; tests_passed: boolean; test_report: string }> => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/timetable/master`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "Failed to upload edited master timetable");
  }

  return await response.json();
};

const Timetable = () => {
  const session = getUserSession();
  const initialPublishSettings = useMemo(() => getTimetablePublishSettings(), []);

  const [semesterWeeksInput, setSemesterWeeksInput] = useState(String(initialPublishSettings.semesterWeeks));
  const [semesterStartDateInput, setSemesterStartDateInput] = useState(initialPublishSettings.semesterStartDate);
  const [semesterEndDateInput, setSemesterEndDateInput] = useState(initialPublishSettings.semesterEndDate);
  const [activeSemesterWeeks, setActiveSemesterWeeks] = useState(initialPublishSettings.semesterWeeks);
  const [activeSemesterStartDate, setActiveSemesterStartDate] = useState(initialPublishSettings.semesterStartDate);
  const [activeSemesterEndDate, setActiveSemesterEndDate] = useState(initialPublishSettings.semesterEndDate);
  const [lastPublishedAt, setLastPublishedAt] = useState(initialPublishSettings.publishedAt);
  const [semesterParity, setSemesterParity] = useState<"even" | "odd">("even");
  const [timetable, setTimetable] = useState<TimetablePayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [facultyCourseCodes, setFacultyCourseCodes] = useState<Set<string> | null>(null);
  const [downloadingImage, setDownloadingImage] = useState(false);
  const [downloadingXlsx, setDownloadingXlsx] = useState(false);
  const [isEditingTimetable, setIsEditingTimetable] = useState(false);
  const [studentOverrides, setStudentOverrides] = useState<Record<string, StudentCellOverride>>({});
  const [editingCellKey, setEditingCellKey] = useState<string | null>(null);
  const [editDraftText, setEditDraftText] = useState("");
  const [editDraftHide, setEditDraftHide] = useState(false);
  const timetableCardRef = useRef<HTMLDivElement>(null);

  // ── Data-file upload state ──────────────────────────────────────────
  // Decluttered flow: pick which file you're uploading from a dropdown,
  // choose the file, hit upload — one file at a time instead of 4 tiles
  // fighting for space.
  const [dataFileStatus, setDataFileStatus] = useState<DataFileStatus | null>(null);
  const [dataFilesOpen, setDataFilesOpen] = useState(false);
  const [selectedDataFileKey, setSelectedDataFileKey] = useState<DataFileKey>("students");
  const [pendingDataFile, setPendingDataFile] = useState<File | null>(null);
  const [uploadingDataFiles, setUploadingDataFiles] = useState(false);
  const [dataFileError, setDataFileError] = useState<string | null>(null);
  const dataFileInputRef = useRef<HTMLInputElement>(null);

  // ── Master timetable upload state ───────────────────────────────────
  const [uploadingEditedMaster, setUploadingEditedMaster] = useState(false);
  const [editedMasterFile, setEditedMasterFile] = useState<File | null>(null);
  const [editedMasterError, setEditedMasterError] = useState<string | null>(null);
  const [editedMasterSuccess, setEditedMasterSuccess] = useState<string | null>(null);
  const [testReport, setTestReport] = useState<string | null>(null);
  const editedMasterInputRef = useRef<HTMLInputElement>(null);

  const refreshDataFileStatus = async () => {
    try {
      const status = await fetchDataFileStatus();
      setDataFileStatus(status);
    } catch (statusError) {
      // Non-fatal: admin can still try uploading/generating; button will
      // just stay disabled until a status check succeeds.
      console.error(statusError);
    }
  };

  useEffect(() => {
    if (session?.role === "admin") {
      void refreshDataFileStatus();
    }
  }, [session?.role]);

  const handleDataFileSelect = (fileList: FileList | null) => {
    setPendingDataFile(fileList?.[0] ?? null);
    setDataFileError(null);
  };

  const handleUploadDataFiles = async () => {
    if (!pendingDataFile) {
      setDataFileError("Choose a file to upload.");
      return;
    }

    setUploadingDataFiles(true);
    setDataFileError(null);
    try {
      const status = await uploadDataFiles({ [selectedDataFileKey]: pendingDataFile });
      setDataFileStatus(status);
      setPendingDataFile(null);
      if (dataFileInputRef.current) {
        dataFileInputRef.current.value = "";
      }
    } catch (uploadError) {
      setDataFileError(uploadError instanceof Error ? uploadError.message : "Failed to upload data files");
    } finally {
      setUploadingDataFiles(false);
    }
  };

  const allDataFilesUploaded = dataFileStatus?.all_present ?? false;
  const missingDataFileLabels = DATA_FILE_FIELDS.filter((f) => !(dataFileStatus?.[f.key] ?? false)).map(
    (f) => f.label
  );

  const handleEditedMasterFileSelect = (fileList: FileList | null) => {
    setEditedMasterFile(fileList?.[0] ?? null);
    setEditedMasterError(null);
    setEditedMasterSuccess(null);
    setTestReport(null);
  };

  const handleUploadEditedMaster = async () => {
    if (!editedMasterFile) {
      setEditedMasterError("Choose the edited master timetable file first.");
      return;
    }

    setUploadingEditedMaster(true);
    setEditedMasterError(null);
    setEditedMasterSuccess(null);
    setTestReport(null);
    try {
      const { timetable: updated, tests_passed, test_report } = await uploadEditedMasterTimetable(editedMasterFile);
      setTimetable(updated);
      setTestReport(test_report);
      setEditedMasterSuccess(
        tests_passed
          ? "Timetable updated. All tests passed."
          : "Timetable updated. Some tests failed — see report below."
      );
      setEditedMasterFile(null);
      if (editedMasterInputRef.current) {
        editedMasterInputRef.current.value = "";
      }
    } catch (uploadError) {
      setEditedMasterError(
        uploadError instanceof Error ? uploadError.message : "Failed to apply edited master timetable"
      );
    } finally {
      setUploadingEditedMaster(false);
    }
  };

  useEffect(() => {
    let isMounted = true;

    const loadState = async () => {
      try {
        setError(null);
        const settings = await fetchTimetablePublishSettings();
        let data: TimetablePayload | null = null;

        try {
          data = await fetchLatestTimetable();
        } catch {
          data = null;
        }

        if (session?.role === "instructor") {
          try {
            const [peopleData, catalog] = await Promise.all([getPeopleData(), getCourseCatalog()]);
            const facultyProfile = findFacultyProfile(peopleData, session.identifier);
            const courseCodes = new Set(
              getCoursesForFaculty(catalog, facultyProfile).map((course) => course.courseCode)
            );
            if (isMounted) {
              setFacultyCourseCodes(courseCodes);
            }
          } catch (facultyLoadError) {
            console.error("Failed to load faculty course assignments", facultyLoadError);
            if (isMounted) {
              setFacultyCourseCodes(new Set());
              setError("Could not load your faculty course records. Try refreshing the page.");
            }
          }
        }

        if (!isMounted) {
          return;
        }

        setSemesterWeeksInput(String(settings.semesterWeeks));
        setSemesterStartDateInput(settings.semesterStartDate);
        setSemesterEndDateInput(settings.semesterEndDate);
        setActiveSemesterWeeks(settings.semesterWeeks);
        setActiveSemesterStartDate(settings.semesterStartDate);
        setActiveSemesterEndDate(settings.semesterEndDate);
        setLastPublishedAt(settings.publishedAt);
        setTimetable(data);
      } catch (loadError) {
        if (isMounted) {
          setError(loadError instanceof Error ? loadError.message : "Failed to load timetable");
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    void loadState();

    return () => {
      isMounted = false;
    };
  }, []);

  const visibleClasses = useMemo(() => {
    if (!timetable) {
      return [] as TimetableClassEntry[];
    }

    if (session?.role === "student") {
      return sortClasses(timetable.by_student[session.identifier]?.classes ?? []);
    }

    if (session?.role === "instructor") {
      if (!facultyCourseCodes) {
        return [] as TimetableClassEntry[];
      }
      return sortClasses(timetable.timetable.filter((entry) => facultyCourseCodes.has(entry.course_code)));
    }

    return sortClasses(timetable.timetable);
  }, [session, timetable, facultyCourseCodes]);

  const visibleClassesByCell = useMemo(() => {
    const classesByCell = new Map<string, TimetableClassEntry[]>();
    const continuationsByCell = new Map<string, TimetableClassEntry[]>();

    if (!timetable) {
      return { classesByCell, continuationsByCell };
    }

    const slotsPerDay = timetable.meta.slots_per_day;
    for (const entry of visibleClasses) {
      const localSlotIndex = entry.slot_index % slotsPerDay;
      const startKey = `${entry.day}-${localSlotIndex}`;
      const existingClasses = classesByCell.get(startKey) ?? [];
      existingClasses.push(entry);
      classesByCell.set(startKey, existingClasses);

      for (let offset = 1; offset < entry.slots; offset += 1) {
        const continuationKey = `${entry.day}-${localSlotIndex + offset}`;
        const existingContinuations = continuationsByCell.get(continuationKey) ?? [];
        existingContinuations.push(entry);
        continuationsByCell.set(continuationKey, existingContinuations);
      }
    }

    return { classesByCell, continuationsByCell };
  }, [timetable, visibleClasses]);

  const handleReloadTimetable = async () => {
    setRefreshing(true);
    setError(null);
    try {
      const data = await fetchLatestTimetable();
      setTimetable(data);
    } catch (reloadError) {
      setError(reloadError instanceof Error ? reloadError.message : "Failed to refresh timetable");
    } finally {
      setRefreshing(false);
    }
  };

  const handlePublishAndGenerate = async () => {
    if (!allDataFilesUploaded) {
      setError("Upload all 4 data files (students, curriculum, teachers, rooms) before generating.");
      return;
    }

    setGenerating(true);
    setError(null);

    try {
      const nextWeeks = Number(semesterWeeksInput);
      const published = await publishTimetableSettings(nextWeeks, semesterStartDateInput, semesterEndDateInput);
      const generated = await generateTimetable({ active_parity: semesterParity });

      setSemesterWeeksInput(String(published.semesterWeeks));
      setSemesterStartDateInput(published.semesterStartDate);
      setSemesterEndDateInput(published.semesterEndDate);
      setActiveSemesterWeeks(published.semesterWeeks);
      setActiveSemesterStartDate(published.semesterStartDate);
      setActiveSemesterEndDate(published.semesterEndDate);
      setLastPublishedAt(published.publishedAt);
      setTimetable(generated);
    } catch (generateError) {
      setError(generateError instanceof Error ? generateError.message : "Failed to generate timetable");
    } finally {
      setGenerating(false);
    }
  };

  const handleExportIcs = () => {
    const semesterStartDate = parseDateInput(activeSemesterStartDate);
    const semesterEndDate = parseDateInput(activeSemesterEndDate);

    if (!semesterStartDate || !semesterEndDate || semesterEndDate < semesterStartDate) {
      window.alert("Semester date range is invalid. Ask admin to publish valid start and end dates.");
      return;
    }

    const semesterUntilUtc = toIcsDateTimeUtc(new Date(Date.UTC(
      semesterEndDate.getFullYear(),
      semesterEndDate.getMonth(),
      semesterEndDate.getDate(),
      23,
      59,
      59,
    )));
    const dtStamp = toIcsDateTimeUtc(new Date());

    const calendarLines: string[] = [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "PRODID:-//Thapar Connect//Timetable Export//EN",
      "CALSCALE:GREGORIAN",
      "METHOD:PUBLISH",
      "X-WR-CALNAME:Thapar Connect Timetable",
      `X-WR-TIMEZONE:${ICS_TIMEZONE}`,
      "BEGIN:VTIMEZONE",
      `TZID:${ICS_TIMEZONE}`,
      "BEGIN:STANDARD",
      "TZOFFSETFROM:+0530",
      "TZOFFSETTO:+0530",
      "TZNAME:IST",
      "DTSTART:19700101T000000",
      "END:STANDARD",
      "END:VTIMEZONE",
    ];

    sortClasses(visibleClasses).forEach((entry) => {
      const dayIndex = DAY_INDEX[entry.day];
      if (typeof dayIndex !== "number") {
        return;
      }

      const startDate = getFirstWeekdayOnOrAfter(semesterStartDate, dayIndex);
      if (startDate > semesterEndDate) {
        return;
      }

      const startClock = parseTime(entry.start);
      const endClock = parseTime(entry.end);
      startDate.setHours(startClock.hour, startClock.minute, 0, 0);
      const endDate = new Date(startDate);
      endDate.setHours(endClock.hour, endClock.minute, 0, 0);

      const safeUid = `${entry.course_code}-${entry.day}-${entry.slot_index}`.replace(/[^a-zA-Z0-9-]/g, "").toLowerCase();
      const description = `Course: ${entry.title}\\nInstructor: ${entry.teacher}\\nRoom: ${entry.room_id}`;

      calendarLines.push(
        "BEGIN:VEVENT",
        `UID:${safeUid}@thapar-connect`,
        `DTSTAMP:${dtStamp}`,
        `SUMMARY:${escapeIcsText(`${entry.course_code} ${entry.title}`)}`,
        `DESCRIPTION:${escapeIcsText(description)}`,
        `LOCATION:${escapeIcsText(entry.room_id)}`,
        `DTSTART;TZID=${ICS_TIMEZONE}:${toIcsDateTimeLocal(startDate)}`,
        `DTEND;TZID=${ICS_TIMEZONE}:${toIcsDateTimeLocal(endDate)}`,
        `RRULE:FREQ=WEEKLY;UNTIL=${semesterUntilUtc}`,
        "STATUS:CONFIRMED",
        "END:VEVENT"
      );
    });

    calendarLines.push("END:VCALENDAR");

    const blob = new Blob([`${calendarLines.join("\r\n")}\r\n`], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const exportDate = new Date();
    const filename = `thapar-timetable-${exportDate.getFullYear()}-${pad(exportDate.getMonth() + 1)}-${pad(exportDate.getDate())}.ics`;

    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleDownloadPng = async () => {
    if (!timetableCardRef.current) {
      return;
    }

    setDownloadingImage(true);
    setError(null);
    try {
      const canvas = await html2canvas(timetableCardRef.current, {
        backgroundColor: "#ffffff",
        scale: 2,
      });
      const dataUrl = canvas.toDataURL("image/png");
      const exportDate = new Date();
      const filename = `thapar-timetable-${exportDate.getFullYear()}-${pad(exportDate.getMonth() + 1)}-${pad(exportDate.getDate())}.png`;

      const link = document.createElement("a");
      link.href = dataUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Failed to download timetable image");
    } finally {
      setDownloadingImage(false);
    }
  };

  const handleDownloadXlsx = async () => {
    setDownloadingXlsx(true);
    setError(null);
    try {
      const blob = await fetchMasterTimetableXlsx();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "master_timetable.xlsx";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Failed to download master timetable");
    } finally {
      setDownloadingXlsx(false);
    }
  };

  const openCellEditor = (slotKey: string) => {
    const existing = studentOverrides[slotKey];
    setEditDraftText(existing?.customText ?? "");
    setEditDraftHide(existing?.hideOriginal ?? false);
    setEditingCellKey(slotKey);
  };

  const saveCellEdit = () => {
    if (!editingCellKey) {
      return;
    }

    setStudentOverrides((prev) => {
      const next = { ...prev };
      if (!editDraftText.trim() && !editDraftHide) {
        delete next[editingCellKey];
      } else {
        next[editingCellKey] = { customText: editDraftText.trim(), hideOriginal: editDraftHide };
      }
      return next;
    });
    setEditingCellKey(null);
  };

  const clearCellEdit = () => {
    if (!editingCellKey) {
      return;
    }

    setStudentOverrides((prev) => {
      const next = { ...prev };
      delete next[editingCellKey];
      return next;
    });
    setEditingCellKey(null);
  };

  const resetAllEdits = () => {
    setStudentOverrides({});
  };

  const timeslots = timetable?.meta.timeslots.slice(0, timetable.meta.slots_per_day) ?? [];
  const days = timetable?.meta.days ?? ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
  const totalVisibleClasses = visibleClasses.length;

  return (
    <div className="min-h-screen flex flex-col pt-20 pb-0">
      <div className="container mx-auto px-4 pb-16 flex-1">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between mb-8">
          <div>
            <h1 className="font-display text-3xl font-bold text-foreground">Timetable</h1>
            <p className="text-muted-foreground mt-1">
              {session?.role === "admin"
                ? "Master timetable view with backend generation controls"
                : session?.role === "instructor"
                  ? `Faculty timetable for ${session.displayName}`
                  : `Student timetable for ${session?.displayName ?? "your account"}`}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Semester: {activeSemesterStartDate || "-"} to {activeSemesterEndDate || "-"} ({activeSemesterWeeks} weeks)
            </p>
          </div>

          <div className="flex flex-col sm:flex-row flex-wrap gap-2">
            <Button variant="outline" onClick={handleReloadTimetable} className="gap-2" disabled={refreshing || loading}>
              <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button onClick={handleExportIcs} variant="outline" className="gap-2" disabled={!visibleClasses.length}>
              <Download className="h-4 w-4" />
              Import to Calendar
            </Button>
            {session?.role === "admin" ? (
              <Button onClick={handleDownloadXlsx} variant="outline" className="gap-2" disabled={downloadingXlsx}>
                <FileSpreadsheet className="h-4 w-4" />
                {downloadingXlsx ? "Downloading..." : "Download XLSX"}
              </Button>
            ) : (
              <Button onClick={handleDownloadPng} variant="outline" className="gap-2" disabled={downloadingImage || !visibleClasses.length}>
                <ImageDown className="h-4 w-4" />
                {downloadingImage ? "Downloading..." : "Download PNG"}
              </Button>
            )}
            {session?.role === "student" ? (
              <>
                <Button
                  variant={isEditingTimetable ? "default" : "outline"}
                  onClick={() => setIsEditingTimetable((value) => !value)}
                  className="gap-2"
                >
                  <Pencil className="h-4 w-4" />
                  {isEditingTimetable ? "Done Editing" : "Edit Timetable"}
                </Button>
                {Object.keys(studentOverrides).length > 0 ? (
                  <Button variant="ghost" onClick={resetAllEdits} className="gap-2 text-muted-foreground">
                    <Undo2 className="h-4 w-4" />
                    Reset Edits
                  </Button>
                ) : null}
              </>
            ) : null}
          </div>
        </div>

        {isEditingTimetable ? (
          <Card className="mb-6 border-accent/30 bg-accent/5">
            <CardContent className="p-4 text-sm text-black">
              Click any cell to add a personal note or hide a class in your view. These edits stay in this browser
              tab only and reset automatically when you refresh the page.
            </CardContent>
          </Card>
        ) : null}

        {error ? (
          <Card className="mb-6 border-destructive/30 bg-destructive/5">
            <CardContent className="p-4 text-sm text-destructive">
              {error}
            </CardContent>
          </Card>
        ) : null}

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
          <Card className="shadow-card">
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground">Visible Classes</p>
              <p className="text-2xl font-display font-bold mt-1">{totalVisibleClasses}</p>
            </CardContent>
          </Card>
          <Card className="shadow-card">
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground">Total Classes</p>
              <p className="text-2xl font-display font-bold mt-1">{timetable?.meta.total_classes ?? 0}</p>
            </CardContent>
          </Card>
          <Card className="shadow-card">
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground">Students Loaded</p>
              <p className="text-2xl font-display font-bold mt-1">{timetable?.meta.total_students ?? 0}</p>
            </CardContent>
          </Card>
          <Card className="shadow-card">
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground">Generated At</p>
              <p className="text-2xl font-display font-bold mt-1 text-sm break-words">
                {lastPublishedAt ? new Date(lastPublishedAt).toLocaleString() : "Not published"}
              </p>
            </CardContent>
          </Card>
        </div>

        {session?.role === "admin" ? (
          <Card className="mb-6 shadow-card">
            <CardContent className="p-4 flex flex-col gap-5">
              {/* ── Data files: one button + dropdown instead of 4 tiles ── */}
              <div>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-foreground">Data Files</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {allDataFilesUploaded
                        ? "All 4 data files are present — ready to generate."
                        : `Waiting on: ${missingDataFileLabels.join(", ")}`}
                    </p>
                  </div>

                  <Popover open={dataFilesOpen} onOpenChange={setDataFilesOpen}>
                    <PopoverTrigger asChild>
                      <Button variant="outline" className="gap-2">
                        <Upload className="h-4 w-4" />
                        Manage Data Files
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-80 space-y-4" align="end">
                      <div>
                        <p className="text-sm font-medium mb-2">Upload a data file</p>
                        <Select
                          value={selectedDataFileKey}
                          onValueChange={(value) => {
                            setSelectedDataFileKey(value as DataFileKey);
                            setPendingDataFile(null);
                            setDataFileError(null);
                            if (dataFileInputRef.current) {
                              dataFileInputRef.current.value = "";
                            }
                          }}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Choose a file type" />
                          </SelectTrigger>
                          <SelectContent>
                            {DATA_FILE_FIELDS.map(({ key, label }) => (
                              <SelectItem key={key} value={key}>
                                <span className="flex items-center gap-2">
                                  {dataFileStatus?.[key] ? (
                                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                                  ) : (
                                    <XCircle className="h-3.5 w-3.5 text-muted-foreground/50 shrink-0" />
                                  )}
                                  {label}
                                </span>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <p className="text-[10px] text-muted-foreground mt-2 leading-snug">
                          {DATA_FILE_FIELDS.find((f) => f.key === selectedDataFileKey)?.hint}
                        </p>
                      </div>

                      <div className="space-y-2">
                        <Input
                          ref={dataFileInputRef}
                          type="file"
                          accept=".xlsx,.xlsm"
                          className="text-xs h-9 file:mr-2 file:text-xs"
                          onChange={(event) => handleDataFileSelect(event.target.files)}
                        />
                        <Button
                          onClick={handleUploadDataFiles}
                          disabled={uploadingDataFiles || !pendingDataFile}
                          className="w-full gap-2"
                        >
                          <Upload className="h-4 w-4" />
                          {uploadingDataFiles ? "Uploading..." : "Upload"}
                        </Button>
                      </div>

                      {dataFileError ? <p className="text-xs text-destructive">{dataFileError}</p> : null}

                      <div className="h-px bg-border" />

                      <div className="space-y-1.5">
                        {DATA_FILE_FIELDS.map(({ key, label }) => (
                          <div key={key} className="flex items-center justify-between text-xs">
                            <span className="text-muted-foreground">{label}</span>
                            {dataFileStatus?.[key] ? (
                              <span className="flex items-center gap-1 text-emerald-600">
                                <CheckCircle2 className="h-3.5 w-3.5" /> Uploaded
                              </span>
                            ) : (
                              <span className="flex items-center gap-1 text-muted-foreground/70">
                                <XCircle className="h-3.5 w-3.5" /> Missing
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                      <p className="text-[10px] text-muted-foreground">
                        Re-uploading a file type replaces the previous one. Any filename is fine as long as the
                        column layout matches.
                      </p>
                    </PopoverContent>
                  </Popover>
                </div>
              </div>

              <div className="h-px bg-border" />

              <div className="flex flex-col lg:flex-row lg:items-end gap-3">
                <div className="w-full lg:max-w-[220px]">
                  <p className="text-sm font-medium text-foreground mb-2">Semester Length (weeks)</p>
                  <Input
                    type="number"
                    min={1}
                    max={52}
                    value={semesterWeeksInput}
                    onChange={(event) => setSemesterWeeksInput(event.target.value)}
                  />
                </div>
                <div className="w-full lg:max-w-[220px]">
                  <p className="text-sm font-medium text-foreground mb-2">Semester Start Date</p>
                  <Input
                    type="date"
                    value={semesterStartDateInput}
                    onChange={(event) => {
                      const nextStart = event.target.value;
                      setSemesterStartDateInput(nextStart);
                      setSemesterWeeksInput(String(deriveSemesterWeeksFromDateRange(nextStart, semesterEndDateInput)));
                    }}
                  />
                </div>
                <div className="w-full lg:max-w-[220px]">
                  <p className="text-sm font-medium text-foreground mb-2">Semester End Date</p>
                  <Input
                    type="date"
                    value={semesterEndDateInput}
                    onChange={(event) => {
                      const nextEnd = event.target.value;
                      setSemesterEndDateInput(nextEnd);
                      setSemesterWeeksInput(String(deriveSemesterWeeksFromDateRange(semesterStartDateInput, nextEnd)));
                    }}
                  />
                </div>
                <div className="w-full lg:max-w-[220px]">
                  <p className="text-sm font-medium text-foreground mb-2">Semester Group</p>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant={semesterParity === "even" ? "default" : "outline"}
                      className="flex-1"
                      onClick={() => setSemesterParity("even")}
                    >
                      Even
                    </Button>
                    <Button
                      type="button"
                      variant={semesterParity === "odd" ? "default" : "outline"}
                      className="flex-1"
                      onClick={() => setSemesterParity("odd")}
                    >
                      Odd
                    </Button>
                  </div>
                </div>
                <Button
                  onClick={handlePublishAndGenerate}
                  disabled={generating || !allDataFilesUploaded}
                  className="gap-2 lg:ml-auto"
                  title={!allDataFilesUploaded ? "Upload all 4 data files first" : undefined}
                >
                  <Sparkles className="h-4 w-4" />
                  {generating ? "Generating..." : "Publish & Generate"}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Publishing stores the semester window for the frontend. Generating runs the backend scheduler and refreshes the master timetable.
              </p>

              <div className="h-px bg-border" />

              {/* ── Manual master-timetable edit round-trip ─────────── */}
              <div>
                <p className="text-sm font-medium text-foreground mb-1">Manual Timetable Edits</p>
                <p className="text-xs text-muted-foreground mb-3">
                  Use the <strong>Download XLSX</strong> button above to get the master timetable, hand-edit
                  rooms/days/times/teachers directly inside that file in Excel, then re-upload it here. Don't add,
                  delete, or reorder rows/columns — only edit the text inside a class's own cell (the room/teacher
                  line). Re-uploading replaces the published timetable directly; it does not re-run the scheduler.
                </p>

                <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                  <Input
                    ref={editedMasterInputRef}
                    type="file"
                    accept=".xlsx,.xlsm"
                    className="text-xs h-9 file:mr-2 file:text-xs max-w-sm"
                    onChange={(event) => handleEditedMasterFileSelect(event.target.files)}
                  />
                  <Button
                    variant="default"
                    onClick={handleUploadEditedMaster}
                    disabled={uploadingEditedMaster || !editedMasterFile}
                    className="gap-2 w-fit"
                  >
                    <FileUp className="h-4 w-4" />
                    {uploadingEditedMaster ? "Applying..." : "Upload Edited Master Timetable"}
                  </Button>
                </div>

                {editedMasterError ? (
                  <p className="text-sm text-destructive mt-2 whitespace-pre-wrap">{editedMasterError}</p>
                ) : null}
                {editedMasterSuccess ? (
                  <p className="text-sm mt-2 text-foreground">{editedMasterSuccess}</p>
                ) : null}
                {testReport ? (
                  <pre className="mt-2 max-h-96 overflow-auto text-[10px] leading-snug bg-secondary/20 border border-border rounded-md p-3 whitespace-pre-wrap">
                    {testReport}
                  </pre>
                ) : null}
              </div>
            </CardContent>
          </Card>
        ) : null}

        <Card className="shadow-card overflow-hidden" ref={timetableCardRef}>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[960px]">
                <thead>
                  <tr className="bg-primary text-primary-foreground">
                    <th className="py-3 px-4 text-left font-medium w-24">Time</th>
                    {days.map((day) => (
                      <th key={day} className="py-3 px-4 text-left font-medium">{day}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {timeslots.map((slot) => (
                    <tr key={`${slot.day}-${slot.slot_index}`} className="border-b border-border align-top">
                      <td className="py-3 px-4 font-medium text-muted-foreground bg-muted/50 whitespace-nowrap">
                        {slot.start} - {slot.end}
                      </td>
                      {days.map((day) => {
                        const slotKey = `${day}-${slot.slot_index % (timetable?.meta.slots_per_day ?? 13)}`;
                        const classesInCell = visibleClassesByCell.classesByCell.get(slotKey) ?? [];
                        const continuationClasses = visibleClassesByCell.continuationsByCell.get(slotKey) ?? [];

                        if (slot.is_lunch) {
                          return (
                            <td key={slotKey} className="p-2 bg-amber-50/60">
                              <div className="min-h-[64px] rounded-lg border border-amber-200 bg-amber-100/70 flex items-center justify-center text-xs font-semibold text-amber-900">
                                LUNCH BREAK
                              </div>
                            </td>
                          );
                        }

                        const canEdit = isEditingTimetable && session?.role === "student";
                        const override = studentOverrides[slotKey];
                        const showOriginal = classesInCell.length > 0 && !override?.hideOriginal;
                        const isEmpty = !showOriginal && continuationClasses.length === 0 && !override?.customText;

                        const cellContent = (
                          <div
                            className={`min-h-[64px] space-y-2 ${
                              canEdit ? "rounded-lg ring-1 ring-transparent hover:ring-primary/50 transition-shadow" : ""
                            }`}
                          >
                            {showOriginal &&
                              classesInCell.map((entry) => (
                                <div key={entry.unit_id} className={`rounded-lg border p-2 ${getClassStyle(entry.type)}`}>
                                  <div className="flex items-start justify-between gap-2">
                                    <div className="font-semibold text-xs">{entry.course_code}</div>
                                    <span className="text-[10px] uppercase tracking-wide opacity-70">{entry.type}</span>
                                  </div>
                                  <div className="text-xs mt-0.5 leading-snug">{entry.title}</div>
                                  <div className="text-[10px] mt-1 opacity-70">{entry.room_id} • {entry.teacher}</div>
                                  <div className="text-[10px] opacity-70">{entry.start} - {entry.end}</div>
                                </div>
                              ))}
                            {override?.customText ? (
                              <div className="rounded-lg border border-dashed border-accent/60 bg-accent/10 p-2">
                                <div className="text-[10px] uppercase tracking-wide text-accent font-semibold mb-0.5">
                                  Personal note
                                </div>
                                <div className="text-xs whitespace-pre-wrap">{override.customText}</div>
                              </div>
                            ) : null}
                            {continuationClasses.length > 0 && showOriginal ? (
                              <div className="text-[10px] italic text-muted-foreground">
                                {continuationClasses.map((entry) => `${entry.course_code} continues`).join(" · ")}
                              </div>
                            ) : null}
                            {isEmpty ? (
                              <div
                                className={`min-h-[64px] rounded-lg border border-dashed border-border/70 ${
                                  canEdit ? "flex items-center justify-center text-[10px] text-muted-foreground/70" : ""
                                }`}
                              >
                                {canEdit ? "+ Add note" : null}
                              </div>
                            ) : null}
                          </div>
                        );

                        if (!canEdit) {
                          return (
                            <td key={slotKey} className="p-2">
                              {cellContent}
                            </td>
                          );
                        }

                        return (
                          <td key={slotKey} className="p-2">
                            <Popover
                              open={editingCellKey === slotKey}
                              onOpenChange={(open) => {
                                if (!open) {
                                  setEditingCellKey(null);
                                }
                              }}
                            >
                              <PopoverTrigger asChild>
                                <button
                                  type="button"
                                  className="w-full text-left cursor-pointer"
                                  onClick={() => openCellEditor(slotKey)}
                                >
                                  {cellContent}
                                </button>
                              </PopoverTrigger>
                              <PopoverContent className="w-72 space-y-3">
                                <div>
                                  <p className="text-sm font-medium mb-1">
                                    Personal note for {day} {slot.start}-{slot.end}
                                  </p>
                                  <Textarea
                                    value={editDraftText}
                                    onChange={(event) => setEditDraftText(event.target.value)}
                                    placeholder="e.g. Study session, reminder..."
                                    rows={3}
                                  />
                                </div>
                                {classesInCell.length > 0 ? (
                                  <label className="flex items-center gap-2 text-xs text-muted-foreground">
                                    <input
                                      type="checkbox"
                                      checked={editDraftHide}
                                      onChange={(event) => setEditDraftHide(event.target.checked)}
                                    />
                                    Hide original class in this view
                                  </label>
                                ) : null}
                                <div className="flex justify-end gap-2">
                                  <Button size="sm" variant="ghost" onClick={clearCellEdit}>
                                    Clear
                                  </Button>
                                  <Button size="sm" onClick={saveCellEdit}>
                                    Save
                                  </Button>
                                </div>
                                <p className="text-[10px] text-muted-foreground">
                                  Personal edits are local to your browser and reset when you refresh.
                                </p>
                              </PopoverContent>
                            </Popover>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
      <Footer />
    </div>
  );
};

export default Timetable;