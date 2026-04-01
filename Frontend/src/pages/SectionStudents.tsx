import { Link, useSearchParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Users } from "lucide-react";
import { getUserSession } from "@/lib/auth";
import { getAllAssignments, getInstructorProfile } from "@/lib/instructorData";

const SectionStudents = () => {
  const [searchParams] = useSearchParams();
  const courseCode = (searchParams.get("courseCode") || "").toUpperCase();
  const sectionName = searchParams.get("section") || "";

  const session = getUserSession();
  const assignments =
    session?.role === "instructor"
      ? getInstructorProfile(session.identifier).assignments
      : getAllAssignments();

  const selected = assignments.find(
    (assignment) =>
      assignment.courseCode === courseCode &&
      assignment.sectionName.toLowerCase() === sectionName.toLowerCase()
  );

  return (
    <div className="min-h-screen bg-background py-10 px-4">
      <div className="container mx-auto max-w-4xl">
        <div className="mb-6">
          <Button asChild variant="outline" size="sm">
            <Link to="/sections">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Sections
            </Link>
          </Button>
        </div>

        <Card className="shadow-card">
          <CardHeader>
            <CardTitle className="font-display text-2xl flex items-center gap-2">
              <Users className="w-5 h-5 text-primary" />
              {selected
                ? `${selected.courseCode} - ${selected.courseName} (${selected.sectionName})`
                : "Section Students"}
            </CardTitle>
          </CardHeader>

          <CardContent>
            {selected ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-muted-foreground">
                      <th className="py-2 text-left font-medium">Student Name</th>
                      <th className="py-2 text-left font-medium">Roll No</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selected.students.map((student) => (
                      <tr key={student.rollNo} className="border-b border-border last:border-0">
                        <td className="py-3 text-foreground font-medium">{student.name}</td>
                        <td className="py-3 text-muted-foreground font-mono">{student.rollNo}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Could not find this section in your teaching assignments.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default SectionStudents;
