import { useMemo } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Users, ExternalLink } from "lucide-react";
import Footer from "@/components/Footer";
import { getUserSession } from "@/lib/auth";
import { getAllAssignments, getInstructorProfile } from "@/lib/instructorData";

const Sections = () => {
  const session = useMemo(() => getUserSession(), []);
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
