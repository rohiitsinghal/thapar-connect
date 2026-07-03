import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Upload, ArrowLeft, FileText } from "lucide-react";
import { getUserSession } from "@/lib/auth";
import { getCourseCatalog, getCoursesForFaculty, type CourseCatalogItem } from "@/lib/courseData";
import { findFacultyProfile, getPeopleData, type PeopleProfile } from "@/lib/peopleData";

type MaterialItem = {
  fileName: string;
  uploadedAt: string;
};

const CourseMaterialManage = () => {
  const [searchParams] = useSearchParams();
  const courseCode = (searchParams.get("code") || "").toUpperCase();
  const [catalog, setCatalog] = useState<CourseCatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [facultyProfile, setFacultyProfile] = useState<PeopleProfile | null>(null);

  const session = getUserSession();
  const isInstructor = session?.role === "instructor";
  const taughtCourses = useMemo(
    () => getCoursesForFaculty(catalog, facultyProfile).filter((course) => course.courseCode === courseCode),
    [catalog, courseCode, facultyProfile]
  );

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadedItems, setUploadedItems] = useState<MaterialItem[]>([]);
  const course = taughtCourses[0] || null;

  const storageKey = `material_${session?.identifier || ""}_${courseCode}`;

  const handleUpload = () => {
    if (!session || !course || !selectedFile) {
      return;
    }

    const updated = [
      {
        fileName: selectedFile.name,
        uploadedAt: new Date().toLocaleString(),
      },
      ...uploadedItems,
    ];

    window.localStorage.setItem(storageKey, JSON.stringify(updated));
    setUploadedItems(updated);
    setSelectedFile(null);
  };

  useEffect(() => {
    let cancelled = false;

    const loadCatalog = async () => {
      try {
        const [peopleData, resolvedCatalog] = await Promise.all([getPeopleData(), getCourseCatalog()]);
        const resolvedFacultyProfile =
          session?.role === "instructor" ? findFacultyProfile(peopleData, session.identifier) : null;
        if (!cancelled) {
          setCatalog(resolvedCatalog);
          setFacultyProfile(resolvedFacultyProfile);
        }
      } catch (error) {
        console.error(error);
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

  useEffect(() => {
    if (!session || !course) {
      setUploadedItems([]);
      return;
    }

    const key = `material_${session.identifier}_${courseCode}`;
    const saved = window.localStorage.getItem(key);
    if (!saved) {
      setUploadedItems([]);
      return;
    }

    try {
      setUploadedItems(JSON.parse(saved) as MaterialItem[]);
    } catch {
      setUploadedItems([]);
    }
  }, [courseCode, course, session]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background py-10 px-4">
        <div className="container mx-auto max-w-2xl">
          <Card>
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground">Loading course information...</p>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (!isInstructor || !session || !course) {
    return (
      <div className="min-h-screen bg-background py-10 px-4">
        <div className="container mx-auto max-w-2xl">
          <Card>
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground">This course is not part of your teaching assignments.</p>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background py-10 px-4">
      <div className="container mx-auto max-w-3xl">
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
            <CardTitle className="font-display text-2xl">Upload Study Material - {courseCode}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2 rounded-lg border border-border bg-secondary/40 p-4">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Taught course</p>
              <p className="text-sm font-medium text-foreground">{course.title}</p>
              <p className="text-xs text-muted-foreground">{course.facultyName}</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="study-material-file">Study Material File</Label>
              <Input
                id="study-material-file"
                type="file"
                onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
              />
            </div>

            <Button onClick={handleUpload} disabled={!selectedFile}>
              <Upload className="w-4 h-4 mr-2" />
              Upload Material
            </Button>

            <div className="space-y-3">
              <h3 className="font-semibold text-foreground">Uploaded Files</h3>
              {uploadedItems.length === 0 ? (
                <p className="text-sm text-muted-foreground">No files uploaded yet for this course.</p>
              ) : (
                uploadedItems.map((item, index) => (
                  <div
                    key={`${item.fileName}-${index}`}
                    className="flex items-center justify-between p-3 border border-border rounded-md"
                  >
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-primary" />
                      <span className="text-sm text-foreground">{item.fileName}</span>
                    </div>
                    <span className="text-xs text-muted-foreground">{item.uploadedAt}</span>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default CourseMaterialManage;
