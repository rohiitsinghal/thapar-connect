import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Search, BookOpen, Loader2 } from "lucide-react";
import Footer from "@/components/Footer";
import { getUserSession } from "@/lib/auth";
import { findFacultyProfile, findStudentProfile, getPeopleData, type PeopleProfile } from "@/lib/peopleData";
import {
  getCourseCatalog,
  getCoursesForAdmin,
  getCoursesForFaculty,
  getCoursesForStudent,
  type CourseCatalogItem,
} from "@/lib/courseData";

const Courses = () => {
  const [search, setSearch] = useState("");
  const [catalog, setCatalog] = useState<CourseCatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [studentProfile, setStudentProfile] = useState<PeopleProfile | null>(null);
  const [facultyProfile, setFacultyProfile] = useState<PeopleProfile | null>(null);
  const session = useMemo(() => getUserSession(), []);
  const isInstructor = session?.role === "instructor";
  const isStudent = session?.role === "student";
  const isAdmin = session?.role === "admin";

  useEffect(() => {
    let cancelled = false;

    const loadCatalog = async () => {
      try {
        const [peopleData, courseCatalog] = await Promise.all([getPeopleData(), getCourseCatalog()]);
        const resolvedStudentProfile =
          session?.role === "student" ? findStudentProfile(peopleData, session.identifier) : null;
        const resolvedFacultyProfile =
          session?.role === "instructor" ? findFacultyProfile(peopleData, session.identifier) : null;

        if (!cancelled) {
          setCatalog(courseCatalog);
          setStudentProfile(resolvedStudentProfile);
          setFacultyProfile(resolvedFacultyProfile);
        }
      } catch (error) {
        console.error(error);
        if (!cancelled) {
          setLoadError("Unable to load course data right now.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void loadCatalog();

    return () => {
      cancelled = true;
    };
  }, [session?.identifier, session?.role]);

  const visibleCourses = useMemo(() => {
    if (isAdmin || !session) {
      return getCoursesForAdmin(catalog);
    }

    if (isInstructor) {
      return getCoursesForFaculty(catalog, facultyProfile);
    }

    if (isStudent) {
      return getCoursesForStudent(catalog, studentProfile);
    }

    return catalog;
  }, [catalog, facultyProfile, isAdmin, isInstructor, isStudent, session, studentProfile]);

  const filtered = visibleCourses.filter(
    (course) =>
      course.title.toLowerCase().includes(search.toLowerCase()) ||
      course.courseCode.toLowerCase().includes(search.toLowerCase()) ||
      course.facultyName.toLowerCase().includes(search.toLowerCase()) ||
      course.programs.join(" ").toLowerCase().includes(search.toLowerCase())
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
              {loading
                ? "Loading courses from the workbook"
                : `${visibleCourses.length} ${isInstructor ? "courses assigned to you" : isStudent ? "courses in your current semester" : isAdmin ? "courses available in the catalog" : "courses across all departments"}`}
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

        {loadError ? <p className="mb-4 text-sm text-destructive">{loadError}</p> : null}

        {loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading workbook data...
          </div>
        ) : null}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((course) => (
            <Card
              key={`${course.courseCode}-${course.semester}-${course.title}`}
              className={`shadow-card hover:shadow-elevated transition-shadow group ${isInstructor ? "cursor-pointer" : ""}`}
              onClick={isInstructor ? () => openStudyMaterial(course.courseCode) : undefined}
            >
              <CardContent className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary transition-colors">
                    <BookOpen className="w-5 h-5 text-primary group-hover:text-primary-foreground transition-colors" />
                  </div>
                  <Badge variant={course.categories.some((category) => /lab/i.test(category)) ? "secondary" : "outline"}>
                    {course.categories[0] || "Course"}
                  </Badge>
                </div>
                <h3 className="font-display font-semibold text-foreground">{course.title}</h3>
                <p className="text-sm text-primary font-mono font-medium mt-0.5">{course.courseCode}</p>
                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                  <span>Sem {course.semester}</span>
                  <span>{course.credits} Credits</span>
                  <span>{course.programs.join(", ") || "Catalog"}</span>
                </div>
                <p className="text-xs text-muted-foreground mt-2">{course.facultyName || "Faculty not listed"}</p>
                {course.facultyCode ? <p className="text-[11px] text-muted-foreground mt-1">Faculty Code: {course.facultyCode}</p> : null}
                {isInstructor ? (
                  <p className="text-xs text-primary mt-3 font-medium">Upload Study Material</p>
                ) : (
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button size="sm" variant="outline" onClick={() => openStudyMaterial(course.courseCode)}>
                      Open Study Material
                    </Button>
                  </div>
                )}
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
