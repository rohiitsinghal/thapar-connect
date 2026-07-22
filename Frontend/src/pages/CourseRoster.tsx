import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Loader2, Users } from "lucide-react";
import { getUserSession } from "@/lib/auth";
import { fetchCourseRoster, type RosterStudent } from "@/lib/coursesApi";

const CourseRoster = () => {
  const [searchParams] = useSearchParams();
  const courseCode = (searchParams.get("code") || "").toUpperCase();
  const session = getUserSession();

  const [students, setStudents] = useState<RosterStudent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      if (!session?.token) {
        setError("You need to be logged in to view course rosters.");
        setLoading(false);
        return;
      }

      setLoading(true);
      setError("");
      try {
        const roster = await fetchCourseRoster(courseCode, session.token);
        if (!cancelled) {
          setStudents(roster);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unable to load the roster.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, [courseCode, session?.token]);

  return (
    <div className="min-h-screen bg-background py-10 px-4">
      <div className="container mx-auto max-w-4xl">
        <div className="mb-6">
          <Button asChild variant="outline" size="sm">
            <Link to="/courses">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Courses
            </Link>
          </Button>
        </div>

        <Card className="shadow-card">
          <CardHeader>
            <CardTitle className="font-display text-2xl flex items-center gap-2">
              <Users className="w-5 h-5 text-primary" />
              {courseCode || "Course Roster"}
            </CardTitle>
          </CardHeader>

          <CardContent>
            {loading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" /> Loading roster...
              </div>
            ) : error ? (
              <p className="text-sm text-destructive">{error}</p>
            ) : students.length === 0 ? (
              <p className="text-sm text-muted-foreground">No students match this course yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-muted-foreground">
                      <th className="py-2 text-left font-medium">Student Name</th>
                      <th className="py-2 text-left font-medium">Roll No</th>
                      <th className="py-2 text-left font-medium">Email</th>
                    </tr>
                  </thead>
                  <tbody>
                    {students.map((student) => (
                      <tr key={student.roll_no} className="border-b border-border last:border-0">
                        <td className="py-3 text-foreground font-medium">{student.name}</td>
                        <td className="py-3 text-muted-foreground font-mono">{student.roll_no}</td>
                        <td className="py-3 text-muted-foreground">{student.email}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default CourseRoster;
