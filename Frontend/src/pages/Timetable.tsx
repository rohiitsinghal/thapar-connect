import { useEffect, useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import Footer from "@/components/Footer";
import { getUserSession } from "@/lib/auth";
import { getInstructorProfile } from "@/lib/instructorData";
import {
  deriveSemesterWeeksFromDateRange,
  fetchTimetablePublishSettings,
  getTimetablePublishSettings,
  publishTimetableSettings,
} from "@/lib/timetablePublishSettings";
import { Download } from "lucide-react";

const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const timeSlots = ["8:00", "9:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"];
const ICS_TIMEZONE = "Asia/Kolkata";
const dayToIndex: Record<string, number> = {
  Monday: 1,
  Tuesday: 2,
  Wednesday: 3,
  Thursday: 4,
  Friday: 5,
};

interface ScheduleEntry {
  course: string;
  code: string;
  room: string;
  instructor: string;
  color: string;
  span: number;
}

const sampleSchedule: Record<string, ScheduleEntry> = {
  "Monday-9:00": { course: "Data Structures", code: "UCS301", room: "LT-101", instructor: "Dr. Gupta", color: "bg-primary/15 text-primary border-primary/30", span: 2 },
  "Monday-14:00": { course: "Linear Algebra", code: "UMA031", room: "LT-205", instructor: "Dr. Verma", color: "bg-accent/15 text-accent border-accent/30", span: 2 },
  "Tuesday-10:00": { course: "Operating Systems", code: "UCS503", room: "LT-103", instructor: "Dr. Kaur", color: "bg-crimson-light/15 text-crimson-light border-crimson-light/30", span: 2 },
  "Tuesday-14:00": { course: "Data Structures Lab", code: "UCS351", room: "Lab-C1", instructor: "Dr. Gupta", color: "bg-primary/15 text-primary border-primary/30", span: 3 },
  "Wednesday-9:00": { course: "Data Structures", code: "UCS301", room: "LT-101", instructor: "Dr. Gupta", color: "bg-primary/15 text-primary border-primary/30", span: 2 },
  "Wednesday-11:00": { course: "DBMS", code: "UCS310", room: "LT-102", instructor: "Dr. Singh", color: "bg-gold/15 text-gold border-gold/30", span: 2 },
  "Thursday-10:00": { course: "Operating Systems", code: "UCS503", room: "LT-103", instructor: "Dr. Kaur", color: "bg-crimson-light/15 text-crimson-light border-crimson-light/30", span: 2 },
  "Thursday-15:00": { course: "OS Lab", code: "UCS553", room: "Lab-C2", instructor: "Dr. Kaur", color: "bg-crimson-light/15 text-crimson-light border-crimson-light/30", span: 2 },
  "Friday-9:00": { course: "Linear Algebra", code: "UMA031", room: "LT-205", instructor: "Dr. Verma", color: "bg-accent/15 text-accent border-accent/30", span: 1 },
  "Friday-11:00": { course: "DBMS", code: "UCS310", room: "LT-102", instructor: "Dr. Singh", color: "bg-gold/15 text-gold border-gold/30", span: 2 },
};

const pad = (value: number): string => String(value).padStart(2, "0");

const parseHourMinute = (time: string): { hour: number; minute: number } => {
  const [hourText, minuteText] = time.split(":");
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

  useEffect(() => {
    let isMounted = true;

    const loadPublishedSettings = async () => {
      const settings = await fetchTimetablePublishSettings();
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
    };

    void loadPublishedSettings();

    return () => {
      isMounted = false;
    };
  }, []);

  const visibleSchedule = useMemo(() => {
    if (session?.role !== "instructor") {
      return sampleSchedule;
    }

    const assignedCourseCodes = new Set(
      getInstructorProfile(session.identifier).assignments.map((assignment) => assignment.courseCode)
    );

    const filteredSchedule: Record<string, ScheduleEntry> = {};

    for (const [slot, entry] of Object.entries(sampleSchedule)) {
      if (assignedCourseCodes.has(entry.code)) {
        filteredSchedule[slot] = entry;
      }
    }

    return filteredSchedule;
  }, [session]);

  const handlePublishSemesterLength = async () => {
    const nextWeeks = Number(semesterWeeksInput);
    const updated = await publishTimetableSettings(nextWeeks, semesterStartDateInput, semesterEndDateInput);
    setSemesterWeeksInput(String(updated.semesterWeeks));
    setSemesterStartDateInput(updated.semesterStartDate);
    setSemesterEndDateInput(updated.semesterEndDate);
    setActiveSemesterWeeks(updated.semesterWeeks);
    setActiveSemesterStartDate(updated.semesterStartDate);
    setActiveSemesterEndDate(updated.semesterEndDate);
    setLastPublishedAt(updated.publishedAt);
  };

  const handleExportIcs = () => {
    const sortedEntries = Object.entries(visibleSchedule).sort(([aKey], [bKey]) => {
      const [aDay, aTime] = aKey.split("-");
      const [bDay, bTime] = bKey.split("-");
      const dayDiff = days.indexOf(aDay) - days.indexOf(bDay);

      if (dayDiff !== 0) {
        return dayDiff;
      }

      return timeSlots.indexOf(aTime) - timeSlots.indexOf(bTime);
    });

    const semesterStartDate = parseDateInput(activeSemesterStartDate);
    const semesterEndDate = parseDateInput(activeSemesterEndDate);

    if (!semesterStartDate || !semesterEndDate || semesterEndDate < semesterStartDate) {
      window.alert("Semester date range is invalid. Ask admin to publish valid start and end dates.");
      return;
    }

    const semesterUntilUtc = toIcsUntilUtc(activeSemesterEndDate);
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

    sortedEntries.forEach(([key, entry]) => {
      const [day, time] = key.split("-");
      const dayIndex = dayToIndex[day];

      if (typeof dayIndex !== "number") {
        return;
      }

      const { hour, minute } = parseHourMinute(time);
      const startDate = getFirstWeekdayOnOrAfter(semesterStartDate, dayIndex);

      if (startDate > semesterEndDate) {
        return;
      }

      startDate.setHours(hour, minute, 0, 0);

      const endDate = new Date(startDate);
      endDate.setHours(endDate.getHours() + entry.span);

      const safeUid = `${entry.code}-${day}-${time}`.replace(/[^a-zA-Z0-9-]/g, "").toLowerCase();
      const description = `Course: ${entry.course}\\nInstructor: ${entry.instructor}\\nRoom: ${entry.room}`;

      calendarLines.push(
        "BEGIN:VEVENT",
        `UID:${safeUid}@thapar-connect`,
        `DTSTAMP:${dtStamp}`,
        `SUMMARY:${escapeIcsText(`${entry.code} ${entry.course}`)}`,
        `DESCRIPTION:${escapeIcsText(description)}`,
        `LOCATION:${escapeIcsText(entry.room)}`,
        `DTSTART;TZID=${ICS_TIMEZONE}:${toIcsDateTimeLocal(startDate)}`,
        `DTEND;TZID=${ICS_TIMEZONE}:${toIcsDateTimeLocal(endDate)}`,
        `RRULE:FREQ=WEEKLY;UNTIL=${semesterUntilUtc}`,
        "STATUS:CONFIRMED",
        "END:VEVENT"
      );
    });

    calendarLines.push("END:VCALENDAR");

    const icsContent = `${calendarLines.join("\r\n")}\r\n`;
    const blob = new Blob([icsContent], { type: "text/calendar;charset=utf-8" });
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

  const skipCells = new Set<string>();

  for (const key of Object.keys(visibleSchedule)) {
    const [day, time] = key.split("-");
    const entry = visibleSchedule[key];
    const startIdx = timeSlots.indexOf(time);
    for (let i = 1; i < entry.span; i++) {
      if (startIdx + i < timeSlots.length) {
        skipCells.add(`${day}-${timeSlots[startIdx + i]}`);
      }
    }
  }

  return (
    <div className="min-h-screen pt-20 pb-0">
      <div className="container mx-auto px-4 pb-16">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
          <div>
            <h1 className="font-display text-3xl font-bold text-foreground">Timetable</h1>
            <p className="text-muted-foreground mt-1">Weekly class schedule view • Semester: {activeSemesterStartDate} to {activeSemesterEndDate} ({activeSemesterWeeks} weeks)</p>
          </div>
          <Button onClick={handleExportIcs} variant="outline" className="gap-2 w-full md:w-auto" disabled={Object.keys(visibleSchedule).length === 0}>
            <Download className="h-4 w-4" />
            Import to Calendar
          </Button>
        </div>

        {session?.role === "admin" ? (
          <Card className="mb-6">
            <CardContent className="p-4 flex flex-col md:flex-row md:items-end gap-3">
              <div className="w-full md:max-w-[220px]">
                <p className="text-sm font-medium text-foreground mb-2">Semester Length (weeks)</p>
                <Input
                  type="number"
                  min={1}
                  max={52}
                  value={semesterWeeksInput}
                  onChange={(event) => setSemesterWeeksInput(event.target.value)}
                />
              </div>
              <div className="w-full md:max-w-[220px]">
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
              <div className="w-full md:max-w-[220px]">
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
              <Button onClick={handlePublishSemesterLength}>Publish Timetable Settings</Button>
              <p className="text-xs text-muted-foreground md:ml-auto">
                {lastPublishedAt
                  ? `Published: ${new Date(lastPublishedAt).toLocaleString()}`
                  : "No publish settings yet. Default 16 weeks is active."}
              </p>
            </CardContent>
          </Card>
        ) : null}

        <Card className="shadow-card overflow-hidden">
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[900px]">
                <thead>
                  <tr className="bg-primary text-primary-foreground">
                    <th className="py-3 px-4 text-left font-medium w-20">Time</th>
                    {days.map((day) => (
                      <th key={day} className="py-3 px-4 text-left font-medium">{day}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {timeSlots.map((time) => (
                    <tr key={time} className="border-b border-border">
                      <td className="py-3 px-4 font-medium text-muted-foreground bg-muted/50 whitespace-nowrap">
                        {time}
                      </td>
                      {days.map((day) => {
                        const key = `${day}-${time}`;
                        if (skipCells.has(key)) return null;
                        const entry = visibleSchedule[key];
                        if (entry) {
                          return (
                            <td key={key} rowSpan={entry.span} className="p-1.5">
                              <div className={`rounded-lg border p-2.5 h-full ${entry.color} cursor-pointer hover:shadow-card transition-shadow`}>
                                <div className="font-semibold text-xs">{entry.code}</div>
                                <div className="text-xs mt-0.5 opacity-80">{entry.course}</div>
                                <div className="text-[10px] mt-1 opacity-60">{entry.room} • {entry.instructor}</div>
                              </div>
                            </td>
                          );
                        }
                        return <td key={key} className="p-1.5"><div className="h-full min-h-[48px]" /></td>;
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
