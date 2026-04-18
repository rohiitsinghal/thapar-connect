import { useEffect, useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Users, ExternalLink, Download } from "lucide-react";
import Footer from "@/components/Footer";
import { getUserSession } from "@/lib/auth";
import { getAllAssignments, getInstructorProfile } from "@/lib/instructorData";
import { fetchTimetablePublishSettings, getTimetablePublishSettings } from "@/lib/timetablePublishSettings";

const dayAbbreviationToByDay: Record<string, string> = {
  Mon: "MO",
  Tue: "TU",
  Wed: "WE",
  Thu: "TH",
  Fri: "FR",
};
const ICS_TIMEZONE = "Asia/Kolkata";

const pad = (value: number): string => String(value).padStart(2, "0");

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

const parseDateInput = (value: string): Date | null => {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) {
    return null;
  }

  const parsed = new Date(year, month - 1, day);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const getFirstWeekdayOnOrAfter = (startDate: Date, weekday: number): Date => {
  const candidate = new Date(startDate);
  const daysUntilTarget = (weekday - candidate.getDay() + 7) % 7;
  candidate.setDate(candidate.getDate() + daysUntilTarget);
  return candidate;
};

const toIcsUntilUtc = (dateInput: string): string => {
  const parsed = parseDateInput(dateInput);
  if (!parsed) {
    return toIcsDateTimeUtc(new Date());
  }

  const utc = new Date(Date.UTC(parsed.getFullYear(), parsed.getMonth(), parsed.getDate(), 23, 59, 59));
  return toIcsDateTimeUtc(utc);
};

const parseTime = (time: string): { hour: number; minute: number } => {
  const [hourText, minuteText] = time.trim().split(":");
  return {
    hour: Number(hourText),
    minute: Number(minuteText),
  };
};

type ParsedAssignmentTime = {
  byDays: string[];
  startHour: number;
  startMinute: number;
  endHour: number;
  endMinute: number;
};

const parseAssignmentTime = (value: string): ParsedAssignmentTime | null => {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  const [dayPart, rangePart] = trimmed.split(" ");
  if (!dayPart || !rangePart) {
    return null;
  }

  const days = dayPart
    .split("/")
    .map((day) => dayAbbreviationToByDay[day])
    .filter(Boolean);

  const [startTimeText, endTimeText] = rangePart.split("-");
  if (!startTimeText || !endTimeText || days.length === 0) {
    return null;
  }

  const start = parseTime(startTimeText);
  const end = parseTime(endTimeText);

  if ([start.hour, start.minute, end.hour, end.minute].some((part) => Number.isNaN(part))) {
    return null;
  }

  return {
    byDays: days,
    startHour: start.hour,
    startMinute: start.minute,
    endHour: end.hour,
    endMinute: end.minute,
  };
};

