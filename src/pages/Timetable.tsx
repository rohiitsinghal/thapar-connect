import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import Footer from "@/components/Footer";

const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const timeSlots = ["8:00", "9:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"];

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

const Timetable = () => {
  const [semester, setSemester] = useState("spring-2026");
  const [department, setDepartment] = useState("csed");

  const skipCells = new Set<string>();

  for (const key of Object.keys(sampleSchedule)) {
    const [day, time] = key.split("-");
    const entry = sampleSchedule[key];
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
            <p className="text-muted-foreground mt-1">Weekly class schedule view</p>
          </div>
          <div className="flex gap-3">
            <Select value={semester} onValueChange={setSemester}>
              <SelectTrigger className="w-44">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="spring-2026">Spring 2026</SelectItem>
                <SelectItem value="fall-2025">Fall 2025</SelectItem>
              </SelectContent>
            </Select>
            <Select value={department} onValueChange={setDepartment}>
              <SelectTrigger className="w-44">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="csed">CSED</SelectItem>
                <SelectItem value="eced">ECED</SelectItem>
                <SelectItem value="med">MED</SelectItem>
                <SelectItem value="ced">CED</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

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
                        const entry = sampleSchedule[key];
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
