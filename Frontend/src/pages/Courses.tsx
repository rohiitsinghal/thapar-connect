import { useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Search, BookOpen } from "lucide-react";
import Footer from "@/components/Footer";
import { getUserSession } from "@/lib/auth";
import { getInstructorProfile } from "@/lib/instructorData";

const coursesData = [
  { code: "UCS301", name: "Data Structures", dept: "CSED", credits: 4, instructor: "Dr. A. Gupta", students: 180, type: "Core" },
  { code: "UCS503", name: "Operating Systems", dept: "CSED", credits: 4, instructor: "Dr. P. Kaur", students: 165, type: "Core" },
  { code: "UCS310", name: "Database Management Systems", dept: "CSED", credits: 4, instructor: "Dr. R. Singh", students: 175, type: "Core" },
  { code: "UMA031", name: "Linear Algebra", dept: "SOM", credits: 3, instructor: "Dr. S. Verma", students: 320, type: "Core" },
  { code: "UCS601", name: "Artificial Intelligence", dept: "CSED", credits: 3, instructor: "Dr. M. Sharma", students: 140, type: "Elective" },
  { code: "UEE501", name: "Power Systems", dept: "EIED", credits: 4, instructor: "Dr. K. Mehta", students: 95, type: "Core" },
  { code: "UME401", name: "Thermodynamics", dept: "MED", credits: 3, instructor: "Dr. N. Rao", students: 110, type: "Core" },
  { code: "UCE301", name: "Structural Analysis", dept: "CED", credits: 4, instructor: "Dr. L. Jain", students: 85, type: "Core" },
  { code: "UCS701", name: "Machine Learning", dept: "CSED", credits: 3, instructor: "Dr. A. Kumar", students: 155, type: "Elective" },
  { code: "UCS351", name: "Data Structures Lab", dept: "CSED", credits: 2, instructor: "Dr. A. Gupta", students: 180, type: "Lab" },
  { code: "UCS553", name: "Operating Systems Lab", dept: "CSED", credits: 2, instructor: "Dr. P. Kaur", students: 165, type: "Lab" },
  { code: "UPH002", name: "Engineering Physics", dept: "SOS", credits: 4, instructor: "Dr. V. Bansal", students: 350, type: "Core" },
];

const Courses = () => {
  const [search, setSearch] = useState("");
  const session = useMemo(() => getUserSession(), []);
  const isInstructor = session?.role === "instructor";

  const visibleCourses = useMemo(() => {
    if (!isInstructor || !session) {
      return coursesData;
    }

    const profile = getInstructorProfile(session.identifier);
    const taughtCodes = new Set(profile.assignments.map((assignment) => assignment.courseCode));
    return coursesData.filter((course) => taughtCodes.has(course.code));
  }, [isInstructor, session]);

  const filtered = visibleCourses.filter(
    (course) =>
      course.name.toLowerCase().includes(search.toLowerCase()) ||
      course.code.toLowerCase().includes(search.toLowerCase()) ||
      course.dept.toLowerCase().includes(search.toLowerCase())
  );

  const openStudyMaterial = (courseCode: string) => {
    const url = isInstructor
      ? `/courses/manage-material?code=${encodeURIComponent(courseCode)}`
      : `/courses/material?code=${encodeURIComponent(courseCode)}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  return (
    <div className="min-h-screen pt-20 pb-0">
      <div className="container mx-auto px-4 pb-16">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
          <div>
            <h1 className="font-display text-3xl font-bold text-foreground">Course Catalog</h1>
            <p className="text-muted-foreground mt-1">
              {visibleCourses.length} {isInstructor ? "courses assigned to you" : "courses across all departments"}
            </p>
          </div>
          <div className="relative w-full md:w-72">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search courses..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((course) => (
            <Card
              key={course.code}
              className="shadow-card hover:shadow-elevated transition-shadow cursor-pointer group"
              onClick={() => openStudyMaterial(course.code)}
            >
              <CardContent className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary transition-colors">
                    <BookOpen className="w-5 h-5 text-primary group-hover:text-primary-foreground transition-colors" />
                  </div>
                  <Badge variant={course.type === "Core" ? "default" : course.type === "Lab" ? "secondary" : "outline"}>
                    {course.type}
                  </Badge>
                </div>
                <h3 className="font-display font-semibold text-foreground">{course.name}</h3>
                <p className="text-sm text-primary font-mono font-medium mt-0.5">{course.code}</p>
                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                  <span>{course.dept}</span>
                  <span>{course.credits} Credits</span>
                  <span>{course.students} Students</span>
                </div>
                <p className="text-xs text-muted-foreground mt-2">{course.instructor}</p>
                <p className="text-xs text-primary mt-3 font-medium">
                  {isInstructor ? "Upload Study Material" : "Open Study Material"}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
      <Footer />
    </div>
  );
};

export default Courses;