const Sections = () => {
  const session = useMemo(() => getUserSession(), []);
  const initialSettings = useMemo(() => getTimetablePublishSettings(), []);
  const [semesterWeeks, setSemesterWeeks] = useState(initialSettings.semesterWeeks);
  const [semesterStartDate, setSemesterStartDate] = useState(initialSettings.semesterStartDate);
  const [semesterEndDate, setSemesterEndDate] = useState(initialSettings.semesterEndDate);

  useEffect(() => {
    let isMounted = true;

    const loadPublishedSettings = async () => {
      const settings = await fetchTimetablePublishSettings();
      if (isMounted) {
        setSemesterWeeks(settings.semesterWeeks);
        setSemesterStartDate(settings.semesterStartDate);
        setSemesterEndDate(settings.semesterEndDate);
      }
    };

    void loadPublishedSettings();

    return () => {
      isMounted = false;
    };
  }, []);

  const assignments = useMemo(() => {
    if (session?.role === "instructor") {
      return getInstructorProfile(session.identifier).assignments;
    }

    return getAllAssignments();
  }, [session]);

  const openStudentsTab = (courseCode: string, sectionName: string) => {
    const url = `/sections/students?courseCode=${encodeURIComponent(courseCode)}&section=${encodeURIComponent(sectionName)}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const handleExportInstructorIcs = () => {
    if (session?.role !== "instructor") {
      return;
    }

    const activeStartDate = parseDateInput(semesterStartDate);
    const activeEndDate = parseDateInput(semesterEndDate);

    if (!activeStartDate || !activeEndDate || activeEndDate < activeStartDate) {
      window.alert("Semester date range is invalid. Ask admin to publish valid start and end dates.");
      return;
    }

    const semesterUntilUtc = toIcsUntilUtc(semesterEndDate);
    const dtStamp = toIcsDateTimeUtc(new Date());
    const calendarLines: string[] = [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "PRODID:-//Thapar Connect//Instructor Timetable Export//EN",
      "CALSCALE:GREGORIAN",
      "METHOD:PUBLISH",
      "X-WR-CALNAME:Instructor Timetable",
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

    for (const assignment of assignments) {
      const parsedTime = parseAssignmentTime(assignment.time);
      if (!parsedTime) {
        continue;
      }

      const dayOffsets = parsedTime.byDays
        .map((dayCode) => ["MO", "TU", "WE", "TH", "FR"].indexOf(dayCode))
        .filter((index) => index >= 0)
        .sort((a, b) => a - b);

      if (dayOffsets.length === 0) {
        continue;
      }

      const firstStartDate = getFirstWeekdayOnOrAfter(activeStartDate, dayOffsets[0] + 1);

      if (firstStartDate > activeEndDate) {
        continue;
      }

      firstStartDate.setHours(parsedTime.startHour, parsedTime.startMinute, 0, 0);

      const firstEndDate = new Date(firstStartDate);
      firstEndDate.setHours(parsedTime.endHour, parsedTime.endMinute, 0, 0);

      const uidSeed = `${assignment.courseCode}-${assignment.sectionName}`
        .replace(/[^a-zA-Z0-9-]/g, "")
        .toLowerCase();

      calendarLines.push(
        "BEGIN:VEVENT",
        `UID:${uidSeed}@thapar-connect`,
        `DTSTAMP:${dtStamp}`,
        `SUMMARY:${escapeIcsText(`${assignment.courseCode} ${assignment.courseName}`)}`,
        `DESCRIPTION:${escapeIcsText(`Section: ${assignment.sectionName}\\nInstructor: ${session.displayName}`)}`,
        `DTSTART;TZID=${ICS_TIMEZONE}:${toIcsDateTimeLocal(firstStartDate)}`,
        `DTEND;TZID=${ICS_TIMEZONE}:${toIcsDateTimeLocal(firstEndDate)}`,
        `RRULE:FREQ=WEEKLY;UNTIL=${semesterUntilUtc};BYDAY=${parsedTime.byDays.join(",")}`,
        "STATUS:CONFIRMED",
        "END:VEVENT"
      );
    }

    calendarLines.push("END:VCALENDAR");

    const icsContent = `${calendarLines.join("\r\n")}\r\n`;
    const blob = new Blob([icsContent], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const exportDate = new Date();
    link.href = url;
    link.download = `instructor-timetable-${exportDate.getFullYear()}-${pad(exportDate.getMonth() + 1)}-${pad(exportDate.getDate())}.ics`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen pt-20 pb-0">
      <div className="container mx-auto px-4 pb-16">
        <div className="mb-8">
          <h1 className="font-display text-3xl font-bold text-foreground">Student Sections</h1>
          <p className="text-muted-foreground mt-1">
            {session?.role === "instructor"
              ? "Sections assigned to you for Spring 2026"
              : "Section assignments for Spring 2026"}
          </p>
          {session?.role === "instructor" ? (
            <div className="mt-4">
              <Button variant="outline" className="gap-2" onClick={handleExportInstructorIcs}>
                <Download className="w-4 h-4" />
                Export Instructor Timetable (.ics)
              </Button>
              <p className="text-xs text-muted-foreground mt-2">Uses published semester range: {semesterStartDate} to {semesterEndDate} ({semesterWeeks} weeks).</p>
            </div>
          ) : null}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {assignments.map((assignment) => (
            <Card
              key={`${assignment.courseCode}-${assignment.sectionName}`}
              className="shadow-card hover:shadow-elevated transition-shadow cursor-pointer"
              onClick={() => openStudentsTab(assignment.courseCode, assignment.sectionName)}
            >
              <CardContent className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="font-display font-semibold text-foreground">
                      {assignment.courseCode} - {assignment.courseName}
                    </p>
                    <p className="text-sm text-muted-foreground mt-1">{assignment.sectionName}</p>
                  </div>
                  <ExternalLink className="w-4 h-4 text-muted-foreground" />
                </div>

                <div className="flex items-center justify-between mt-3">
                  <Badge variant="outline" className="text-xs">
                    <Users className="w-3 h-3 mr-1" /> {assignment.students.length} Students
                  </Badge>
                  <span className="text-xs text-muted-foreground">{assignment.time}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
      <Footer />
    </div>
  );
};

export default Sections;
