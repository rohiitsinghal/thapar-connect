import { Card, CardContent } from "@/components/ui/card";
import { Clock, MapPin } from "lucide-react";
import Footer from "@/components/Footer";

const exams = [
  { code: "UCS301", name: "Data Structures", date: "Apr 15, 2026", time: "9:00 AM - 12:00 PM", room: "LT-101", students: 180, status: "Scheduled" },
  { code: "UCS503", name: "Operating Systems", date: "Apr 17, 2026", time: "2:00 PM - 5:00 PM", room: "LT-103", students: 165, status: "Scheduled" },
  { code: "UMA031", name: "Linear Algebra", date: "Apr 19, 2026", time: "9:00 AM - 12:00 PM", room: "LT-205", students: 320, status: "Scheduled" },
  { code: "UCS310", name: "DBMS", date: "Apr 21, 2026", time: "9:00 AM - 12:00 PM", room: "LT-102", students: 175, status: "Scheduled" },
  { code: "UCS601", name: "Artificial Intelligence", date: "Apr 22, 2026", time: "2:00 PM - 5:00 PM", room: "LT-205", students: 140, status: "Pending" },
  { code: "UEE501", name: "Power Systems", date: "Apr 23, 2026", time: "9:00 AM - 12:00 PM", room: "D-302", students: 95, status: "Scheduled" },
  { code: "UME401", name: "Thermodynamics", date: "Apr 24, 2026", time: "2:00 PM - 5:00 PM", room: "A-201", students: 110, status: "Conflict" },
  { code: "UPH002", name: "Engineering Physics", date: "Apr 25, 2026", time: "9:00 AM - 12:00 PM", room: "LT-102", students: 350, status: "Scheduled" },
];

const Exams = () => (
  <div className="min-h-screen pt-20 pb-0">
    <div className="container mx-auto px-4 pb-16">
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold text-foreground">Exam Schedule</h1>
        <p className="text-muted-foreground mt-1">End Semester Examinations — Spring 2026</p>
      </div>

      <Card className="shadow-card overflow-hidden">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-primary text-primary-foreground">
                  <th className="py-3 px-4 text-left font-medium">Code</th>
                  <th className="py-3 px-4 text-left font-medium">Course</th>
                  <th className="py-3 px-4 text-left font-medium">Date</th>
                  <th className="py-3 px-4 text-left font-medium">Time</th>
                  <th className="py-3 px-4 text-left font-medium">Room</th>
                </tr>
              </thead>
              <tbody>
                {exams.map((exam) => (
                  <tr key={exam.code} className="border-b border-border hover:bg-muted/50 transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-primary">{exam.code}</td>
                    <td className="py-3 px-4 font-medium text-foreground">{exam.name}</td>
                    <td className="py-3 px-4 text-muted-foreground">{exam.date}</td>
                    <td className="py-3 px-4 text-muted-foreground">
                      <span className="inline-flex items-center gap-1">
                        <Clock className="w-3 h-3" /> {exam.time}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-muted-foreground">
                      <span className="inline-flex items-center gap-1">
                        <MapPin className="w-3 h-3" /> {exam.room}
                      </span>
                    </td>
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

export default Exams;
