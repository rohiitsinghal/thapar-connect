import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Users } from "lucide-react";
import Footer from "@/components/Footer";

const sections = [
  { course: "UCS301 - Data Structures", sections: [
    { name: "Section A", students: 60, instructor: "Dr. A. Gupta", time: "Mon/Wed 9:00-10:30" },
    { name: "Section B", students: 60, instructor: "Dr. A. Gupta", time: "Mon/Wed 11:00-12:30" },
    { name: "Section C", students: 60, instructor: "Dr. R. Patel", time: "Tue/Thu 9:00-10:30" },
  ]},
  { course: "UCS503 - Operating Systems", sections: [
    { name: "Section A", students: 55, instructor: "Dr. P. Kaur", time: "Tue/Thu 10:00-11:30" },
    { name: "Section B", students: 55, instructor: "Dr. P. Kaur", time: "Wed/Fri 10:00-11:30" },
    { name: "Section C", students: 55, instructor: "Dr. H. Bansal", time: "Mon/Wed 14:00-15:30" },
  ]},
  { course: "UMA031 - Linear Algebra", sections: [
    { name: "Section A", students: 80, instructor: "Dr. S. Verma", time: "Mon/Wed 14:00-15:30" },
    { name: "Section B", students: 80, instructor: "Dr. S. Verma", time: "Tue/Thu 14:00-15:30" },
    { name: "Section C", students: 80, instructor: "Dr. T. Das", time: "Wed/Fri 9:00-10:30" },
    { name: "Section D", students: 80, instructor: "Dr. T. Das", time: "Mon/Thu 11:00-12:30" },
  ]},
  { course: "UCS310 - Database Management Systems", sections: [
    { name: "Section A", students: 58, instructor: "Dr. R. Singh", time: "Wed/Fri 11:00-12:30" },
    { name: "Section B", students: 58, instructor: "Dr. R. Singh", time: "Mon/Thu 11:00-12:30" },
    { name: "Section C", students: 59, instructor: "Dr. Y. Sharma", time: "Tue/Fri 14:00-15:30" },
  ]},
];

const Sections = () => (
  <div className="min-h-screen pt-20 pb-0">
    <div className="container mx-auto px-4 pb-16">
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold text-foreground">Student Sections</h1>
        <p className="text-muted-foreground mt-1">Section assignments for Spring 2026</p>
      </div>

      <div className="space-y-6">
        {sections.map((course) => (
          <Card key={course.course} className="shadow-card">
            <CardContent className="p-6">
              <h3 className="font-display text-lg font-semibold text-foreground mb-4">{course.course}</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {course.sections.map((sec) => (
                  <div key={sec.name} className="p-4 rounded-lg bg-secondary border border-border">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold text-foreground">{sec.name}</span>
                      <Badge variant="outline" className="text-xs">
                        <Users className="w-3 h-3 mr-1" /> {sec.students}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">{sec.instructor}</p>
                    <p className="text-xs text-muted-foreground mt-1">{sec.time}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
    <Footer />
  </div>
);

export default Sections;
