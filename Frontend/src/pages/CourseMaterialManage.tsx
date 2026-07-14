import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Upload, ArrowLeft, FileText, Trash2, Loader2 } from "lucide-react";
import { getUserSession } from "@/lib/auth";
import { getCourseCatalog, getCoursesForFaculty, type CourseCatalogItem } from "@/lib/courseData";
import { findFacultyProfile, getPeopleData, type PeopleProfile } from "@/lib/peopleData";
import {
  deleteCourseMaterial,
  listCourseMaterial,
  uploadCourseMaterial,
  type CourseMaterialItem,
} from "@/lib/courseMaterialApi";

const formatSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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

  const [title, setTitle] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [materials, setMaterials] = useState<CourseMaterialItem[]>([]);
  const [materialsLoading, setMaterialsLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const course = taughtCourses[0] || null;

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
      } catch (loadCatalogError) {
        console.error(loadCatalogError);
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

  const refreshMaterials = async () => {
    if (!session?.token || !course) {
      return;
    }

    setMaterialsLoading(true);
    setError("");
    try {
      const items = await listCourseMaterial(courseCode, session.token);
      setMaterials(items);
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "Unable to load material.");
    } finally {
      setMaterialsLoading(false);
    }
  };

  useEffect(() => {
    void refreshMaterials();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseCode, course, session?.token]);

  const handleUpload = async () => {
    if (!session?.token || !course || !selectedFile || !title.trim()) {
      return;
    }

    setUploading(true);
    setError("");
    try {
      await uploadCourseMaterial(courseCode, title.trim(), selectedFile, session.token);
      setTitle("");
      setSelectedFile(null);
      await refreshMaterials();
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (materialId: string) => {
    if (!session?.token) {
      return;
    }

    setError("");
    try {
      await deleteCourseMaterial(courseCode, materialId, session.token);
      await refreshMaterials();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Delete failed.");
    }
  };

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
              <Label htmlFor="study-material-title">Title</Label>
              <Input
                id="study-material-title"
                placeholder="e.g. Module 3: Graphs and Traversal Algorithms"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="study-material-file">Study Material File</Label>
              <Input
                id="study-material-file"
                type="file"
                onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
              />
            </div>

            {error ? <p className="text-sm text-destructive">{error}</p> : null}

            <Button onClick={handleUpload} disabled={!selectedFile || !title.trim() || uploading}>
              {uploading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Upload className="w-4 h-4 mr-2" />}
              Upload Material
            </Button>

            <div className="space-y-3">
              <h3 className="font-semibold text-foreground">Uploaded Files</h3>
              {materialsLoading ? (
                <p className="text-sm text-muted-foreground">Loading uploaded files...</p>
              ) : materials.length === 0 ? (
                <p className="text-sm text-muted-foreground">No files uploaded yet for this course.</p>
              ) : (
                materials.map((item) => (
                  <div
                    key={item.material_id}
                    className="flex items-center justify-between p-3 border border-border rounded-md"
                  >
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-primary" />
                      <div>
                        <p className="text-sm text-foreground">{item.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {item.file_name} · {formatSize(item.size_bytes)} · {new Date(item.uploaded_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(item.material_id)}>
                      <Trash2 className="w-4 h-4 text-destructive" />
                    </Button>
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
